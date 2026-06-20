"""World-model holdout validation for Paper 6 Experiment 6."""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from data_agent.experiments.run_causal import PROJECT_ROOT, _dump_portable_json


DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results"
)
EMBEDDING_COLUMNS = [f"A{i:02d}" for i in range(64)]
FIXTURE_CLASSES = (10, 30, 40, 50, 60, 80)
DEFAULT_SCALE_FACTORS = (0.25, 0.5, 1.0, 2.0, 4.0)
DEFAULT_SCENARIOS = ("baseline", "urban_sprawl", "ecological_restoration")


def _normalize_rows(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.ndim == 1:
        values = values[None, :]
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    norms = np.where(norms <= 1e-12, 1.0, norms)
    return values / norms


def _make_prototypes(random_state: int) -> dict[int, np.ndarray]:
    rng = np.random.default_rng(random_state)
    prototypes = {}
    for cls in FIXTURE_CLASSES:
        prototypes[cls] = _normalize_rows(rng.normal(size=(1, len(EMBEDDING_COLUMNS))))[0]
    return prototypes


def _default_fixture_areas() -> list[dict[str, Any]]:
    return [
        {"area": "Yangtze_Delta", "split": "Train", "family": "urban"},
        {"area": "Jianghan_Plain", "split": "Train", "family": "agriculture"},
        {"area": "Poyang_Lake", "split": "Val", "family": "wetland"},
        {"area": "Wuyi_Mountain", "split": "Test", "family": "forest"},
        {"area": "Lhasa_Valley", "split": "OOD", "family": "plateau"},
    ]


def _class_prior(family: str) -> np.ndarray:
    priors = {
        "urban": np.array([0.18, 0.10, 0.22, 0.34, 0.06, 0.10]),
        "agriculture": np.array([0.08, 0.18, 0.42, 0.12, 0.08, 0.12]),
        "wetland": np.array([0.15, 0.16, 0.18, 0.08, 0.05, 0.38]),
        "forest": np.array([0.52, 0.20, 0.10, 0.08, 0.05, 0.05]),
        "plateau": np.array([0.10, 0.22, 0.14, 0.08, 0.36, 0.10]),
    }
    return priors[family]


def _transition_matrix(family: str) -> dict[int, np.ndarray]:
    classes = list(FIXTURE_CLASSES)
    base = {}
    for idx, cls in enumerate(classes):
        probs = np.full(len(classes), 0.03, dtype=float)
        probs[idx] = 0.82
        base[cls] = probs

    def set_prob(src: int, dst: int, value: float) -> None:
        src_idx = classes.index(src)
        dst_idx = classes.index(dst)
        probs = np.full(len(classes), 0.02, dtype=float)
        probs[src_idx] = max(0.0, 1.0 - value - 0.08)
        probs[dst_idx] = value
        for idx in range(len(classes)):
            if idx not in (src_idx, dst_idx):
                probs[idx] = 0.08 / max(len(classes) - 2, 1)
        base[src] = probs / probs.sum()

    if family == "urban":
        set_prob(40, 50, 0.22)
        set_prob(30, 50, 0.15)
        set_prob(10, 50, 0.10)
    elif family == "agriculture":
        set_prob(30, 40, 0.16)
        set_prob(40, 50, 0.08)
    elif family == "wetland":
        set_prob(30, 80, 0.18)
        set_prob(40, 80, 0.12)
    elif family == "forest":
        set_prob(10, 30, 0.08)
        set_prob(30, 10, 0.10)
    elif family == "plateau":
        set_prob(60, 30, 0.12)
        set_prob(30, 60, 0.10)

    return {cls: probs / probs.sum() for cls, probs in base.items()}


def build_offline_fixture_panel(
    *,
    random_state: int = 0,
    n_pixels_per_area: int = 32,
    years: Iterable[int] = (2018, 2019, 2020, 2021, 2022),
    areas: list[dict[str, Any]] | None = None,
) -> pd.DataFrame:
    """Create a deterministic AlphaEarth-like temporal panel."""
    rng = np.random.default_rng(random_state)
    prototypes = _make_prototypes(random_state + 11)
    drift_vectors = {
        cls: _normalize_rows(rng.normal(size=(1, len(EMBEDDING_COLUMNS))))[0] * 0.04
        for cls in FIXTURE_CLASSES
    }
    years = tuple(sorted(int(year) for year in years))
    areas = areas or _default_fixture_areas()
    global_trend = _normalize_rows(rng.normal(size=(1, len(EMBEDDING_COLUMNS))))[0] * 0.03
    records: list[dict[str, Any]] = []

    for area_idx, area in enumerate(areas):
        family = area["family"]
        split = area["split"]
        area_name = area["area"]
        area_vec = _normalize_rows(rng.normal(size=(1, len(EMBEDDING_COLUMNS))))[0] * 0.18
        transition = _transition_matrix(family)
        priors = _class_prior(family)
        change_scale = {"Train": 0.90, "Val": 1.00, "Test": 1.10, "OOD": 1.25}[split]

        for pixel_idx in range(int(n_pixels_per_area)):
            pixel_id = f"{area_name}_px{pixel_idx:03d}"
            pixel_vec = _normalize_rows(rng.normal(size=(1, len(EMBEDDING_COLUMNS))))[0] * 0.10
            current_class = int(rng.choice(FIXTURE_CLASSES, p=priors))
            for year_offset, year in enumerate(years):
                yearly_vec = (
                    prototypes[current_class]
                    + area_vec
                    + pixel_vec
                    + drift_vectors[current_class] * (year_offset * change_scale)
                    + global_trend * (0.25 * area_idx + 0.15 * year_offset)
                    + rng.normal(scale=0.015, size=len(EMBEDDING_COLUMNS))
                )
                embedding = _normalize_rows(yearly_vec)[0]
                record = {
                    "area": area_name,
                    "split": split,
                    "pixel_id": pixel_id,
                    "year": int(year),
                    "lulc_label": int(current_class),
                }
                record.update(
                    {
                        column: float(value)
                        for column, value in zip(EMBEDDING_COLUMNS, embedding, strict=True)
                    }
                )
                records.append(record)

                if year != years[-1]:
                    probs = transition[current_class]
                    current_class = int(rng.choice(FIXTURE_CLASSES, p=probs))

    return pd.DataFrame(records)


def _embedding_from_row(row: pd.Series) -> np.ndarray:
    return row[EMBEDDING_COLUMNS].to_numpy(dtype=float)


def build_transition_pairs(
    panel: pd.DataFrame,
    *,
    horizons: Iterable[int] = (1, 2),
    holdout_splits: Iterable[str] = ("Test", "OOD"),
    holdout_years: Iterable[int] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build train and holdout transition pairs from a temporal panel."""
    holdout_splits = tuple(holdout_splits)
    holdout_years = None if holdout_years is None else {int(year) for year in holdout_years}
    rows: list[dict[str, Any]] = []
    ordered = panel.sort_values(["area", "pixel_id", "year"]).reset_index(drop=True)

    for (_, _), group in ordered.groupby(["area", "pixel_id"], sort=False):
        group = group.sort_values("year").reset_index(drop=True)
        if len(group) < 2:
            continue
        for start_idx in range(len(group)):
            for horizon in horizons:
                target_idx = start_idx + int(horizon)
                if target_idx >= len(group):
                    continue
                start = group.iloc[start_idx]
                target = group.iloc[target_idx]
                rows.append(
                    {
                        "area": start["area"],
                        "split": start["split"],
                        "pixel_id": start["pixel_id"],
                        "year_t": int(start["year"]),
                        "year_tp1": int(target["year"]),
                        "horizon": int(horizon),
                        "z_t": _embedding_from_row(start),
                        "z_tp1": _embedding_from_row(target),
                        "lulc_t": int(start["lulc_label"]),
                        "lulc_tp1": int(target["lulc_label"]),
                    }
                )

    pairs = pd.DataFrame(rows)
    if pairs.empty:
        return pairs.copy(), pairs.copy()

    holdout_mask = pairs["split"].isin(holdout_splits)
    if holdout_years is not None:
        holdout_mask &= pairs["year_tp1"].isin(holdout_years)
    train_mask = ~pairs["split"].isin(holdout_splits)
    return pairs.loc[train_mask].reset_index(drop=True), pairs.loc[holdout_mask].reset_index(drop=True)


def _stack_vectors(series: pd.Series) -> np.ndarray:
    return np.stack(series.to_list()).astype(float)


def _compute_class_prototypes(
    embeddings: np.ndarray,
    labels: np.ndarray,
) -> dict[int, np.ndarray]:
    prototypes = {}
    for cls in sorted(pd.unique(labels).tolist()):
        members = embeddings[labels == cls]
        if len(members) == 0:
            continue
        prototypes[int(cls)] = _normalize_rows(members.mean(axis=0))[0]
    return prototypes


def _decode_with_prototypes(
    embeddings: np.ndarray,
    prototypes: dict[int, np.ndarray],
) -> np.ndarray:
    classes = sorted(prototypes)
    if not classes:
        return np.zeros(len(embeddings), dtype=int)
    prototype_matrix = np.stack([prototypes[cls] for cls in classes])
    similarities = _normalize_rows(embeddings) @ prototype_matrix.T
    indices = np.argmax(similarities, axis=1)
    return np.array([classes[idx] for idx in indices], dtype=int)


def _metrics_row(
    *,
    baseline: str,
    horizon: int,
    evaluation_mode: str,
    predicted: np.ndarray | None,
    truth: np.ndarray,
    truth_labels: np.ndarray,
    prototypes: dict[int, np.ndarray],
) -> dict[str, Any]:
    if predicted is None:
        return {
            "baseline": baseline,
            "evaluation_mode": evaluation_mode,
            "horizon": int(horizon),
            "mean_cosine_similarity": np.nan,
            "mean_cosine_distance": np.nan,
            "rmse": np.nan,
            "mae": np.nan,
            "mean_l2_distance": np.nan,
            "decoded_accuracy": np.nan,
            "n_rows": int(len(truth)),
            "status": "skipped",
        }

    truth_norm = _normalize_rows(truth)
    pred_norm = _normalize_rows(predicted)
    cosine = np.sum(truth_norm * pred_norm, axis=1)
    diffs = pred_norm - truth_norm
    predicted_labels = _decode_with_prototypes(pred_norm, prototypes)
    return {
        "baseline": baseline,
        "evaluation_mode": evaluation_mode,
        "horizon": int(horizon),
        "mean_cosine_similarity": float(np.mean(cosine)),
        "mean_cosine_distance": float(np.mean(1.0 - cosine)),
        "rmse": float(np.sqrt(np.mean(diffs**2))),
        "mae": float(np.mean(np.abs(diffs))),
        "mean_l2_distance": float(np.mean(np.linalg.norm(diffs, axis=1))),
        "decoded_accuracy": float(np.mean(predicted_labels == truth_labels)),
        "n_rows": int(len(truth_norm)),
        "status": "ok",
    }


def _predict_persistence(holdout_pairs: pd.DataFrame) -> np.ndarray:
    return _stack_vectors(holdout_pairs["z_t"])


def _predict_mean_delta(train_pairs: pd.DataFrame, holdout_pairs: pd.DataFrame) -> np.ndarray | None:
    if train_pairs.empty or holdout_pairs.empty:
        return None
    z_train = _stack_vectors(train_pairs["z_t"])
    z_train_next = _stack_vectors(train_pairs["z_tp1"])
    delta = z_train_next - z_train
    mean_delta = delta.mean(axis=0, keepdims=True)
    predicted = _stack_vectors(holdout_pairs["z_t"]) + mean_delta
    return _normalize_rows(predicted)


def _predict_ridge_transition(train_pairs: pd.DataFrame, holdout_pairs: pd.DataFrame) -> np.ndarray | None:
    if train_pairs.empty or holdout_pairs.empty:
        return None
    x_train = _stack_vectors(train_pairs["z_t"])
    y_train = _stack_vectors(train_pairs["z_tp1"])
    x_holdout = _stack_vectors(holdout_pairs["z_t"])
    model = Ridge(alpha=1.0, random_state=0)
    model.fit(x_train, y_train)
    predicted = model.predict(x_holdout)
    return _normalize_rows(predicted)


def _build_markov_components(train_pairs: pd.DataFrame) -> tuple[dict[int, np.ndarray], dict[int, dict[int, float]]]:
    target_embeddings = _stack_vectors(train_pairs["z_tp1"])
    target_labels = train_pairs["lulc_tp1"].to_numpy(dtype=int)
    prototypes = _compute_class_prototypes(target_embeddings, target_labels)
    transitions: dict[int, dict[int, float]] = {}
    counts = (
        train_pairs.groupby(["lulc_t", "lulc_tp1"]).size().reset_index(name="n")
    )
    for cls_t, group in counts.groupby("lulc_t"):
        total = float(group["n"].sum())
        transitions[int(cls_t)] = {
            int(row["lulc_tp1"]): float(row["n"]) / total
            for _, row in group.iterrows()
        }
    return prototypes, transitions


def _predict_markov_transition(train_pairs: pd.DataFrame, holdout_pairs: pd.DataFrame) -> np.ndarray | None:
    if train_pairs.empty or holdout_pairs.empty:
        return None
    prototypes, transitions = _build_markov_components(train_pairs)
    if not prototypes:
        return None
    predictions = []
    for _, row in holdout_pairs.iterrows():
        probs = transitions.get(int(row["lulc_t"]))
        if not probs:
            predictions.append(np.asarray(row["z_t"], dtype=float))
            continue
        vector = np.zeros(len(EMBEDDING_COLUMNS), dtype=float)
        weight_sum = 0.0
        for cls, weight in probs.items():
            if cls not in prototypes:
                continue
            vector += weight * prototypes[cls]
            weight_sum += weight
        if weight_sum <= 1e-12:
            vector = np.asarray(row["z_t"], dtype=float)
        predictions.append(vector)
    return _normalize_rows(np.stack(predictions))


def _call_world_model_predictor(
    predictor: Callable[..., np.ndarray | None],
    *,
    train_pairs: pd.DataFrame,
    holdout_pairs: pd.DataFrame,
    horizon: int,
    scenario: str,
    scale_factor: float = 1.0,
) -> np.ndarray | None:
    signature = inspect.signature(predictor)
    accepts_kwargs = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )
    kwargs = {
        "train_pairs": train_pairs,
        "holdout_pairs": holdout_pairs,
        "horizon": horizon,
        "scenario": scenario,
        "scale_factor": scale_factor,
    }
    if accepts_kwargs:
        return predictor(**kwargs)
    filtered = {key: value for key, value in kwargs.items() if key in signature.parameters}
    return predictor(**filtered)


def default_world_model_predictor(
    *,
    train_pairs: pd.DataFrame,
    holdout_pairs: pd.DataFrame,
    horizon: int,
    scenario: str,
    scale_factor: float = 1.0,
) -> np.ndarray | None:
    """Run the repository latent dynamics model on vector rows if available."""
    if holdout_pairs.empty:
        return None
    try:
        import torch
        import torch.nn.functional as F

        from data_agent.world_model import _load_model, encode_scenario

        z_t = _stack_vectors(holdout_pairs["z_t"])
        model = _load_model()
        scenario_vec = encode_scenario(scenario).repeat(len(z_t), 1) * float(scale_factor)
        z = torch.tensor(z_t, dtype=torch.float32).unsqueeze(-1).unsqueeze(-1)
        with torch.no_grad():
            for _ in range(int(horizon)):
                z = model(z, scenario_vec)
                z = F.normalize(z, p=2, dim=1)
        return z.squeeze(-1).squeeze(-1).cpu().numpy()
    except Exception:
        return None


def evaluate_holdout_metrics(
    train_pairs: pd.DataFrame,
    holdout_pairs: pd.DataFrame,
    *,
    evaluation_mode: str,
    include_world_model_baseline: bool = True,
    world_model_predictor: Callable[..., np.ndarray | None] | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if holdout_pairs.empty:
        return pd.DataFrame(
            [
                {
                    "baseline": "none",
                    "evaluation_mode": evaluation_mode,
                    "horizon": 1,
                    "mean_cosine_similarity": np.nan,
                    "mean_cosine_distance": np.nan,
                    "rmse": np.nan,
                    "mae": np.nan,
                    "mean_l2_distance": np.nan,
                    "decoded_accuracy": np.nan,
                    "n_rows": 0,
                    "status": "skipped",
                }
            ]
        )

    truth_all = _stack_vectors(holdout_pairs["z_tp1"])
    truth_labels_all = holdout_pairs["lulc_tp1"].to_numpy(dtype=int)
    prototypes = _compute_class_prototypes(
        _stack_vectors(train_pairs["z_tp1"]),
        train_pairs["lulc_tp1"].to_numpy(dtype=int),
    )
    baseline_predictor = world_model_predictor or default_world_model_predictor

    for horizon, horizon_pairs in holdout_pairs.groupby("horizon", sort=True):
        train_subset = train_pairs[train_pairs["horizon"] == horizon]
        truth = _stack_vectors(horizon_pairs["z_tp1"])
        truth_labels = horizon_pairs["lulc_tp1"].to_numpy(dtype=int)
        rows.append(
            _metrics_row(
                baseline="persistence",
                horizon=int(horizon),
                evaluation_mode=evaluation_mode,
                predicted=_predict_persistence(horizon_pairs),
                truth=truth,
                truth_labels=truth_labels,
                prototypes=prototypes,
            )
        )
        rows.append(
            _metrics_row(
                baseline="mean_delta",
                horizon=int(horizon),
                evaluation_mode=evaluation_mode,
                predicted=_predict_mean_delta(train_subset, horizon_pairs),
                truth=truth,
                truth_labels=truth_labels,
                prototypes=prototypes,
            )
        )
        rows.append(
            _metrics_row(
                baseline="ridge_transition",
                horizon=int(horizon),
                evaluation_mode=evaluation_mode,
                predicted=_predict_ridge_transition(train_subset, horizon_pairs),
                truth=truth,
                truth_labels=truth_labels,
                prototypes=prototypes,
            )
        )
        rows.append(
            _metrics_row(
                baseline="markov_transition",
                horizon=int(horizon),
                evaluation_mode=evaluation_mode,
                predicted=_predict_markov_transition(train_subset, horizon_pairs),
                truth=truth,
                truth_labels=truth_labels,
                prototypes=prototypes,
            )
        )
        if include_world_model_baseline:
            predicted = _call_world_model_predictor(
                baseline_predictor,
                train_pairs=train_subset,
                holdout_pairs=horizon_pairs,
                horizon=int(horizon),
                scenario="baseline",
                scale_factor=1.0,
            )
            rows.append(
                _metrics_row(
                    baseline="world_model_baseline",
                    horizon=int(horizon),
                    evaluation_mode=evaluation_mode,
                    predicted=predicted,
                    truth=truth,
                    truth_labels=truth_labels,
                    prototypes=prototypes,
                )
            )

    return pd.DataFrame(rows)


def run_scenario_calibration(
    train_pairs: pd.DataFrame,
    holdout_pairs: pd.DataFrame,
    *,
    evaluation_mode: str,
    scenarios: Iterable[str] = DEFAULT_SCENARIOS,
    scale_factors: Iterable[float] = DEFAULT_SCALE_FACTORS,
) -> pd.DataFrame:
    """Measure whether scaled scenario deltas stay within a conservative envelope."""
    if holdout_pairs.empty:
        return pd.DataFrame(
            [
                {
                    "scenario": "baseline",
                    "scale_factor": 1.0,
                    "predicted_delta_l2": np.nan,
                    "observed_holdout_delta_l2": np.nan,
                    "delta_ratio_vs_holdout": np.nan,
                    "plausible_vs_holdout": False,
                    "evaluation_mode": evaluation_mode,
                    "status": "skipped",
                }
            ]
        )

    base_holdout = holdout_pairs[holdout_pairs["horizon"] == 1].copy()
    if base_holdout.empty:
        base_holdout = holdout_pairs.copy()
    train_base = train_pairs[train_pairs["horizon"] == 1].copy()
    if train_base.empty:
        train_base = train_pairs.copy()

    z_holdout = _stack_vectors(base_holdout["z_t"])
    observed_next = _stack_vectors(base_holdout["z_tp1"])
    observed_delta_l2 = float(np.mean(np.linalg.norm(observed_next - z_holdout, axis=1)))
    mean_delta = (
        _stack_vectors(train_base["z_tp1"]) - _stack_vectors(train_base["z_t"])
    ).mean(axis=0)
    scenario_modifiers = {
        "baseline": 1.0,
        "urban_sprawl": 1.25,
        "ecological_restoration": 0.75,
    }

    rows = []
    for scenario in scenarios:
        modifier = float(scenario_modifiers.get(scenario, 1.0))
        for scale_factor in scale_factors:
            effective_scale = float(scale_factor) * modifier
            predicted = _normalize_rows(z_holdout + effective_scale * mean_delta)
            predicted_delta_l2 = float(
                np.mean(np.linalg.norm(predicted - z_holdout, axis=1))
            )
            ratio = (
                predicted_delta_l2 / observed_delta_l2
                if observed_delta_l2 > 1e-12
                else np.nan
            )
            plausible = bool(
                np.isfinite(ratio)
                and ratio >= 0.5
                and ratio <= 2.0
            )
            rows.append(
                {
                    "scenario": scenario,
                    "scale_factor": float(scale_factor),
                    "predicted_delta_l2": predicted_delta_l2,
                    "observed_holdout_delta_l2": observed_delta_l2,
                    "delta_ratio_vs_holdout": ratio,
                    "plausible_vs_holdout": plausible,
                    "evaluation_mode": evaluation_mode,
                    "status": "ok",
                }
            )
    return pd.DataFrame(rows)


def _best_baseline(metrics: pd.DataFrame) -> dict[str, Any] | None:
    if metrics.empty:
        return None
    ok = metrics[metrics["status"] == "ok"].copy()
    if ok.empty:
        return None
    ordered = ok.sort_values(["horizon", "rmse", "mean_l2_distance"])
    return ordered.iloc[0].to_dict()


def _render_report(
    metrics: pd.DataFrame,
    calibration: pd.DataFrame,
    *,
    evaluation_mode: str,
    claim_guidance: str,
) -> str:
    best = _best_baseline(metrics)
    lines = [
        "# World Model Holdout Validation Report",
        "",
        f"- Evaluation mode: `{evaluation_mode}`",
        f"- Claim guidance: `{claim_guidance}`",
        "",
    ]
    if best is not None:
        lines.extend(
            [
                "## Best Baseline",
                "",
                f"- Baseline: `{best['baseline']}`",
                f"- Horizon: `{int(best['horizon'])}`",
                f"- RMSE: `{best['rmse']}`",
                f"- Mean cosine similarity: `{best['mean_cosine_similarity']}`",
                "",
            ]
        )
    lines.extend(["## Holdout Metrics", ""])
    for _, row in metrics.iterrows():
        lines.append(
            f"- `{row['baseline']}` horizon `{int(row['horizon'])}`: "
            f"status `{row['status']}`, RMSE `{row['rmse']}`, "
            f"decoded accuracy `{row['decoded_accuracy']}`"
        )
    lines.extend(["", "## Scenario Calibration", ""])
    for _, row in calibration.iterrows():
        lines.append(
            f"- `{row['scenario']}` x `{row['scale_factor']}`: "
            f"delta L2 `{row['predicted_delta_l2']}`, "
            f"plausible `{row['plausible_vs_holdout']}`"
        )
    return "\n".join(lines) + "\n"


def write_world_model_holdout_outputs(
    *,
    output_dir: str | Path,
    metrics: pd.DataFrame,
    calibration: pd.DataFrame,
    evaluation_mode: str,
    panel_metadata: dict[str, Any],
) -> dict[str, Any]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    metrics_path = target / "world_model_holdout_metrics.csv"
    calibration_path = target / "world_model_scenario_calibration.csv"
    manifest_path = target / "world_model_holdout_validation_manifest.json"
    report_path = target / "world_model_holdout_validation_report.md"

    metrics.to_csv(metrics_path, index=False)
    calibration.to_csv(calibration_path, index=False)

    claim_guidance = (
        "predictive_validation_available"
        if evaluation_mode == "real_alphaearth_panel"
        else "scenario_simulation_only"
    )
    report_path.write_text(
        _render_report(
            metrics,
            calibration,
            evaluation_mode=evaluation_mode,
            claim_guidance=claim_guidance,
        ),
        encoding="utf-8",
    )

    manifest = {
        "holdout_metrics_csv": str(metrics_path),
        "scenario_calibration_csv": str(calibration_path),
        "manifest_json": str(manifest_path),
        "report_md": str(report_path),
        "evaluation_mode": evaluation_mode,
        "claim_guidance": claim_guidance,
        "n_metric_rows": int(len(metrics)),
        "n_calibration_rows": int(len(calibration)),
        "panel_metadata": panel_metadata,
    }
    _dump_portable_json(manifest, manifest_path)
    return manifest


def _decode_embeddings_with_world_model_decoder(embeddings: np.ndarray) -> np.ndarray | None:
    try:
        from data_agent.world_model import _load_decoder

        decoder = _load_decoder()
        return decoder.predict(embeddings)
    except Exception:
        return None


def _load_cached_real_panel(
    *,
    years: Iterable[int],
    areas: list[dict[str, Any]] | None = None,
) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    try:
        from data_agent.embedding_store import load_grid_embeddings
        from data_agent.experiments.run_world_model import AREAS
    except Exception as exc:
        return None, {"status": f"cache_unavailable: {exc}"}

    years = tuple(sorted(int(year) for year in years))
    source_areas = areas or AREAS
    records: list[dict[str, Any]] = []
    loaded_areas = 0
    total_pixels = 0
    for area in source_areas:
        area_name = area["name"]
        split = area["split"]
        grids = []
        for year in years:
            grid = load_grid_embeddings(area["bbox"], year)
            if grid is None:
                grids = []
                break
            grids.append((year, grid))
        if not grids:
            continue
        min_h = min(grid.shape[0] for _, grid in grids)
        min_w = min(grid.shape[1] for _, grid in grids)
        loaded_areas += 1
        total_pixels += min_h * min_w
        for year, grid in grids:
            flat = grid[:min_h, :min_w, :].reshape(-1, len(EMBEDDING_COLUMNS))
            labels = _decode_embeddings_with_world_model_decoder(flat)
            if labels is None:
                labels = np.zeros(len(flat), dtype=int)
            for pixel_idx, vector in enumerate(flat):
                record = {
                    "area": area_name,
                    "split": split,
                    "pixel_id": f"{area_name}_px{pixel_idx:05d}",
                    "year": int(year),
                    "lulc_label": int(labels[pixel_idx]),
                }
                record.update(
                    {
                        column: float(value)
                        for column, value in zip(EMBEDDING_COLUMNS, vector, strict=True)
                    }
                )
                records.append(record)
    if not records:
        return None, {"status": "cache_empty"}
    return (
        pd.DataFrame(records),
        {
            "status": "ok",
            "source": "cached_grids",
            "loaded_areas": int(loaded_areas),
            "loaded_pixels": int(total_pixels),
            "years": list(years),
        },
    )


def _sample_real_alphaearth_panel(
    *,
    years: Iterable[int],
    n_points_per_area: int,
    random_state: int,
    areas: list[dict[str, Any]] | None = None,
) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    try:
        import ee

        from data_agent.experiments.run_world_model import AREAS
        from data_agent.world_model import AEF_BANDS, AEF_COLLECTION

        ee.Initialize()
    except Exception as exc:
        return None, {"status": f"gee_unavailable: {exc}"}

    years = tuple(sorted(int(year) for year in years))
    source_areas = areas or AREAS
    records: list[dict[str, Any]] = []
    attempted = 0
    successful = 0

    for area_idx, area in enumerate(source_areas):
        attempted += 1
        bbox = area["bbox"]
        split = area["split"]
        area_name = area["name"]
        try:
            roi = ee.Geometry.Rectangle(bbox)
            stacked = None
            for year in years:
                year_bands = [f"{year}_{band}" for band in AEF_BANDS]
                image = (
                    ee.ImageCollection(AEF_COLLECTION)
                    .filterDate(f"{year}-01-01", f"{year + 1}-01-01")
                    .filterBounds(roi)
                    .select(AEF_BANDS)
                    .mosaic()
                    .rename(year_bands)
                )
                stacked = image if stacked is None else stacked.addBands(image)
            points = ee.FeatureCollection.randomPoints(
                region=roi,
                points=int(n_points_per_area),
                seed=int(random_state + area_idx),
            )
            sampled = stacked.sampleRegions(
                collection=points,
                scale=10,
                geometries=False,
            ).getInfo()
            features = sampled.get("features", [])
            if not features:
                continue
            successful += 1
            for pixel_idx, feature in enumerate(features):
                props = feature.get("properties", {})
                complete = True
                yearly_vectors = {}
                for year in years:
                    vector = [props.get(f"{year}_{band}") for band in AEF_BANDS]
                    if any(value is None for value in vector):
                        complete = False
                        break
                    yearly_vectors[year] = _normalize_rows(np.asarray(vector, dtype=float))[0]
                if not complete:
                    continue
                decoded = _decode_embeddings_with_world_model_decoder(
                    np.stack([yearly_vectors[year] for year in years])
                )
                if decoded is None:
                    decoded = np.zeros(len(years), dtype=int)
                for year_idx, year in enumerate(years):
                    record = {
                        "area": area_name,
                        "split": split,
                        "pixel_id": f"{area_name}_px{pixel_idx:04d}",
                        "year": int(year),
                        "lulc_label": int(decoded[year_idx]),
                    }
                    record.update(
                        {
                            column: float(value)
                            for column, value in zip(
                                EMBEDDING_COLUMNS,
                                yearly_vectors[year],
                                strict=True,
                            )
                        }
                    )
                    records.append(record)
        except Exception:
            continue

    if not records:
        return None, {
            "status": "gee_sampling_failed",
            "attempted_areas": int(attempted),
            "successful_areas": int(successful),
            "years": list(years),
        }
    return (
        pd.DataFrame(records),
        {
            "status": "ok",
            "source": "gee_points",
            "attempted_areas": int(attempted),
            "successful_areas": int(successful),
            "years": list(years),
            "n_points_per_area": int(n_points_per_area),
        },
    )


def try_build_real_alphaearth_panel(
    *,
    years: Iterable[int],
    n_points_per_area: int = 64,
    random_state: int = 0,
    attempt_gee: bool = False,
) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    panel, metadata = _load_cached_real_panel(years=years)
    if panel is not None and not panel.empty:
        return panel, metadata
    if attempt_gee:
        panel, gee_metadata = _sample_real_alphaearth_panel(
            years=years,
            n_points_per_area=n_points_per_area,
            random_state=random_state,
        )
        if panel is not None and not panel.empty:
            return panel, gee_metadata
        return None, {"status": "fallback_to_fixture", "cache": metadata, "gee": gee_metadata}
    return None, {"status": "fallback_to_fixture", "cache": metadata}


def run_world_model_holdout_validation(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    random_state: int = 0,
    years: Iterable[int] = (2018, 2019, 2020, 2021, 2022),
    horizons: Iterable[int] = (1, 2),
    holdout_splits: Iterable[str] = ("Test", "OOD"),
    n_pixels_per_area: int = 32,
    holdout_years: Iterable[int] | None = None,
    use_real_panel: bool = False,
    attempt_gee: bool = False,
    n_points_per_area: int = 64,
    include_world_model_baseline: bool = True,
    world_model_predictor: Callable[..., np.ndarray | None] | None = None,
) -> dict[str, Any]:
    years = tuple(sorted(int(year) for year in years))
    target_holdout_years = (
        tuple(int(year) for year in holdout_years)
        if holdout_years is not None
        else (years[-1],)
    )

    panel: pd.DataFrame
    panel_metadata: dict[str, Any]
    evaluation_mode = "offline_fixture_proxy"
    if use_real_panel:
        real_panel, real_metadata = try_build_real_alphaearth_panel(
            years=years,
            n_points_per_area=n_points_per_area,
            random_state=random_state,
            attempt_gee=attempt_gee,
        )
        if real_panel is not None and not real_panel.empty:
            panel = real_panel
            panel_metadata = real_metadata
            evaluation_mode = "real_alphaearth_panel"
        else:
            panel = build_offline_fixture_panel(
                random_state=random_state,
                n_pixels_per_area=n_pixels_per_area,
                years=years,
            )
            panel_metadata = {"fallback": real_metadata, "status": "offline_fixture_proxy"}
    else:
        panel = build_offline_fixture_panel(
            random_state=random_state,
            n_pixels_per_area=n_pixels_per_area,
            years=years,
        )
        panel_metadata = {"status": "offline_fixture_proxy", "years": list(years)}

    train_pairs, holdout_pairs = build_transition_pairs(
        panel,
        horizons=horizons,
        holdout_splits=holdout_splits,
        holdout_years=target_holdout_years,
    )
    metrics = evaluate_holdout_metrics(
        train_pairs,
        holdout_pairs,
        evaluation_mode=evaluation_mode,
        include_world_model_baseline=include_world_model_baseline,
        world_model_predictor=world_model_predictor,
    )
    calibration = run_scenario_calibration(
        train_pairs,
        holdout_pairs,
        evaluation_mode=evaluation_mode,
    )
    panel_metadata.update(
        {
            "n_panel_rows": int(len(panel)),
            "n_train_pairs": int(len(train_pairs)),
            "n_holdout_pairs": int(len(holdout_pairs)),
            "holdout_years": list(target_holdout_years),
            "holdout_splits": list(holdout_splits),
        }
    )
    return write_world_model_holdout_outputs(
        output_dir=output_dir,
        metrics=metrics,
        calibration=calibration,
        evaluation_mode=evaluation_mode,
        panel_metadata=panel_metadata,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Paper 6 world-model holdout validation.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--random-state", type=int, default=0)
    parser.add_argument("--n-pixels-per-area", type=int, default=32)
    parser.add_argument("--years", nargs="*", type=int, default=[2018, 2019, 2020, 2021, 2022])
    parser.add_argument("--holdout-years", nargs="*", type=int, default=None)
    parser.add_argument("--use-real-panel", action="store_true")
    parser.add_argument("--attempt-gee", action="store_true")
    parser.add_argument("--n-points-per-area", type=int, default=64)
    parser.add_argument("--no-world-model-baseline", action="store_true")
    args = parser.parse_args()

    manifest = run_world_model_holdout_validation(
        output_dir=args.output_dir,
        random_state=args.random_state,
        years=tuple(args.years),
        holdout_years=tuple(args.holdout_years) if args.holdout_years else None,
        n_pixels_per_area=args.n_pixels_per_area,
        use_real_panel=args.use_real_panel,
        attempt_gee=args.attempt_gee,
        n_points_per_area=args.n_points_per_area,
        include_world_model_baseline=not args.no_world_model_baseline,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
