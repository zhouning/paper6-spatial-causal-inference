"""GeoFM / AlphaEarth availability and causal ablation for Paper 6."""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from data_agent.experiments.chongqing_uhi_analysis import (
    DEFAULT_OUTPUT_DIR,
    GEOMETRY_COLUMNS,
    SENTINEL_BAND_COLUMNS,
    SENTINEL_INDEX_COLUMNS,
    TERRAIN_COLUMNS,
    _json_ready,
    run_psm_ablation,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PHASE0_REPORT = PROJECT_ROOT / "scripts" / "phase0_results" / "phase0_results.json"
OUTPUT_FILES = {
    "availability_report_json": "geofm_availability_report.json",
    "causal_ablation_csv": "geofm_causal_ablation.csv",
    "balance_diagnostics_csv": "geofm_balance_diagnostics.csv",
    "manifest_json": "geofm_alphaearth_ablation_manifest.json",
    "report_md": "geofm_alphaearth_ablation_report.md",
    "analysis_sample_csv": "geofm_alphaearth_analysis_sample.csv",
}
VARIANT_COLUMNS = {
    "geometry_only": GEOMETRY_COLUMNS,
    "geometry_rs_context": (
        *GEOMETRY_COLUMNS,
        *SENTINEL_BAND_COLUMNS,
        *SENTINEL_INDEX_COLUMNS,
        *TERRAIN_COLUMNS,
    ),
}
GEOFM_VARIANTS = (
    "geometry_alphaearth_64d",
    "geometry_rs_alphaearth_64d",
    "geometry_alphaearth_pca",
    "geometry_rs_alphaearth_pca",
)


def resolve_geofm_columns(frame: pd.DataFrame) -> list[str]:
    """Resolve 64 AlphaEarth columns across supported naming conventions."""
    patterns = [
        [f"A{idx:02d}" for idx in range(64)],
        [f"rs_A{idx:02d}" for idx in range(64)],
        [f"geofm_{idx:02d}" for idx in range(64)],
        [f"geofm_{idx}" for idx in range(64)],
    ]
    columns = set(frame.columns)
    for pattern in patterns:
        if all(column in columns for column in pattern):
            return pattern
    return []


def _read_phase0_report(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {"available": False, "path": None}
    report_path = Path(path)
    if not report_path.exists():
        return {"available": False, "path": str(report_path)}
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        return {"available": False, "path": str(report_path), "error": str(exc)}
    verdict = payload.get("verdict", {})
    return {
        "available": True,
        "path": str(report_path),
        "overall": verdict.get("overall"),
        "recommendation": verdict.get("recommendation"),
        "criteria": verdict.get("criteria", {}),
    }


def _default_coverage_loader() -> dict[str, Any]:
    try:
        from data_agent.embedding_store import get_coverage

        return get_coverage()
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"total_embeddings": 0, "areas": [], "error": str(exc)}


def _runtime_probe() -> dict[str, Any]:
    try:
        import ee

        ee.Initialize()
        return {"available": True, "status": "ok"}
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"available": False, "status": f"error: {exc}"}


def _attach_geofm_columns(
    frame: pd.DataFrame,
    geofm_values: pd.DataFrame,
) -> pd.DataFrame:
    attached = frame.copy()
    aligned = geofm_values.reindex(attached.index)
    for column in aligned.columns:
        attached[column] = pd.to_numeric(aligned[column], errors="coerce")
    return attached


def _call_geofm_sampler(
    sampler: Callable[..., tuple[pd.DataFrame, dict[str, Any]]],
    frame: pd.DataFrame,
    **kwargs: Any,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    signature = inspect.signature(sampler)
    accepts_kwargs = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )
    if accepts_kwargs:
        return sampler(frame, **kwargs)
    filtered = {key: value for key, value in kwargs.items() if key in signature.parameters}
    return sampler(frame, **filtered)


def _default_geofm_sampler(
    frame: pd.DataFrame,
    *,
    year: int,
    random_state: int,
    batch_size: int = 250,
    max_rows: int | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    try:
        import ee

        from data_agent.world_model import AEF_BANDS, AEF_COLLECTION

        ee.Initialize()
        working = frame.copy()
        if max_rows is not None and len(working) > max_rows:
            working = working.sample(n=max_rows, random_state=random_state).sort_index()
        if working.empty:
            return pd.DataFrame(index=frame.index), {"status": "error: no_points", "year": year, "n_rows": 0}
        xmin = float(pd.to_numeric(working["centroid_x"], errors="coerce").min())
        xmax = float(pd.to_numeric(working["centroid_x"], errors="coerce").max())
        ymin = float(pd.to_numeric(working["centroid_y"], errors="coerce").min())
        ymax = float(pd.to_numeric(working["centroid_y"], errors="coerce").max())
        region = ee.Geometry.Rectangle([xmin, ymin, xmax, ymax])
        img = (
            ee.ImageCollection(AEF_COLLECTION)
            .filterDate(f"{year}-01-01", f"{year + 1}-01-01")
            .filterBounds(region)
            .select(AEF_BANDS)
            .mosaic()
            .clip(region)
        )
        records: dict[str, dict[str, Any]] = {}
        indices = list(working.index)
        batch_size = max(int(batch_size), 1)
        for start in range(0, len(indices), batch_size):
            batch_indices = indices[start : start + batch_size]
            features = []
            for idx, row in working.loc[batch_indices].iterrows():
                pt = ee.Geometry.Point([float(row["centroid_x"]), float(row["centroid_y"])])
                features.append(ee.Feature(pt, {"row_id": str(idx)}))
            fc = ee.FeatureCollection(features)
            sampled = img.sampleRegions(collection=fc, scale=10, geometries=False).getInfo()
            for feature in sampled.get("features", []):
                props = feature.get("properties", {})
                row_id = props.get("row_id")
                if row_id is None:
                    continue
                records[str(row_id)] = {band: props.get(band) for band in AEF_BANDS}
        if not records:
            return pd.DataFrame(index=frame.index), {
                "status": "error: no_samples",
                "year": year,
                "n_rows": int(len(working)),
                "batch_size": batch_size,
                "max_rows": max_rows,
            }
        geofm_frame = pd.DataFrame.from_dict(records, orient="index")
        geofm_frame.index = pd.Index(geofm_frame.index)
        geofm_frame = geofm_frame.reindex(frame.index.astype(str), copy=False)
        geofm_frame.index = frame.index
        complete = int(geofm_frame.dropna(how="any").shape[0])
        return geofm_frame, {
            "status": "ok",
            "year": year,
            "n_rows": int(len(working)),
            "n_sampled_rows": complete,
            "batch_size": batch_size,
            "max_rows": max_rows,
        }
    except Exception as exc:  # pragma: no cover - environment dependent
        return pd.DataFrame(index=frame.index), {
            "status": f"error: {exc}",
            "year": year,
            "n_rows": int(len(frame)),
        }


def _build_alphaearth_pca_frame(
    frame: pd.DataFrame,
    geofm_columns: list[str],
    *,
    random_state: int,
    include_rs_context: bool = False,
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    working = frame.copy()
    numeric = working[geofm_columns].apply(pd.to_numeric, errors="coerce")
    complete_mask = numeric.notna().all(axis=1)
    complete_numeric = numeric.loc[complete_mask]
    if len(complete_numeric) < 2:
        working["alphaearth_pca_1"] = np.nan
        base_columns = [*GEOMETRY_COLUMNS]
        if include_rs_context:
            base_columns.extend(
                [*SENTINEL_BAND_COLUMNS, *SENTINEL_INDEX_COLUMNS, *TERRAIN_COLUMNS]
            )
        return working, [*base_columns, "alphaearth_pca_1"], {
            "pca_components": 0,
            "pca_explained_variance": 0.0,
            "geofm_complete_rows": int(len(complete_numeric)),
        }
    x_scaled = StandardScaler().fit_transform(complete_numeric.to_numpy(dtype=float))
    if x_scaled.shape[1] <= 1:
        working["alphaearth_pca_1"] = np.nan
        working.loc[complete_numeric.index, "alphaearth_pca_1"] = (
            x_scaled[:, 0] if x_scaled.shape[1] else 0.0
        )
        base_columns = [*GEOMETRY_COLUMNS]
        if include_rs_context:
            base_columns.extend(
                [*SENTINEL_BAND_COLUMNS, *SENTINEL_INDEX_COLUMNS, *TERRAIN_COLUMNS]
            )
        return working, [*base_columns, "alphaearth_pca_1"], {
            "pca_components": 1,
            "pca_explained_variance": 1.0,
            "geofm_complete_rows": int(len(complete_numeric)),
        }
    pca = PCA(n_components=0.95, svd_solver="full", random_state=random_state)
    components = pca.fit_transform(x_scaled)
    columns = []
    for idx in range(components.shape[1]):
        name = f"alphaearth_pca_{idx + 1}"
        working[name] = np.nan
        working.loc[complete_numeric.index, name] = components[:, idx]
        columns.append(name)
    base_columns = [*GEOMETRY_COLUMNS]
    if include_rs_context:
        base_columns.extend(
            [*SENTINEL_BAND_COLUMNS, *SENTINEL_INDEX_COLUMNS, *TERRAIN_COLUMNS]
        )
    return working, [*base_columns, *columns], {
        "pca_components": int(components.shape[1]),
        "pca_explained_variance": float(pca.explained_variance_ratio_.sum()),
        "geofm_complete_rows": int(len(complete_numeric)),
    }


def _run_variant(
    frame: pd.DataFrame,
    variant: str,
    *,
    geofm_columns: list[str],
    threshold: int,
    caliper: float,
    n_bootstrap: int,
    random_state: int,
) -> tuple[dict[str, Any], pd.DataFrame]:
    if variant == "geometry_alphaearth_64d":
        covariates = [*GEOMETRY_COLUMNS, *geofm_columns]
        working = frame
        extra: dict[str, Any] = {}
    elif variant == "geometry_rs_alphaearth_64d":
        covariates = [
            *GEOMETRY_COLUMNS,
            *SENTINEL_BAND_COLUMNS,
            *SENTINEL_INDEX_COLUMNS,
            *TERRAIN_COLUMNS,
            *geofm_columns,
        ]
        working = frame
        extra = {}
    elif variant == "geometry_alphaearth_pca":
        working, covariates, extra = _build_alphaearth_pca_frame(
            frame,
            geofm_columns,
            random_state=random_state,
        )
    elif variant == "geometry_rs_alphaearth_pca":
        working, covariates, extra = _build_alphaearth_pca_frame(
            frame,
            geofm_columns,
            random_state=random_state,
            include_rs_context=True,
        )
    else:
        covariates = list(VARIANT_COLUMNS[variant])
        working = frame
        extra = {}

    temp_variant = "__temp_variant__"
    variant_frame = working.copy()
    from data_agent.experiments import chongqing_uhi_analysis as cqa

    original_specs = dict(cqa.FEATURE_SPECS)
    try:
        cqa.FEATURE_SPECS[temp_variant] = tuple(covariates)
        ablation, balance, _ = run_psm_ablation(
            variant_frame,
            threshold=threshold,
            caliper=caliper,
            n_bootstrap=n_bootstrap,
            random_state=random_state,
            outcome_col="LST",
            variants=(temp_variant,),
        )
    finally:
        cqa.FEATURE_SPECS.clear()
        cqa.FEATURE_SPECS.update(original_specs)

    row = ablation.iloc[0].to_dict() if not ablation.empty else {"status": "skipped: no_row"}
    row["variant"] = variant
    row.update(extra)
    if not balance.empty:
        balance = balance.copy()
        balance["variant"] = variant
    return row, balance


def run_geofm_causal_ablation(
    frame: pd.DataFrame,
    *,
    threshold: int = 10,
    caliper: float = 0.2,
    n_bootstrap: int = 200,
    random_state: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run observed-only and GeoFM-aware PSM variants on a Chongqing-like frame."""
    geofm_columns = resolve_geofm_columns(frame)
    rows: list[dict[str, Any]] = []
    balance_parts: list[pd.DataFrame] = []
    variant_order = [
        "geometry_only",
        "geometry_rs_context",
        "geometry_alphaearth_64d",
        "geometry_rs_alphaearth_64d",
        "geometry_alphaearth_pca",
        "geometry_rs_alphaearth_pca",
    ]
    for offset, variant in enumerate(variant_order):
        if variant in GEOFM_VARIANTS and not geofm_columns:
            rows.append(
                {
                    "variant": variant,
                    "threshold": int(threshold),
                    "estimator": "psm_nearest_caliper",
                    "status": "skipped: no_alphaearth_columns",
                    "common_support_n": 0,
                    "att": np.nan,
                    "se": np.nan,
                    "ci_lower": np.nan,
                    "ci_upper": np.nan,
                    "caliper": float(caliper),
                    "caliper_abs": np.nan,
                    "max_pre_smd": np.nan,
                    "max_post_smd": np.nan,
                    "balance_pass_0_1": False,
                    "matched_treated_n": 0,
                    "matched_control_n": 0,
                    "geofm_columns_present": 0,
                }
            )
            continue
        row, balance = _run_variant(
            frame,
            variant,
            geofm_columns=geofm_columns,
            threshold=threshold,
            caliper=caliper,
            n_bootstrap=n_bootstrap,
            random_state=random_state + offset,
        )
        row["geofm_columns_present"] = int(len(geofm_columns))
        rows.append(row)
        if not balance.empty:
            balance_parts.append(balance)

    ablation = pd.DataFrame(rows)
    balance = pd.concat(balance_parts, ignore_index=True) if balance_parts else pd.DataFrame()
    return ablation, balance


def build_geofm_availability_report(
    frame: pd.DataFrame,
    *,
    phase0_report_path: str | Path | None = DEFAULT_PHASE0_REPORT,
    coverage_loader: Callable[[], dict[str, Any]] | None = None,
    runtime_probe: bool = True,
    runtime_sampling: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if coverage_loader is None:
        coverage_loader = _default_coverage_loader
    geofm_columns = resolve_geofm_columns(frame)
    local_weights = {
        "available": bool((PROJECT_ROOT / "data_agent" / "weights" / "local_alphaearth_encoder.pth").exists()),
        "path": str(PROJECT_ROOT / "data_agent" / "weights" / "local_alphaearth_encoder.pth"),
    }
    report = {
        "phase0_validation": _read_phase0_report(phase0_report_path),
        "local_alphaearth_weights": local_weights,
        "embedding_store_coverage": coverage_loader(),
        "input_geofm_columns": {
            "available": bool(geofm_columns),
            "n_columns": int(len(geofm_columns)),
            "columns": geofm_columns,
            "complete_rows": int(frame[geofm_columns].dropna(how="any").shape[0])
            if geofm_columns
            else 0,
        },
        "runtime_probe": _runtime_probe() if runtime_probe else {"available": None, "status": "not_run"},
        "runtime_sampling": runtime_sampling or {"status": "not_run"},
    }
    if report["input_geofm_columns"]["available"]:
        claim = "candidate_real_geofm_available"
    else:
        claim = "geofm_unavailable"
    report["claim_guidance"] = claim
    return report


def _best_row(frame: pd.DataFrame, variants: list[str]) -> dict[str, Any] | None:
    if frame.empty:
        return None
    subset = frame[frame["variant"].isin(variants)].copy()
    if subset.empty:
        return None
    subset["max_post_smd_num"] = pd.to_numeric(subset["max_post_smd"], errors="coerce")
    subset = subset[subset["status"] == "ok"]
    if subset.empty:
        return None
    ordered = subset.sort_values(["max_post_smd_num", "matched_treated_n"], ascending=[True, False])
    return ordered.iloc[0].to_dict()


def _determine_claim_guidance(ablation: pd.DataFrame) -> str:
    observed_best = _best_row(ablation, ["geometry_only", "geometry_rs_context"])
    geofm_best = _best_row(ablation, list(GEOFM_VARIANTS))
    if not geofm_best:
        return "geofm_unavailable"
    geofm_smd = float(geofm_best.get("max_post_smd_num", np.inf))
    observed_smd = (
        float(observed_best.get("max_post_smd_num", np.inf))
        if observed_best
        else np.inf
    )
    if geofm_smd < 0.1 and geofm_smd <= observed_smd:
        return "bounded_geofm_claim_supported"
    return "geofm_no_clear_gain"


def _render_report(ablation: pd.DataFrame, availability: dict[str, Any]) -> str:
    claim = availability.get("claim_guidance") or _determine_claim_guidance(ablation)
    lines = [
        "# GeoFM AlphaEarth Ablation Report",
        "",
        f"- Claim guidance: `{claim}`",
        f"- Input GeoFM columns: `{availability['input_geofm_columns']['n_columns']}`",
        f"- Runtime sampling: `{availability['runtime_sampling'].get('status')}`",
        "",
        "## Variants",
        "",
    ]
    for _, row in ablation.iterrows():
        lines.append(
            f"- `{row.get('variant')}`: status `{row.get('status')}`, "
            f"ATT `{row.get('att')}`, max post-match SMD `{row.get('max_post_smd')}`"
        )
    return "\n".join(lines) + "\n"


def write_geofm_outputs(
    *,
    output_dir: str | Path,
    availability_report: dict[str, Any],
    ablation: pd.DataFrame,
    balance: pd.DataFrame,
    analysis_sample: pd.DataFrame | None = None,
) -> dict[str, Any]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    availability_path = target / OUTPUT_FILES["availability_report_json"]
    ablation_path = target / OUTPUT_FILES["causal_ablation_csv"]
    balance_path = target / OUTPUT_FILES["balance_diagnostics_csv"]
    manifest_path = target / OUTPUT_FILES["manifest_json"]
    report_path = target / OUTPUT_FILES["report_md"]
    sample_path = target / OUTPUT_FILES["analysis_sample_csv"]

    availability_report = dict(availability_report)
    availability_report["claim_guidance"] = _determine_claim_guidance(ablation)

    ablation.to_csv(ablation_path, index=False)
    balance.to_csv(balance_path, index=False)
    if analysis_sample is not None:
        analysis_sample.to_csv(sample_path, index=False)
    availability_path.write_text(
        json.dumps(_json_ready(availability_report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_path.write_text(_render_report(ablation, availability_report), encoding="utf-8")

    manifest = {
        "availability_report_json": str(availability_path),
        "causal_ablation_csv": str(ablation_path),
        "balance_diagnostics_csv": str(balance_path),
        "manifest_json": str(manifest_path),
        "report_md": str(report_path),
        "analysis_sample_csv": str(sample_path),
        "n_ablation_rows": int(len(ablation)),
        "n_balance_rows": int(len(balance)),
    }
    manifest_path.write_text(
        json.dumps(_json_ready(manifest), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def run_geofm_alphaearth_analysis(
    *,
    frame: pd.DataFrame,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    phase0_report_path: str | Path | None = DEFAULT_PHASE0_REPORT,
    coverage_loader: Callable[[], dict[str, Any]] | None = None,
    geofm_sampler: Callable[[pd.DataFrame], tuple[pd.DataFrame, dict[str, Any]]] | None = None,
    attempt_gee_sampling: bool = False,
    probe_runtime: bool = True,
    year: int = 2021,
    sampling_batch_size: int = 250,
    max_sampling_rows: int | None = None,
    threshold: int = 10,
    caliper: float = 0.2,
    n_bootstrap: int = 200,
    random_state: int = 0,
) -> dict[str, Any]:
    """Run the full GeoFM/AlphaEarth availability and ablation suite."""
    working = frame.copy()
    runtime_sampling = {"status": "not_run", "year": year}
    if not resolve_geofm_columns(working) and attempt_gee_sampling:
        sampler = geofm_sampler or _default_geofm_sampler
        geofm_frame, runtime_sampling = _call_geofm_sampler(
            sampler,
            working,
            year=year,
            random_state=random_state,
            batch_size=sampling_batch_size,
            max_rows=max_sampling_rows,
        )
        if isinstance(geofm_frame, pd.DataFrame) and not geofm_frame.empty:
            working = _attach_geofm_columns(working, geofm_frame)

    ablation, balance = run_geofm_causal_ablation(
        working,
        threshold=threshold,
        caliper=caliper,
        n_bootstrap=n_bootstrap,
        random_state=random_state,
    )
    availability = build_geofm_availability_report(
        working,
        phase0_report_path=phase0_report_path,
        coverage_loader=coverage_loader,
        runtime_probe=probe_runtime,
        runtime_sampling=runtime_sampling,
    )
    return write_geofm_outputs(
        output_dir=output_dir,
        availability_report=availability,
        ablation=ablation,
        balance=balance,
        analysis_sample=working,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GeoFM AlphaEarth ablation for Paper 6.")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--phase0-report", default=str(DEFAULT_PHASE0_REPORT))
    parser.add_argument("--year", type=int, default=2021)
    parser.add_argument("--attempt-gee", action="store_true")
    parser.add_argument("--probe-runtime", action="store_true")
    parser.add_argument("--sampling-batch-size", type=int, default=250)
    parser.add_argument("--max-sampling-rows", type=int, default=None)
    parser.add_argument("--n-bootstrap", type=int, default=200)
    parser.add_argument("--random-state", type=int, default=0)
    args = parser.parse_args()

    frame = pd.read_csv(args.input_csv)
    manifest = run_geofm_alphaearth_analysis(
        frame=frame,
        output_dir=args.output_dir,
        phase0_report_path=args.phase0_report,
        attempt_gee_sampling=args.attempt_gee,
        probe_runtime=args.probe_runtime,
        year=args.year,
        sampling_batch_size=args.sampling_batch_size,
        max_sampling_rows=args.max_sampling_rows,
        n_bootstrap=args.n_bootstrap,
        random_state=args.random_state,
    )
    print(json.dumps(_json_ready(manifest), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
