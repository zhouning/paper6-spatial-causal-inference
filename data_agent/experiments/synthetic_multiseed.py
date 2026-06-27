"""Multi-seed synthetic benchmark for Paper 6 causal estimators."""

from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from data_agent.experiments.run_causal import (
    PROJECT_ROOT,
    _dump_portable_json,
    generate_causal_forest_data,
    generate_did_data,
    generate_erf_data,
    generate_gccm_data,
    generate_granger_data,
    generate_psm_data,
)


DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "paper"
    / "ijgis_submission_20260605"
    / "07_results"
)


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    method: str
    generator: Callable[..., tuple[Any, dict[str, Any]]]
    runner: Callable[[Any, dict[str, Any], int, str], dict[str, Any]]
    variant: str = "standard"


def _write_frame_to_temp(data: Any, suffix: str) -> str:
    if suffix == ".geojson":
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.close()
        data.to_file(tmp.name, driver="GeoJSON")
        return tmp.name

    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False, mode="w")
    data.to_csv(tmp.name, index=False)
    tmp.close()
    return tmp.name


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        value_f = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value_f):
        return None
    return value_f


def _load_json_result(result_json: str) -> dict[str, Any]:
    result = json.loads(result_json)
    if "error" in result:
        raise RuntimeError(str(result["error"]))
    return result


def _coverage(ci_lower: Any, ci_upper: Any, true_value: float) -> bool | None:
    lo = _safe_float(ci_lower)
    hi = _safe_float(ci_upper)
    if lo is None or hi is None:
        return None
    return lo <= true_value <= hi


def _row(
    *,
    scenario: str,
    method: str,
    seed: int,
    metric_name: str,
    true_value: float,
    estimate: float,
    ci_lower: float | None = None,
    ci_upper: float | None = None,
    variant: str = "standard",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "scenario": scenario,
        "variant": variant,
        "method": method,
        "seed": int(seed),
        "status": "ok",
        "metric_name": metric_name,
        "true_value": float(true_value),
        "estimate": float(estimate),
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "covered": _coverage(ci_lower, ci_upper, true_value),
    }
    if extra:
        row.update(extra)
    return row


def _error_row(
    *,
    scenario: str,
    method: str,
    seed: int,
    metric_name: str,
    true_value: float | None = None,
    variant: str = "standard",
    error: str,
) -> dict[str, Any]:
    return {
        "scenario": scenario,
        "variant": variant,
        "method": method,
        "seed": int(seed),
        "status": "error",
        "metric_name": metric_name,
        "true_value": true_value,
        "estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "covered": None,
        "error": error,
    }


def _run_psm(data: pd.DataFrame, meta: dict[str, Any], seed: int, variant: str) -> dict[str, Any]:
    from data_agent.causal_inference import propensity_score_matching

    true_value = float(meta["true_ate"])
    if variant == "naive_difference":
        treated = data[data["treatment"] == 1]["price"]
        control = data[data["treatment"] == 0]["price"]
        estimate = float(treated.mean() - control.mean())
        return _row(
            scenario="PSM",
            method="mean_difference",
            seed=seed,
            metric_name="ate",
            true_value=true_value,
            estimate=estimate,
            variant=variant,
            extra={
                "n_treated": int(len(treated)),
                "n_control": int(len(control)),
                "n_matched": None,
            },
        )

    if variant == "ols_adjusted":
        import statsmodels.api as sm

        model_data = data[["price", "treatment", "income", "school_dist"]].dropna()
        y = model_data["price"].astype(float)
        x = sm.add_constant(model_data[["treatment", "income", "school_dist"]].astype(float))
        model = sm.OLS(y, x).fit()
        estimate = float(model.params["treatment"])
        ci = model.conf_int().loc["treatment"]
        return _row(
            scenario="PSM",
            method="ols_adjusted",
            seed=seed,
            metric_name="ate",
            true_value=true_value,
            estimate=estimate,
            ci_lower=float(ci.iloc[0]),
            ci_upper=float(ci.iloc[1]),
            variant=variant,
            extra={
                "n_treated": int((model_data["treatment"] == 1).sum()),
                "n_control": int((model_data["treatment"] == 0).sum()),
                "n_matched": None,
            },
        )

    method = "nearest"
    kwargs: dict[str, Any] = {}
    if variant == "caliper":
        method = "caliper"
        kwargs["caliper"] = 0.5
    elif variant == "kernel":
        method = "kernel"

    path = _write_frame_to_temp(data, ".csv")
    try:
        result = _load_json_result(
            propensity_score_matching(
                file_path=path,
                treatment_col="treatment",
                outcome_col="price",
                confounders="income,school_dist",
                method=method,
                **kwargs,
            )
        )
    finally:
        os.unlink(path)

    return _row(
        scenario="PSM",
        method="propensity_score_matching",
        seed=seed,
        metric_name="att",
        true_value=true_value,
        estimate=float(result["att"]),
        ci_lower=_safe_float(result.get("ci_lower")),
        ci_upper=_safe_float(result.get("ci_upper")),
        variant=variant,
        extra={
            "n_treated": result.get("n_treated"),
            "n_control": result.get("n_control"),
            "n_matched": result.get("n_matched"),
        },
    )


def _run_did(data: pd.DataFrame, meta: dict[str, Any], seed: int, variant: str) -> dict[str, Any]:
    from data_agent.causal_inference import difference_in_differences

    path = _write_frame_to_temp(data, ".csv")
    try:
        result = _load_json_result(
            difference_in_differences(
                file_path=path,
                outcome_col="pm25",
                treatment_col="treated",
                time_col="time",
                post_col="post",
                entity_col="entity",
            )
        )
    finally:
        os.unlink(path)

    true_value = float(meta["true_effect"])
    return _row(
        scenario="DiD",
        method="difference_in_differences",
        seed=seed,
        metric_name="did_estimate",
        true_value=true_value,
        estimate=float(result["did_estimate"]),
        ci_lower=_safe_float(result.get("ci_lower")),
        ci_upper=_safe_float(result.get("ci_upper")),
        variant=variant,
        extra={"n_observations": result.get("n_observations")},
    )


def _run_erf(data: pd.DataFrame, meta: dict[str, Any], seed: int, variant: str) -> dict[str, Any]:
    from data_agent.causal_inference import exposure_response_function

    path = _write_frame_to_temp(data, ".csv")
    try:
        result = _load_json_result(
            exposure_response_function(
                file_path=path,
                exposure_col="distance",
                outcome_col="health_score",
                confounders="income",
            )
        )
    finally:
        os.unlink(path)

    erf_curve = pd.read_csv(result["erf_data_path"])
    valid = erf_curve.dropna(subset=["exposure", "response"])
    if len(valid) < 2:
        raise RuntimeError("ERF output has fewer than two valid grid points")

    exposure = valid["exposure"].to_numpy(dtype=float)
    response = valid["response"].to_numpy(dtype=float)
    true_response = 60.0 + 2.0 * exposure - 0.05 * exposure**2
    true_range = float(true_response[-1] - true_response[0])
    estimated_range = float(response[-1] - response[0])
    shape_corr = float(np.corrcoef(response, true_response)[0, 1])

    return _row(
        scenario="ERF",
        method="exposure_response_function",
        seed=seed,
        metric_name="range_effect",
        true_value=true_range,
        estimate=estimated_range,
        variant=variant,
        extra={
            "shape_correlation": shape_corr,
            "n_observations": result.get("n_observations"),
            "balance_mean_abs_smd": result.get("balance_mean_abs_smd"),
        },
    )


def _run_causal_forest(data: pd.DataFrame, meta: dict[str, Any], seed: int, variant: str) -> dict[str, Any]:
    from data_agent.causal_inference import causal_forest_analysis

    path = _write_frame_to_temp(data, ".csv")
    try:
        result = _load_json_result(
            causal_forest_analysis(
                file_path=path,
                treatment_col="treatment",
                outcome_col="crop_yield",
                feature_cols="aridity,soil_quality",
            )
        )
    finally:
        os.unlink(path)

    true_value = float((200.0 * data["aridity"]).mean())
    return _row(
        scenario="CausalForest",
        method="causal_forest_analysis",
        seed=seed,
        metric_name="ate",
        true_value=true_value,
        estimate=float(result["ate"]),
        ci_lower=_safe_float(result.get("ci_lower")),
        ci_upper=_safe_float(result.get("ci_upper")),
        variant=variant,
        extra={
            "cate_std": result.get("cate_std"),
            "heterogeneity_pvalue": result.get("heterogeneity_pvalue"),
        },
    )


def _run_granger(data: pd.DataFrame, meta: dict[str, Any], seed: int, variant: str) -> dict[str, Any]:
    from data_agent.causal_inference import spatial_granger_causality

    path = _write_frame_to_temp(data, ".csv")
    try:
        result = _load_json_result(
            spatial_granger_causality(
                file_path=path,
                variables="urban_area,farmland_area",
                time_col="time",
                location_col="location",
                max_lag=4,
                significance=0.05,
            )
        )
    finally:
        os.unlink(path)

    matrix = result["causality_matrix"]
    forward = bool(matrix["urban_area"]["farmland_area"]["significant"])
    reverse = bool(matrix["farmland_area"]["urban_area"]["significant"])
    correct = float(forward and not reverse)
    return _row(
        scenario="Granger",
        method="spatial_granger_causality",
        seed=seed,
        metric_name="direction_accuracy",
        true_value=1.0,
        estimate=correct,
        variant=variant,
        extra={
            "forward_significant": forward,
            "reverse_significant": reverse,
            "forward_p_value": matrix["urban_area"]["farmland_area"].get("p_value"),
            "reverse_p_value": matrix["farmland_area"]["urban_area"].get("p_value"),
        },
    )



def _gccm_direction_accuracy(result: dict[str, Any]) -> float:
    has_convergence_flags = (
        "x_causes_y_converges" in result or "y_causes_x_converges" in result
    )
    forward = bool(result.get("x_causes_y_converges"))
    reverse = bool(result.get("y_causes_x_converges"))
    forward_rho = _safe_float(result.get("x_causes_y_rho"))
    reverse_rho = _safe_float(result.get("y_causes_x_rho"))

    if forward and not reverse:
        return 1.0
    if forward_rho is not None and reverse_rho is not None:
        if not has_convergence_flags:
            return float(forward_rho >= reverse_rho)
        if forward and reverse:
            return float(forward_rho >= reverse_rho)
    return 0.0


def _gccm_direction_rule(result: dict[str, Any]) -> str:
    has_convergence_flags = (
        "x_causes_y_converges" in result or "y_causes_x_converges" in result
    )
    forward = bool(result.get("x_causes_y_converges"))
    reverse = bool(result.get("y_causes_x_converges"))
    forward_rho = _safe_float(result.get("x_causes_y_rho"))
    reverse_rho = _safe_float(result.get("y_causes_x_rho"))
    if forward and not reverse:
        return "forward_only_convergence"
    if forward_rho is not None and reverse_rho is not None:
        if not has_convergence_flags:
            if forward_rho >= reverse_rho:
                return "saved_detail_forward_rho_dominance"
            return "saved_detail_reverse_rho_dominance"
        if forward and reverse:
            if forward_rho >= reverse_rho:
                return "bidirectional_convergence_forward_rho_dominance"
            return "bidirectional_convergence_reverse_rho_dominance"
    return "no_forward_direction_evidence"


def _run_gccm(data: Any, meta: dict[str, Any], seed: int, variant: str) -> dict[str, Any]:
    from data_agent.causal_inference import geographic_causal_mapping

    kwargs: dict[str, Any] = {"k": 4}
    if variant == "knn_k2":
        kwargs["k"] = 2
    elif variant == "queen":
        kwargs["k"] = 4
        kwargs["weights_type"] = "queen"

    path = _write_frame_to_temp(data, ".geojson")
    try:
        result = _load_json_result(
            geographic_causal_mapping(
                file_path=path,
                cause_col="rainfall",
                effect_col="ndvi",
                **kwargs,
            )
        )
    finally:
        os.unlink(path)

    correct = _gccm_direction_accuracy(result)
    direction_rule = _gccm_direction_rule(result)
    return _row(
        scenario="GCCM",
        method="geographic_causal_mapping",
        seed=seed,
        metric_name="direction_accuracy",
        true_value=1.0,
        estimate=correct,
        variant=variant,
        extra={
            "x_causes_y_rho": result.get("x_causes_y_rho"),
            "y_causes_x_rho": result.get("y_causes_x_rho"),
            "x_causes_y_converges": result.get("x_causes_y_converges"),
            "y_causes_x_converges": result.get("y_causes_x_converges"),
            "causal_direction": result.get("causal_direction"),
            "direction_decision_rule": direction_rule,
        },
    )


SCENARIOS: dict[str, ScenarioSpec] = {
    "PSM": ScenarioSpec("PSM", "propensity_score_matching", generate_psm_data, _run_psm),
    "DiD": ScenarioSpec("DiD", "difference_in_differences", generate_did_data, _run_did),
    "ERF": ScenarioSpec("ERF", "exposure_response_function", generate_erf_data, _run_erf),
    "Granger": ScenarioSpec("Granger", "spatial_granger_causality", generate_granger_data, _run_granger),
    "GCCM": ScenarioSpec("GCCM", "geographic_causal_mapping", generate_gccm_data, _run_gccm),
    "CausalForest": ScenarioSpec(
        "CausalForest",
        "causal_forest_analysis",
        generate_causal_forest_data,
        _run_causal_forest,
    ),
}


def _summarize_group(group: pd.DataFrame) -> dict[str, Any]:
    ok = group[group["status"] == "ok"].copy()
    estimates = pd.to_numeric(ok["estimate"], errors="coerce").dropna()
    true_values = pd.to_numeric(ok["true_value"], errors="coerce")
    valid_pairs = ok.copy()
    valid_pairs["estimate_num"] = pd.to_numeric(valid_pairs["estimate"], errors="coerce")
    valid_pairs["true_num"] = pd.to_numeric(valid_pairs["true_value"], errors="coerce")
    valid_pairs = valid_pairs.dropna(subset=["estimate_num", "true_num"])
    true_value = float(valid_pairs["true_num"].mean()) if len(valid_pairs) else np.nan

    if estimates.empty or len(valid_pairs) == 0:
        return {
            "n_seeds": int(len(group)),
            "n_success": 0,
            "failure_count": int((group["status"] != "ok").sum()),
            "true_value": true_value,
            "estimate_mean": np.nan,
            "estimate_median": np.nan,
            "estimate_std": np.nan,
            "bias": np.nan,
            "rmse": np.nan,
            "mae": np.nan,
            "coverage_rate": np.nan,
        }

    errors = (
        valid_pairs["estimate_num"].to_numpy(dtype=float)
        - valid_pairs["true_num"].to_numpy(dtype=float)
    )
    covered = ok["covered"].dropna()
    coverage_rate = float(covered.astype(bool).mean()) if len(covered) else np.nan
    return {
        "n_seeds": int(len(group)),
        "n_success": int(len(valid_pairs)),
        "failure_count": int((group["status"] != "ok").sum()),
        "true_value": true_value,
        "estimate_mean": float(estimates.mean()),
        "estimate_median": float(estimates.median()),
        "estimate_std": float(estimates.std(ddof=1)) if len(estimates) > 1 else 0.0,
        "bias": float(errors.mean()),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "mae": float(np.mean(np.abs(errors))),
        "coverage_rate": coverage_rate,
    }


def summarize_benchmark_details(details: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(details)
    if frame.empty:
        return pd.DataFrame()
    if "covered" not in frame.columns:
        frame["covered"] = pd.Series([None] * len(frame), dtype=object)
    else:
        frame["covered"] = frame["covered"].astype(object)
    missing_covered = frame["covered"].isna()
    for idx, row in frame[missing_covered].iterrows():
        true_value = _safe_float(row.get("true_value"))
        if true_value is None:
            continue
        frame.at[idx, "covered"] = _coverage(
            row.get("ci_lower"),
            row.get("ci_upper"),
            true_value,
        )

    rows = []
    for keys, group in frame.groupby(["scenario", "variant", "method", "metric_name"], dropna=False):
        scenario, variant, method, metric_name = keys
        row = {
            "scenario": scenario,
            "variant": variant,
            "method": method,
            "metric_name": metric_name,
        }
        row.update(_summarize_group(group))
        rows.append(row)

    return pd.DataFrame(rows).sort_values(["scenario", "variant"]).reset_index(drop=True)


def write_benchmark_outputs(details: list[dict[str, Any]], output_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = summarize_benchmark_details(details)
    summary_path = output_dir / "synthetic_multiseed_summary.csv"
    details_path = output_dir / "synthetic_multiseed_details.json"
    manifest_path = output_dir / "synthetic_multiseed_manifest.json"

    summary.to_csv(summary_path, index=False)
    _dump_portable_json(details, details_path)

    manifest = {
        "summary_csv": str(summary_path),
        "details_json": str(details_path),
        "manifest_json": str(manifest_path),
        "n_rows": len(details),
        "n_summary_rows": len(summary),
        "scenarios": sorted({row["scenario"] for row in details}),
    }
    _dump_portable_json(manifest, manifest_path)
    return manifest


def run_synthetic_multiseed_benchmark(
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    seeds: Iterable[int] | None = None,
    scenario_names: Iterable[str] | None = None,
    include_extended_variants: bool = False,
) -> dict[str, Any]:
    if seeds is None:
        seeds = range(30)
    seeds = [int(seed) for seed in seeds]

    if scenario_names is None:
        scenario_names = SCENARIOS.keys()
    scenario_names = list(scenario_names)

    details: list[dict[str, Any]] = []
    for scenario_name in scenario_names:
        if scenario_name not in SCENARIOS:
            raise ValueError(f"Unknown synthetic scenario: {scenario_name}")
        spec = SCENARIOS[scenario_name]
        variants = [spec.variant]
        if include_extended_variants:
            if scenario_name == "PSM":
                variants = ["standard", "caliper", "kernel", "naive_difference", "ols_adjusted"]
            elif scenario_name == "GCCM":
                variants = ["standard", "knn_k2", "queen"]
        for seed in seeds:
            data, meta = spec.generator(seed=seed)
            for variant in variants:
                try:
                    details.append(spec.runner(data, meta, seed, variant))
                except Exception as exc:
                    details.append(
                        _error_row(
                            scenario=spec.name,
                            method=spec.method,
                            seed=seed,
                            metric_name="unknown",
                            variant=variant,
                            error=str(exc),
                        )
                    )
                    

    return write_benchmark_outputs(details, output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Paper 6 synthetic multi-seed benchmark.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--n-seeds", type=int, default=30)
    parser.add_argument(
        "--scenarios",
        default=",".join(SCENARIOS.keys()),
        help="Comma-separated scenario names. Default: all scenarios.",
    )
    args = parser.parse_args()

    scenarios = [item.strip() for item in args.scenarios.split(",") if item.strip()]
    manifest = run_synthetic_multiseed_benchmark(
        output_dir=args.output_dir,
        seeds=range(args.n_seeds),
        scenario_names=scenarios,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
