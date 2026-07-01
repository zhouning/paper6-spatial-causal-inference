"""Chongqing UHI ablation and robustness analysis utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results"
)

GEOMETRY_COLUMNS = ("centroid_x", "centroid_y", "area_m2")
TERRAIN_COLUMNS = ("elevation", "slope")
SENTINEL_INDEX_COLUMNS = ("NDVI", "NDBI", "MNDWI", "BSI")
SENTINEL_BAND_COLUMNS = ("B2", "B3", "B4", "B8", "B11", "B12")

FEATURE_SPECS: dict[str, tuple[str, ...]] = {
    "raw": (),
    "coordinates_only": ("centroid_x", "centroid_y"),
    "geometry": GEOMETRY_COLUMNS,
    "terrain": (*GEOMETRY_COLUMNS, *TERRAIN_COLUMNS),
    # Primary causal specification: coordinates + geometry + terrain only.
    # These sources are plausibly fixed *before* high-rise construction, so the
    # adjustment set avoids conditioning on Sentinel-derived surfaces that may be
    # post-treatment mediators (see the variable-role audit). This is the
    # manuscript's preferred confounder-only design.
    "pre_treatment": (*GEOMETRY_COLUMNS, *TERRAIN_COLUMNS),
    "sentinel_indices": (*GEOMETRY_COLUMNS, *SENTINEL_INDEX_COLUMNS),
    "sentinel_bands": (*GEOMETRY_COLUMNS, *SENTINEL_BAND_COLUMNS),
    # full_rs_context ADDS Sentinel bands+indices on top of the pre-treatment set.
    # It is retained as an over-adjustment comparison, NOT as the preferred causal
    # specification, because Sentinel surfaces may be affected by the treatment.
    "full_rs_context": (
        *GEOMETRY_COLUMNS,
        *SENTINEL_BAND_COLUMNS,
        *SENTINEL_INDEX_COLUMNS,
        *TERRAIN_COLUMNS,
    ),
    "pca_context": GEOMETRY_COLUMNS,
}

# Adjustment sets that only use plausibly pre-treatment context. Used by the
# evidence synthesis to select the preferred causal specification on a
# causal-validity basis rather than on post-match balance alone.
PRE_TREATMENT_VARIANTS = ("coordinates_only", "terrain", "pre_treatment")
# Adjustment sets that condition on Sentinel-derived surfaces (possible mediators).
MEDIATOR_RISK_VARIANTS = ("sentinel_indices", "sentinel_bands", "full_rs_context")


OUTPUT_FILES = {
    "ablation_csv": "chongqing_uhi_ablation.csv",
    "balance_csv": "chongqing_uhi_balance.csv",
    "matched_counts_csv": "chongqing_uhi_matched_counts.csv",
    "bootstrap_csv": "chongqing_spatial_bootstrap.csv",
    "placebo_csv": "chongqing_placebo_thresholds.csv",
    "residual_csv": "chongqing_residual_spatial_diagnostics.csv",
    "change_of_support_csv": "chongqing_change_of_support.csv",
    "manifest_json": "chongqing_uhi_analysis_manifest.json",
    "report_md": "chongqing_uhi_analysis_report.md",
}


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        return numeric if np.isfinite(numeric) else None
    return value


def resolve_feature_columns(frame: pd.DataFrame, names: Iterable[str]) -> list[str]:
    """Resolve requested feature names, accepting either plain or rs_ columns."""
    aliases = {
        "area_m2": ("area_m2", "area_sqm"),
        "floor": ("floor", "Floor", "floors"),
        "LST": ("LST", "lst"),
    }
    resolved: list[str] = []
    for name in names:
        candidates = list(aliases.get(name, (name,)))
        candidates.append(f"rs_{name}")
        for candidate in candidates:
            if candidate in frame.columns:
                resolved.append(candidate)
                break
        else:
            raise KeyError(f"Missing Chongqing UHI feature column: {name}")
    return resolved


def _resolve_optional_column(
    frame: pd.DataFrame,
    preferred: str,
    aliases: Iterable[str],
) -> str:
    for candidate in (preferred, *aliases):
        if candidate in frame.columns:
            return candidate
    raise KeyError(f"Missing required column: {preferred}")


def _make_treatment(
    frame: pd.DataFrame,
    *,
    threshold: int,
    floor_col: str = "floor",
    treatment_col: str = "treatment",
) -> pd.Series:
    try:
        actual_floor = _resolve_optional_column(frame, floor_col, ("Floor", "floors"))
        return (pd.to_numeric(frame[actual_floor], errors="coerce") >= threshold).astype(float)
    except KeyError:
        actual_treatment = _resolve_optional_column(frame, treatment_col, ("high_rise",))
        return pd.to_numeric(frame[actual_treatment], errors="coerce")


def _coerce_analysis_frame(
    frame: pd.DataFrame,
    *,
    threshold: int,
    outcome_col: str,
    covariates: Iterable[str],
    floor_col: str = "floor",
    treatment_col: str = "treatment",
) -> pd.DataFrame:
    actual_outcome = _resolve_optional_column(frame, outcome_col, ("lst", "LST"))
    columns = list(dict.fromkeys([actual_outcome, *covariates]))
    prepared = frame.copy()
    prepared["_outcome"] = pd.to_numeric(prepared[actual_outcome], errors="coerce")
    prepared["_treatment"] = _make_treatment(
        prepared,
        threshold=threshold,
        floor_col=floor_col,
        treatment_col=treatment_col,
    )
    for column in covariates:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    required = ["_outcome", "_treatment", *covariates]
    return prepared.dropna(subset=required).copy()


def _smd(treated_values: np.ndarray, control_values: np.ndarray) -> float:
    treated_values = np.asarray(treated_values, dtype=float)
    control_values = np.asarray(control_values, dtype=float)
    if treated_values.size == 0 or control_values.size == 0:
        return np.nan
    pooled = np.sqrt((np.var(treated_values) + np.var(control_values)) / 2.0)
    diff = float(np.mean(treated_values) - np.mean(control_values))
    if pooled < 1e-12:
        return 0.0 if abs(diff) < 1e-12 else np.inf
    return diff / pooled


def _bootstrap_ci(diffs: np.ndarray, n_bootstrap: int, rng: np.random.Generator) -> tuple[float, float, float]:
    diffs = np.asarray(diffs, dtype=float)
    if diffs.size == 0:
        return np.nan, np.nan, np.nan
    if diffs.size == 1 or n_bootstrap <= 0:
        se = 0.0
        return float(diffs.mean()), float(diffs.mean()), se
    estimates = []
    for _ in range(n_bootstrap):
        idx = rng.choice(diffs.size, size=diffs.size, replace=True)
        estimates.append(float(diffs[idx].mean()))
    values = np.asarray(estimates, dtype=float)
    return (
        float(np.percentile(values, 2.5)),
        float(np.percentile(values, 97.5)),
        float(values.std(ddof=1)),
    )


def _raw_ablation(
    frame: pd.DataFrame,
    *,
    threshold: int,
    outcome_col: str,
    n_bootstrap: int,
    random_state: int,
) -> tuple[dict[str, Any], pd.DataFrame, dict[str, Any], dict[str, Any]]:
    rng = np.random.default_rng(random_state)
    prepared = _coerce_analysis_frame(
        frame,
        threshold=threshold,
        outcome_col=outcome_col,
        covariates=(),
    )
    treated = prepared.loc[prepared["_treatment"] == 1, "_outcome"].to_numpy(dtype=float)
    control = prepared.loc[prepared["_treatment"] == 0, "_outcome"].to_numpy(dtype=float)
    if treated.size == 0 or control.size == 0:
        att = ci_lower = ci_upper = se = np.nan
        status = "skipped"
        diffs = np.asarray([], dtype=float)
    else:
        att = float(treated.mean() - control.mean())
        status = "ok"
        if n_bootstrap > 0:
            estimates = []
            for _ in range(n_bootstrap):
                t_idx = rng.choice(treated.size, size=treated.size, replace=True)
                c_idx = rng.choice(control.size, size=control.size, replace=True)
                estimates.append(float(treated[t_idx].mean() - control[c_idx].mean()))
            boot = np.asarray(estimates, dtype=float)
            ci_lower = float(np.percentile(boot, 2.5))
            ci_upper = float(np.percentile(boot, 97.5))
            se = float(boot.std(ddof=1)) if boot.size > 1 else 0.0
        else:
            diffs = np.asarray([att], dtype=float)
            ci_lower, ci_upper, se = _bootstrap_ci(diffs, 0, rng)

    row = {
        "variant": "raw",
        "threshold": int(threshold),
        "estimator": "raw_difference",
        "status": status,
        "n_total": int(len(frame)),
        "complete_n": int(len(prepared)),
        "common_support_n": int(len(prepared)),
        "att": att,
        "se": se,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "caliper": np.nan,
        "caliper_abs": np.nan,
        "max_pre_smd": np.nan,
        "max_post_smd": np.nan,
        "balance_pass_0_1": False,
        "matched_treated_n": int(treated.size),
        "matched_control_n": int(control.size),
    }
    counts = {
        "variant": "raw",
        "threshold": int(threshold),
        "n_total": int(len(frame)),
        "complete_n": int(len(prepared)),
        "n_common_support": int(len(prepared)),
        "common_support_n": int(len(prepared)),
        "treated_n": int(treated.size),
        "control_n": int(control.size),
        "common_treated_n": int(treated.size),
        "common_control_n": int(control.size),
        "matched_treated_n": int(treated.size),
        "matched_control_n": int(control.size),
        "unmatched_treated_n": 0,
        "drop_rate": 0.0,
    }
    return row, pd.DataFrame(), counts, {"prepared": prepared, "matched_indices": prepared.index.to_numpy()}


def _standardized_matrix(frame: pd.DataFrame, covariates: list[str]) -> np.ndarray:
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    return scaler.fit_transform(frame[covariates].to_numpy(dtype=float))


def _propensity_scores(x_scaled: np.ndarray, treatment: np.ndarray) -> np.ndarray:
    from sklearn.linear_model import LogisticRegression

    if len(np.unique(treatment)) < 2:
        return np.full_like(treatment, fill_value=np.nan, dtype=float)
    try:
        model = LogisticRegression(max_iter=2000, solver="lbfgs")
        model.fit(x_scaled, treatment.astype(int))
        return model.predict_proba(x_scaled)[:, 1]
    except Exception:
        return np.full(treatment.shape, float(np.mean(treatment)), dtype=float)


def _add_pca_context(frame: pd.DataFrame, *, random_state: int) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    working = frame.copy()
    geometry = resolve_feature_columns(working, GEOMETRY_COLUMNS)
    remote_names = (*SENTINEL_BAND_COLUMNS, *SENTINEL_INDEX_COLUMNS, *TERRAIN_COLUMNS)
    remote = []
    for name in remote_names:
        try:
            remote.extend(resolve_feature_columns(working, (name,)))
        except KeyError:
            continue
    remote = list(dict.fromkeys(remote))
    if not remote:
        return working, geometry, {"pca_components": 0, "pca_explained_variance": 0.0}

    numeric = working[remote].apply(pd.to_numeric, errors="coerce")
    numeric = numeric.fillna(numeric.median(numeric_only=True))
    x_scaled = StandardScaler().fit_transform(numeric.to_numpy(dtype=float))
    max_components = min(x_scaled.shape[0], x_scaled.shape[1])
    if max_components <= 1:
        working["pca_context_1"] = x_scaled[:, 0] if x_scaled.shape[1] else 0.0
        return working, [*geometry, "pca_context_1"], {
            "pca_components": 1,
            "pca_explained_variance": 1.0,
        }
    pca = PCA(n_components=0.95, svd_solver="full", random_state=random_state)
    components = pca.fit_transform(x_scaled)
    pca_columns = []
    for idx in range(components.shape[1]):
        column = f"pca_context_{idx + 1}"
        working[column] = components[:, idx]
        pca_columns.append(column)
    return working, [*geometry, *pca_columns], {
        "pca_components": int(components.shape[1]),
        "pca_explained_variance": float(pca.explained_variance_ratio_.sum()),
    }


def _variant_frame_and_covariates(
    frame: pd.DataFrame,
    variant: str,
    *,
    random_state: int,
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    if variant == "pca_context":
        return _add_pca_context(frame, random_state=random_state)
    if variant not in FEATURE_SPECS:
        raise ValueError(f"Unknown Chongqing UHI variant: {variant}")
    return frame.copy(), resolve_feature_columns(frame, FEATURE_SPECS[variant]), {}


def _match_variant(
    frame: pd.DataFrame,
    *,
    variant: str,
    threshold: int,
    caliper: float,
    n_bootstrap: int,
    random_state: int,
    outcome_col: str,
) -> tuple[dict[str, Any], pd.DataFrame, dict[str, Any], dict[str, Any]]:
    if variant == "raw":
        return _raw_ablation(
            frame,
            threshold=threshold,
            outcome_col=outcome_col,
            n_bootstrap=n_bootstrap,
            random_state=random_state,
        )

    rng = np.random.default_rng(random_state)
    working, covariates, extra = _variant_frame_and_covariates(
        frame,
        variant,
        random_state=random_state,
    )
    prepared = _coerce_analysis_frame(
        working,
        threshold=threshold,
        outcome_col=outcome_col,
        covariates=covariates,
    )
    treatment = prepared["_treatment"].to_numpy(dtype=int)
    row_base = {
        "variant": variant,
        "threshold": int(threshold),
        "estimator": "psm_nearest_caliper",
        "n_total": int(len(frame)),
        "complete_n": int(len(prepared)),
        "caliper": float(caliper),
        **extra,
    }
    if len(prepared) < 4 or len(np.unique(treatment)) < 2:
        row = {
            **row_base,
            "status": "skipped",
            "common_support_n": 0,
            "att": np.nan,
            "se": np.nan,
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "caliper_abs": np.nan,
            "max_pre_smd": np.nan,
            "max_post_smd": np.nan,
            "balance_pass_0_1": False,
            "matched_treated_n": 0,
            "matched_control_n": 0,
        }
        counts = {
            "variant": variant,
            "threshold": int(threshold),
            "n_total": int(len(frame)),
            "complete_n": int(len(prepared)),
            "n_common_support": 0,
            "common_support_n": 0,
            "treated_n": int((treatment == 1).sum()),
            "control_n": int((treatment == 0).sum()),
            "common_treated_n": 0,
            "common_control_n": 0,
            "matched_treated_n": 0,
            "matched_control_n": 0,
            "unmatched_treated_n": 0,
            "drop_rate": 1.0,
        }
        return row, pd.DataFrame(), counts, {"prepared": prepared, "matched_indices": np.asarray([], dtype=int)}

    x_scaled = _standardized_matrix(prepared, covariates)
    ps = _propensity_scores(x_scaled, treatment)
    prepared["_propensity_score"] = ps
    standardized = pd.DataFrame(
        x_scaled,
        columns=[f"_z_{idx}" for idx in range(x_scaled.shape[1])],
        index=prepared.index,
    )
    prepared = prepared.join(standardized)
    t_mask = treatment == 1
    c_mask = treatment == 0
    support_low = max(float(np.nanmin(ps[t_mask])), float(np.nanmin(ps[c_mask])))
    support_high = min(float(np.nanmax(ps[t_mask])), float(np.nanmax(ps[c_mask])))
    support = prepared[(prepared["_propensity_score"] >= support_low) & (prepared["_propensity_score"] <= support_high)].copy()
    support_t = support[support["_treatment"] == 1]
    support_c = support[support["_treatment"] == 0]
    common_treated_n = int(len(support_t))
    common_control_n = int(len(support_c))

    pre_rows = []
    original_t = prepared[prepared["_treatment"] == 1]
    original_c = prepared[prepared["_treatment"] == 0]
    for covariate in covariates:
        pre_rows.append(
            {
                "variant": variant,
                "threshold": int(threshold),
                "covariate": covariate,
                "pre_smd": abs(_smd(original_t[covariate], original_c[covariate])),
            }
        )

    ps_std = float(np.nanstd(ps))
    caliper_abs = max(float(caliper) * ps_std, 1e-8)
    if support_t.empty or support_c.empty:
        matched_t = support_t.iloc[0:0]
        matched_c = support_c.iloc[0:0]
    else:
        z_columns = [column for column in prepared.columns if column.startswith("_z_")]
        available_controls = support_c.copy()
        matched_t_rows = []
        matched_c_rows = []
        for _, treated_row in support_t.sort_values("_propensity_score").iterrows():
            if available_controls.empty:
                break
            deltas = (available_controls["_propensity_score"] - treated_row["_propensity_score"]).abs()
            candidate_mask = deltas <= caliper_abs
            candidates = available_controls.loc[candidate_mask].copy()
            if candidates.empty:
                continue
            candidates["_ps_delta"] = deltas.loc[candidates.index]
            if z_columns:
                treated_vector = treated_row[z_columns].to_numpy(dtype=float)
                candidate_matrix = candidates[z_columns].to_numpy(dtype=float)
                candidates["_covariate_distance"] = np.sqrt(
                    np.sum((candidate_matrix - treated_vector) ** 2, axis=1)
                )
            else:
                candidates["_covariate_distance"] = 0.0
            selected = candidates.sort_values(
                ["_ps_delta", "_covariate_distance"]
            ).iloc[0]
            matched_t_rows.append(treated_row)
            matched_c_rows.append(available_controls.loc[selected.name])
            available_controls = available_controls.drop(index=selected.name)
        matched_t = pd.DataFrame(matched_t_rows)
        matched_c = pd.DataFrame(matched_c_rows)

    if matched_t.empty:
        att = se = ci_lower = ci_upper = np.nan
        status = "skipped"
        diffs = np.asarray([], dtype=float)
    else:
        diffs = matched_t["_outcome"].to_numpy(dtype=float) - matched_c["_outcome"].to_numpy(dtype=float)
        att = float(diffs.mean())
        ci_lower, ci_upper, se = _bootstrap_ci(diffs, n_bootstrap, rng)
        status = "ok"

    balance_rows = []
    post_smds = []
    for item in pre_rows:
        covariate = item["covariate"]
        post_smd = (
            abs(_smd(matched_t[covariate], matched_c[covariate]))
            if not matched_t.empty
            else np.nan
        )
        post_smds.append(post_smd)
        balance_rows.append(
            {
                **item,
                "post_smd": post_smd,
                "balance_pass_0_1": bool(np.isfinite(post_smd) and post_smd < 0.1),
            }
        )
    balance = pd.DataFrame(balance_rows)
    max_pre_smd = float(np.nanmax([row["pre_smd"] for row in pre_rows])) if pre_rows else np.nan
    finite_post = [value for value in post_smds if np.isfinite(value)]
    max_post_smd = float(max(finite_post)) if finite_post else np.nan
    balance_pass = bool(np.isfinite(max_post_smd) and max_post_smd < 0.1)

    counts = {
        "variant": variant,
        "threshold": int(threshold),
        "n_total": int(len(frame)),
        "complete_n": int(len(prepared)),
        "n_common_support": int(len(support)),
        "common_support_n": int(len(support)),
        "treated_n": int(t_mask.sum()),
        "control_n": int(c_mask.sum()),
        "common_treated_n": common_treated_n,
        "common_control_n": common_control_n,
        "matched_treated_n": int(len(matched_t)),
        "matched_control_n": int(len(matched_c)),
        "unmatched_treated_n": int(max(common_treated_n - len(matched_t), 0)),
        "drop_rate": float(1.0 - (len(matched_t) / common_treated_n)) if common_treated_n else 1.0,
    }
    row = {
        **row_base,
        "status": status,
        "common_support_n": int(len(support)),
        "att": att,
        "se": se,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "caliper_abs": caliper_abs,
        "max_pre_smd": max_pre_smd,
        "max_post_smd": max_post_smd,
        "balance_pass_0_1": balance_pass,
        "matched_treated_n": int(len(matched_t)),
        "matched_control_n": int(len(matched_c)),
    }
    matched_indices = np.concatenate([matched_t.index.to_numpy(), matched_c.index.to_numpy()])
    return row, balance, counts, {
        "prepared": prepared,
        "support": support,
        "matched_treated": matched_t,
        "matched_control": matched_c,
        "matched_indices": matched_indices,
        "covariates": covariates,
    }


def run_psm_ablation(
    frame: pd.DataFrame,
    *,
    threshold: int = 10,
    caliper: float = 0.2,
    n_bootstrap: int = 200,
    random_state: int = 0,
    outcome_col: str = "LST",
    variants: Iterable[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run Chongqing UHI PSM ablations with balance and matched-count outputs."""
    if variants is None:
        variants = FEATURE_SPECS.keys()
    rows = []
    balance_parts = []
    count_rows = []
    for offset, variant in enumerate(variants):
        row, balance, counts, _ = _match_variant(
            frame,
            variant=variant,
            threshold=threshold,
            caliper=caliper,
            n_bootstrap=n_bootstrap,
            random_state=random_state + offset,
            outcome_col=outcome_col,
        )
        rows.append(row)
        if not balance.empty:
            balance_parts.append(balance)
        count_rows.append(counts)
    return (
        pd.DataFrame(rows),
        pd.concat(balance_parts, ignore_index=True) if balance_parts else pd.DataFrame(),
        pd.DataFrame(count_rows),
    )


def run_threshold_placebos(
    frame: pd.DataFrame,
    *,
    thresholds: Iterable[int] = (8, 10, 12),
    variants: Iterable[str] = ("pre_treatment", "full_rs_context"),
    caliper: float = 0.2,
    n_bootstrap: int = 100,
    random_state: int = 0,
    outcome_col: str = "LST",
) -> pd.DataFrame:
    rows = []
    for offset, threshold in enumerate(thresholds):
        ablation, _, _ = run_psm_ablation(
            frame,
            threshold=int(threshold),
            caliper=caliper,
            n_bootstrap=n_bootstrap,
            random_state=random_state + offset * 100,
            outcome_col=outcome_col,
            variants=variants,
        )
        rows.append(ablation)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _grid_blocks(frame: pd.DataFrame, *, block_size_m: float) -> pd.Series:
    x_col, y_col = resolve_feature_columns(frame, ("centroid_x", "centroid_y"))
    x = pd.to_numeric(frame[x_col], errors="coerce")
    y = pd.to_numeric(frame[y_col], errors="coerce")
    mean_lat = float(y.mean()) if y.notna().any() else 0.0
    x_m = (x - x.min()) * 111_000.0 * max(np.cos(np.deg2rad(mean_lat)), 0.1)
    y_m = (y - y.min()) * 111_000.0
    bx = np.floor(x_m / max(block_size_m, 1.0)).astype("Int64")
    by = np.floor(y_m / max(block_size_m, 1.0)).astype("Int64")
    return bx.astype(str) + "_" + by.astype(str)


def run_spatial_block_bootstrap(
    frame: pd.DataFrame,
    *,
    variants: Iterable[str] = ("terrain",),
    threshold: int = 10,
    n_replicates: int = 200,
    caliper: float = 0.2,
    random_state: int = 0,
    block_size_m: float = 2000.0,
    outcome_col: str = "LST",
) -> pd.DataFrame:
    rng = np.random.default_rng(random_state)
    working = frame.copy()
    working["_uhi_grid_block"] = _grid_blocks(working, block_size_m=block_size_m)
    blocks = working["_uhi_grid_block"].dropna().astype(str).unique()
    rows = []
    for variant_offset, variant in enumerate(variants):
        try:
            _, _, _, details = _match_variant(
                working,
                variant=variant,
                threshold=threshold,
                caliper=caliper,
                n_bootstrap=0,
                random_state=random_state + variant_offset,
                outcome_col=outcome_col,
            )
            matched_t = details.get("matched_treated", pd.DataFrame())
            matched_c = details.get("matched_control", pd.DataFrame())
            if matched_t.empty or matched_c.empty:
                pair_table = pd.DataFrame(columns=["block", "diff"])
            else:
                pair_table = pd.DataFrame(
                    {
                        "block": matched_t["_uhi_grid_block"].astype(str).to_numpy(),
                        "diff": (
                            matched_t["_outcome"].to_numpy(dtype=float)
                            - matched_c["_outcome"].to_numpy(dtype=float)
                        ),
                    }
                )
        except Exception:
            pair_table = pd.DataFrame(columns=["block", "diff"])

        pair_blocks = pair_table["block"].dropna().astype(str).unique()
        block_count = int(len(pair_blocks) if len(pair_blocks) else len(blocks))
        for replicate in range(n_replicates):
            try:
                if pair_table.empty or len(pair_blocks) == 0:
                    raise ValueError("No matched pairs available for block bootstrap.")
                sampled_blocks = rng.choice(pair_blocks, size=len(pair_blocks), replace=True)
                sampled_diffs = [
                    pair_table.loc[pair_table["block"] == block, "diff"].to_numpy(dtype=float)
                    for block in sampled_blocks
                ]
                diffs = np.concatenate(sampled_diffs) if sampled_diffs else np.asarray([], dtype=float)
                if diffs.size == 0:
                    raise ValueError("Sampled blocks contained no matched pairs.")
                rows.append(
                    {
                        "variant": variant,
                        "threshold": int(threshold),
                        "replicate": int(replicate),
                        "block_count": block_count,
                        "sampled_block_count": int(len(sampled_blocks)),
                        "att": float(diffs.mean()),
                        "matched_treated_n": int(len(pair_table)),
                        "matched_control_n": int(len(pair_table)),
                        "status": "ok",
                    }
                )
            except Exception as exc:
                rows.append(
                    {
                        "variant": variant,
                        "threshold": int(threshold),
                        "replicate": int(replicate),
                        "block_count": block_count,
                        "sampled_block_count": 0,
                        "att": np.nan,
                        "matched_treated_n": 0,
                        "matched_control_n": 0,
                        "status": f"error: {exc}",
                    }
                )
    return pd.DataFrame(rows)


def _ols_residuals(frame: pd.DataFrame, outcome: str, columns: list[str]) -> np.ndarray:
    y = frame[outcome].to_numpy(dtype=float)
    x = frame[columns].to_numpy(dtype=float)
    x = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    return y - x @ beta


def _moran_i(
    residuals: np.ndarray,
    coords: np.ndarray,
    *,
    n_permutations: int,
    rng: np.random.Generator,
) -> tuple[float, float, float]:
    n = len(residuals)
    if n < 3:
        return np.nan, np.nan, np.nan
    z = residuals - residuals.mean()
    denom = float(np.sum(z**2))
    if denom <= 1e-12:
        return 0.0, 1.0, 0.0
    diffs = coords[:, None, :] - coords[None, :, :]
    distances = np.sqrt(np.sum(diffs**2, axis=2))
    positive = distances[distances > 0]
    if positive.size == 0:
        return 0.0, 1.0, 0.0
    distance_band = float(np.percentile(positive, 25))
    weights = ((distances > 0) & (distances <= distance_band)).astype(float)
    if weights.sum() == 0:
        weights = (distances > 0).astype(float)
        distance_band = float(np.max(positive))
    weight_sum = float(weights.sum())

    def statistic(values: np.ndarray) -> float:
        centered = values - values.mean()
        local_denom = float(np.sum(centered**2))
        if local_denom <= 1e-12:
            return 0.0
        return float(n / weight_sum * np.sum(weights * np.outer(centered, centered)) / local_denom)

    observed = statistic(z)
    if n_permutations <= 0:
        return observed, np.nan, distance_band
    permuted = []
    for _ in range(n_permutations):
        permuted.append(statistic(rng.permutation(z)))
    permuted_values = np.asarray(permuted, dtype=float)
    p_value = float((np.sum(np.abs(permuted_values) >= abs(observed)) + 1) / (len(permuted_values) + 1))
    return observed, p_value, distance_band


def run_residual_spatial_diagnostics(
    frame: pd.DataFrame,
    *,
    variants: Iterable[str] = ("terrain", "full_rs_context"),
    threshold: int = 10,
    caliper: float = 0.2,
    random_state: int = 0,
    n_permutations: int = 99,
    outcome_col: str = "LST",
) -> pd.DataFrame:
    rng = np.random.default_rng(random_state)
    rows = []
    x_col, y_col = resolve_feature_columns(frame, ("centroid_x", "centroid_y"))
    for offset, variant in enumerate(variants):
        try:
            row, _, _, details = _match_variant(
                frame,
                variant=variant,
                threshold=threshold,
                caliper=caliper,
                n_bootstrap=0,
                random_state=random_state + offset,
                outcome_col=outcome_col,
            )
            matched_indices = details.get("matched_indices", np.asarray([], dtype=int))
            prepared = details["prepared"]
            matched = prepared.loc[pd.Index(matched_indices).unique()].copy()
            covariates = list(details.get("covariates", []))
            if matched.empty or not covariates:
                raise ValueError("No matched rows available for residual diagnostics.")
            residual_columns = ["_treatment", *covariates]
            residuals = _ols_residuals(matched, "_outcome", residual_columns)
            coords = matched[[x_col, y_col]].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
            mean_lat = float(np.nanmean(coords[:, 1])) if len(coords) else 0.0
            coords_m = np.column_stack(
                [
                    (coords[:, 0] - np.nanmin(coords[:, 0])) * 111_000.0 * max(np.cos(np.deg2rad(mean_lat)), 0.1),
                    (coords[:, 1] - np.nanmin(coords[:, 1])) * 111_000.0,
                ]
            )
            moran, p_value, distance_band = _moran_i(
                residuals,
                coords_m,
                n_permutations=n_permutations,
                rng=rng,
            )
            rows.append(
                {
                    "variant": variant,
                    "threshold": int(threshold),
                    "moran_i": moran,
                    "permutation_p_value": p_value,
                    "n": int(len(matched)),
                    "distance_band": distance_band,
                    "matched_treated_n": row.get("matched_treated_n"),
                    "matched_control_n": row.get("matched_control_n"),
                    "status": "ok",
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "variant": variant,
                    "threshold": int(threshold),
                    "moran_i": np.nan,
                    "permutation_p_value": np.nan,
                    "n": 0,
                    "distance_band": np.nan,
                    "matched_treated_n": 0,
                    "matched_control_n": 0,
                    "status": f"error: {exc}",
                }
            )
    return pd.DataFrame(rows)


def assign_lst_pixels(
    frame: pd.DataFrame,
    *,
    cell_size_m: float = 1000.0,
    outcome_col: str = "LST",
) -> pd.Series:
    """Assign each building to a coarse outcome pixel.

    The Chongqing outcome (summer LST) is retrieved on a ~1 km MODIS grid, so
    many buildings share one outcome pixel. We recover that shared-pixel
    structure with a coordinate grid at ``cell_size_m``. Where an exact outcome
    value is shared by several buildings (the common case for a coarse thermal
    product), buildings with the same rounded outcome inside a grid cell are
    treated as one pixel. The returned Series is a stable pixel id per row.
    """
    x_col, y_col = resolve_feature_columns(frame, ("centroid_x", "centroid_y"))
    x = pd.to_numeric(frame[x_col], errors="coerce")
    y = pd.to_numeric(frame[y_col], errors="coerce")
    mean_lat = float(y.mean()) if y.notna().any() else 0.0
    x_m = (x - x.min()) * 111_000.0 * max(np.cos(np.deg2rad(mean_lat)), 0.1)
    y_m = (y - y.min()) * 111_000.0
    gx = np.floor(x_m / max(cell_size_m, 1.0)).astype("Int64")
    gy = np.floor(y_m / max(cell_size_m, 1.0)).astype("Int64")
    outcome = _resolve_optional_column(frame, outcome_col, ("lst", "LST"))
    # Round the outcome to 3 dp so identical retrieved pixel values collapse.
    lst_key = pd.to_numeric(frame[outcome], errors="coerce").round(3)
    return gx.astype(str) + "_" + gy.astype(str) + "_" + lst_key.astype(str)


def _cluster_robust_ols(
    y: np.ndarray,
    X: np.ndarray,
    clusters: np.ndarray,
) -> dict[str, float]:
    """OLS with CR1 cluster-robust (clustered) standard errors.

    Returns the treatment coefficient (column 1, after intercept) with a
    cluster-robust standard error and a 95% normal-approximation CI. Clustering
    on the shared outcome pixel corrects the naive building-level SE for the
    fact that many buildings share one outcome measurement.
    """
    n, k = X.shape
    XtX = X.T @ X
    XtX_inv = np.linalg.pinv(XtX)
    beta = XtX_inv @ (X.T @ y)
    resid = y - X @ beta
    uniq = np.unique(clusters)
    g = len(uniq)
    meat = np.zeros((k, k))
    for c in uniq:
        mask = clusters == c
        Xc = X[mask]
        uc = resid[mask]
        sc = Xc.T @ uc
        meat += np.outer(sc, sc)
    # CR1 small-sample correction.
    dof_scale = (g / max(g - 1, 1)) * ((n - 1) / max(n - k, 1))
    cov = dof_scale * (XtX_inv @ meat @ XtX_inv)
    se = float(np.sqrt(max(cov[1, 1], 0.0)))
    coef = float(beta[1])
    return {
        "coef": coef,
        "cluster_robust_se": se,
        "ci_lower": coef - 1.96 * se,
        "ci_upper": coef + 1.96 * se,
        "n_clusters": int(g),
        "n_obs": int(n),
    }


def run_change_of_support_analysis(
    frame: pd.DataFrame,
    *,
    variants: Iterable[str] = ("pre_treatment", "full_rs_context"),
    threshold: int = 10,
    cell_size_m: float = 1000.0,
    outcome_col: str = "LST",
    random_state: int = 0,
) -> pd.DataFrame:
    """Quantify how the building-level ATT changes under change of support.

    For each adjustment variant we report three estimands that make the
    treatment/outcome scale mismatch explicit:

    1. ``building_naive`` -- adjusted OLS at the building level, ignoring the
       fact that ~7 buildings share one outcome pixel (over-states precision).
    2. ``building_cluster_robust`` -- the same point estimate with standard
       errors clustered on the shared outcome pixel.
    3. ``pixel_aggregated`` -- one row per outcome pixel (pixel-mean treatment
       share vs pixel outcome), the estimand that is actually identified at the
       outcome resolution.

    The gap between (1) and (2)/(3) is the reviewer-flagged change-of-support
    problem, now measured rather than only acknowledged.
    """
    rows: list[dict[str, Any]] = []
    working = frame.copy()
    working["_pixel"] = assign_lst_pixels(
        working, cell_size_m=cell_size_m, outcome_col=outcome_col
    )
    for variant in variants:
        try:
            v_frame, covariates, _ = _variant_frame_and_covariates(
                working, variant, random_state=random_state
            )
            v_frame["_pixel"] = working.loc[v_frame.index, "_pixel"].to_numpy()
            prepared = _coerce_analysis_frame(
                v_frame,
                threshold=threshold,
                outcome_col=outcome_col,
                covariates=covariates,
            )
            prepared["_pixel"] = v_frame.loc[prepared.index, "_pixel"].to_numpy()
            n_buildings = int(len(prepared))
            n_pixels = int(prepared["_pixel"].nunique())

            # (1)+(2) building-level adjusted OLS with cluster-robust SE.
            y = prepared["_outcome"].to_numpy(dtype=float)
            design = np.column_stack(
                [
                    np.ones(len(prepared)),
                    prepared["_treatment"].to_numpy(dtype=float),
                    prepared[covariates].to_numpy(dtype=float),
                ]
            )
            clusters = pd.factorize(prepared["_pixel"])[0]
            cr = _cluster_robust_ols(y, design, clusters)
            # naive (iid) SE for the same coefficient.
            resid = y - design @ (np.linalg.pinv(design.T @ design) @ (design.T @ y))
            sigma2 = float(resid @ resid) / max(len(y) - design.shape[1], 1)
            naive_cov = sigma2 * np.linalg.pinv(design.T @ design)
            naive_se = float(np.sqrt(max(naive_cov[1, 1], 0.0)))

            rows.append(
                {
                    "variant": variant,
                    "estimand": "building_naive",
                    "att": cr["coef"],
                    "se": naive_se,
                    "ci_lower": cr["coef"] - 1.96 * naive_se,
                    "ci_upper": cr["coef"] + 1.96 * naive_se,
                    "n_units": n_buildings,
                    "n_pixels": n_pixels,
                    "buildings_per_pixel": round(n_buildings / max(n_pixels, 1), 3),
                }
            )
            rows.append(
                {
                    "variant": variant,
                    "estimand": "building_cluster_robust",
                    "att": cr["coef"],
                    "se": cr["cluster_robust_se"],
                    "ci_lower": cr["ci_lower"],
                    "ci_upper": cr["ci_upper"],
                    "n_units": n_buildings,
                    "n_pixels": n_pixels,
                    "buildings_per_pixel": round(n_buildings / max(n_pixels, 1), 3),
                }
            )

            # (3) pixel-aggregated estimand: collapse to one row per pixel.
            agg_cols = {c: "mean" for c in covariates}
            agg_cols["_outcome"] = "mean"
            agg_cols["_treatment"] = "mean"
            pix = prepared.groupby("_pixel").agg(agg_cols)
            if len(pix) >= 5 and pix["_treatment"].nunique() > 1:
                yp = pix["_outcome"].to_numpy(dtype=float)
                Xp = np.column_stack(
                    [
                        np.ones(len(pix)),
                        pix["_treatment"].to_numpy(dtype=float),
                        pix[covariates].to_numpy(dtype=float),
                    ]
                )
                betap = np.linalg.pinv(Xp.T @ Xp) @ (Xp.T @ yp)
                rp = yp - Xp @ betap
                s2p = float(rp @ rp) / max(len(yp) - Xp.shape[1], 1)
                covp = s2p * np.linalg.pinv(Xp.T @ Xp)
                sep = float(np.sqrt(max(covp[1, 1], 0.0)))
                rows.append(
                    {
                        "variant": variant,
                        "estimand": "pixel_aggregated",
                        "att": float(betap[1]),
                        "se": sep,
                        "ci_lower": float(betap[1]) - 1.96 * sep,
                        "ci_upper": float(betap[1]) + 1.96 * sep,
                        "n_units": int(len(pix)),
                        "n_pixels": int(len(pix)),
                        "buildings_per_pixel": round(n_buildings / max(n_pixels, 1), 3),
                    }
                )
        except Exception as exc:  # pragma: no cover - defensive
            rows.append(
                {
                    "variant": variant,
                    "estimand": "error",
                    "att": np.nan,
                    "se": np.nan,
                    "ci_lower": np.nan,
                    "ci_upper": np.nan,
                    "n_units": 0,
                    "n_pixels": 0,
                    "buildings_per_pixel": np.nan,
                    "status": f"error: {exc}",
                }
            )
    return pd.DataFrame(rows)


def run_chongqing_uhi_analysis(
    frame: pd.DataFrame,
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    threshold: int = 10,
    caliper: float = 0.2,
    n_bootstrap: int = 200,
    n_spatial_bootstrap: int = 200,
    random_state: int = 0,
    outcome_col: str = "LST",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the full Chongqing UHI ablation and robustness suite."""
    ablation, balance, matched_counts = run_psm_ablation(
        frame,
        threshold=threshold,
        caliper=caliper,
        n_bootstrap=n_bootstrap,
        random_state=random_state,
        outcome_col=outcome_col,
    )
    bootstrap = run_spatial_block_bootstrap(
        frame,
        variants=("terrain", "full_rs_context"),
        threshold=threshold,
        n_replicates=n_spatial_bootstrap,
        caliper=caliper,
        random_state=random_state,
        outcome_col=outcome_col,
    )
    placebos = run_threshold_placebos(
        frame,
        thresholds=(8, 10, 12),
        caliper=caliper,
        n_bootstrap=max(20, min(n_bootstrap, 100)),
        random_state=random_state,
        outcome_col=outcome_col,
    )
    residuals = run_residual_spatial_diagnostics(
        frame,
        variants=("terrain", "pre_treatment", "full_rs_context"),
        threshold=threshold,
        caliper=caliper,
        random_state=random_state,
        outcome_col=outcome_col,
    )
    change_of_support = run_change_of_support_analysis(
        frame,
        variants=("pre_treatment", "full_rs_context"),
        threshold=threshold,
        outcome_col=outcome_col,
        random_state=random_state,
    )
    manifest_metadata = {
        "sample_size": int(len(frame)),
        "treatment_threshold": int(threshold),
        "caliper": float(caliper),
        "n_bootstrap": int(n_bootstrap),
        "n_spatial_bootstrap": int(n_spatial_bootstrap),
        **(metadata or {}),
    }
    return write_chongqing_outputs(
        output_dir=output_dir,
        ablation=ablation,
        balance=balance,
        matched_counts=matched_counts,
        bootstrap=bootstrap,
        placebos=placebos,
        residual_diagnostics=residuals,
        change_of_support=change_of_support,
        metadata=manifest_metadata,
    )


def _balance_interpretation(ablation: pd.DataFrame) -> str:
    if "max_post_smd" not in ablation.columns:
        return "not_evaluated"
    max_smd = pd.to_numeric(ablation["max_post_smd"], errors="coerce").dropna()
    if max_smd.empty:
        return "not_evaluated"
    if (max_smd < 0.1).any():
        return "credible_balance"
    if (max_smd < 0.25).any():
        return "bounded_balance"
    return "failed_balance"


def _render_report(ablation: pd.DataFrame, metadata: dict[str, Any]) -> str:
    interpretation = _balance_interpretation(ablation)
    lines = [
        "# Chongqing UHI Ablation and Robustness Report",
        "",
        f"- Balance interpretation: `{interpretation}`",
        f"- Sample size: `{metadata.get('sample_size', 'unknown')}`",
        f"- Treatment threshold: `{metadata.get('treatment_threshold', 'unknown')}` floors",
        "",
        "## Ablation Rows",
        "",
    ]
    for _, row in ablation.iterrows():
        variant = row.get("variant", "unknown")
        att = row.get("att", None)
        max_post_smd = row.get("max_post_smd", None)
        lines.append(f"- `{variant}`: ATT `{att}`, max post-match SMD `{max_post_smd}`")
    return "\n".join(lines) + "\n"


def write_chongqing_outputs(
    *,
    output_dir: str | Path,
    ablation: pd.DataFrame,
    balance: pd.DataFrame,
    matched_counts: pd.DataFrame,
    bootstrap: pd.DataFrame,
    placebos: pd.DataFrame,
    residual_diagnostics: pd.DataFrame,
    change_of_support: pd.DataFrame | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write IJGIS-required Chongqing UHI experiment outputs."""
    metadata = dict(metadata or {})
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    frames = {
        "ablation_csv": ablation,
        "balance_csv": balance,
        "matched_counts_csv": matched_counts,
        "bootstrap_csv": bootstrap,
        "placebo_csv": placebos,
        "residual_csv": residual_diagnostics,
    }
    if change_of_support is not None:
        frames["change_of_support_csv"] = change_of_support
    manifest: dict[str, Any] = {}
    for key, frame in frames.items():
        path = target / OUTPUT_FILES[key]
        frame.to_csv(path, index=False)
        manifest[key] = str(path)

    interpretation = _balance_interpretation(ablation)
    metadata["balance_interpretation"] = interpretation
    report_path = target / OUTPUT_FILES["report_md"]
    report_path.write_text(_render_report(ablation, metadata), encoding="utf-8")

    manifest_path = target / OUTPUT_FILES["manifest_json"]
    manifest.update(
        {
            "manifest_json": str(manifest_path),
            "report_md": str(report_path),
            "metadata": metadata,
            "balance_interpretation": interpretation,
        }
    )
    manifest_path.write_text(
        json.dumps(_json_ready(manifest), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest
