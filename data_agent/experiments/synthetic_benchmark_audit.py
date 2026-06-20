"""Synthetic benchmark audit for Paper 6 causal estimators."""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from data_agent.experiments.run_causal import PROJECT_ROOT, _dump_portable_json
from data_agent.experiments.synthetic_multiseed import (
    SCENARIOS,
    _coverage,
    _error_row,
    _safe_float,
)


DEFAULT_AUDIT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "paper"
    / "ijgis_submission_20260605"
    / "07_results"
    / "synthetic_benchmark_audit"
)


@dataclass(frozen=True)
class AuditSetting:
    name: str
    stress_level: str
    generator: Callable[[int], tuple[Any, dict[str, Any]]]


def _generate_psm_parameterized(
    *,
    seed: int,
    n: int = 2000,
    treatment_intercept: float = -1.0,
    treatment_noise: float = 0.5,
    outcome_noise: float = 8000.0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rng = np.random.default_rng(seed)
    income = rng.normal(50000, 15000, n)
    school_dist = rng.uniform(0, 5, n)
    logit = (
        treatment_intercept
        + 0.00002 * income
        - 0.3 * school_dist
        + rng.normal(0, treatment_noise, n)
    )
    prop = 1 / (1 + np.exp(-logit))
    treatment = rng.binomial(1, prop)
    noise = rng.normal(0, outcome_noise, n)
    price = 150000 + 1.5 * income - 5000 * school_dist + 15000 * treatment + noise
    df = pd.DataFrame(
        {
            "treatment": treatment,
            "price": price,
            "income": income,
            "school_dist": school_dist,
        }
    )
    meta = {
        "true_ate": 15000.0,
        "method": "PSM",
        "scenario": "park_price",
    }
    return df, meta


def _generate_did_parameterized(
    *,
    seed: int,
    n: int = 500,
    n_periods: int = 6,
    effect_size: float = -8.0,
    noise_sd: float = 2.0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rng = np.random.default_rng(seed)
    rows = []
    post_start = max(1, n_periods // 2)
    for i in range(n):
        treated = int(i < n // 2)
        for t in range(n_periods):
            post = int(t >= post_start)
            base = 45 + rng.normal(0, 3)
            trend = -0.5 * t
            effect = effect_size * treated * post
            pm25 = base + trend + 5 * treated + effect + rng.normal(0, noise_sd)
            rows.append(
                {
                    "entity": i,
                    "time": t,
                    "treated": treated,
                    "post": post,
                    "pm25": pm25,
                }
            )
    return pd.DataFrame(rows), {
        "true_effect": effect_size,
        "method": "DiD",
        "scenario": "pm25_restriction",
    }


def _generate_erf_parameterized(
    *,
    seed: int,
    n: int = 1000,
    distance_min: float = 0.0,
    distance_max: float = 20.0,
    outcome_noise: float = 3.0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rng = np.random.default_rng(seed)
    distance = rng.uniform(distance_min, distance_max, n)
    income = rng.normal(50000, 10000, n)
    health = (
        60
        + 2.0 * distance
        - 0.05 * distance**2
        + 0.0001 * income
        + rng.normal(0, outcome_noise, n)
    )
    df = pd.DataFrame(
        {"distance": distance, "health_score": health, "income": income}
    )
    return df, {"method": "ERF", "scenario": "pollution_health", "true_shape": "quadratic"}


def _generate_granger_parameterized(
    *,
    seed: int,
    n_time: int = 100,
    urban_drift: float = 1.5,
    urban_noise: float = 0.5,
    farm_effect: float = -0.3,
    farm_noise: float = 1.0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rng = np.random.default_rng(seed)
    urban = np.zeros(n_time)
    farm = np.zeros(n_time)
    urban[0] = 50
    farm[0] = 200
    for t in range(1, n_time):
        urban[t] = urban[t - 1] + rng.normal(urban_drift, urban_noise)
        lag_urban = urban[t - 2] if t >= 2 else urban[0]
        farm[t] = farm[t - 1] + farm_effect * lag_urban + rng.normal(0, farm_noise)
    df = pd.DataFrame(
        {
            "time": range(n_time),
            "location": 0,
            "urban_area": urban,
            "farmland_area": farm,
        }
    )
    return df, {"true_lag": 2, "method": "Granger", "scenario": "urban_farmland"}


def _generate_gccm_parameterized(
    *,
    seed: int,
    n_side: int = 14,
    rainfall_noise: float = 8.0,
    ndvi_noise: float = 0.015,
    ndvi_coeff: float = 0.0016,
    gradient_coeff: float = 0.08,
) -> tuple[Any, dict[str, Any]]:
    rng = np.random.default_rng(seed)
    import geopandas as gpd
    from shapely.geometry import box

    records = []
    geometries = []
    for i in range(n_side):
        for j in range(n_side):
            rainfall = (
                500
                + 35 * np.sin(i / n_side * np.pi)
                + 25 * np.cos(j / n_side * np.pi)
                + rng.normal(0, rainfall_noise)
            )
            local_gradient = (i + j) / (2 * n_side)
            ndvi = (
                0.15
                + ndvi_coeff * rainfall
                + gradient_coeff * local_gradient
                + rng.normal(0, ndvi_noise)
            )
            records.append({"rainfall": rainfall, "ndvi": ndvi})
            geometries.append(box(j, i, j + 1, i + 1))

    gdf = gpd.GeoDataFrame(records, geometry=geometries, crs="EPSG:3857")
    return gdf, {"method": "GCCM", "scenario": "rain_ndvi", "true_direction": "rain->ndvi"}


def _generate_causal_forest_parameterized(
    *,
    seed: int,
    n: int = 1000,
    outcome_noise: float = 30.0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rng = np.random.default_rng(seed)
    aridity = rng.uniform(0, 1, n)
    soil_quality = rng.normal(50, 10, n)
    treatment = rng.binomial(1, 0.5, n)
    cate = 200 * aridity
    base_yield = 500 + 3 * soil_quality + rng.normal(0, outcome_noise, n)
    crop_yield = base_yield + cate * treatment
    df = pd.DataFrame(
        {
            "treatment": treatment,
            "crop_yield": crop_yield,
            "aridity": aridity,
            "soil_quality": soil_quality,
        }
    )
    return df, {
        "method": "CausalForest",
        "scenario": "irrigation_yield",
        "true_ate_arid": 200,
    }


def _build_setting_catalog() -> dict[str, dict[str, AuditSetting]]:
    return {
        "PSM": {
            "baseline": AuditSetting(
                "baseline",
                "baseline",
                lambda seed: _generate_psm_parameterized(seed=seed),
            ),
            "small_sample": AuditSetting(
                "small_sample",
                "mild",
                lambda seed: _generate_psm_parameterized(seed=seed, n=600),
            ),
            "noisy_outcome": AuditSetting(
                "noisy_outcome",
                "mild",
                lambda seed: _generate_psm_parameterized(
                    seed=seed, outcome_noise=14000.0
                ),
            ),
            "severe_stress": AuditSetting(
                "severe_stress",
                "severe",
                lambda seed: _generate_psm_parameterized(
                    seed=seed,
                    n=500,
                    treatment_intercept=-2.0,
                    treatment_noise=0.2,
                    outcome_noise=18000.0,
                ),
            ),
        },
        "DiD": {
            "baseline": AuditSetting(
                "baseline",
                "baseline",
                lambda seed: _generate_did_parameterized(seed=seed),
            ),
            "small_sample": AuditSetting(
                "small_sample",
                "mild",
                lambda seed: _generate_did_parameterized(seed=seed, n=150),
            ),
            "noisy_outcome": AuditSetting(
                "noisy_outcome",
                "mild",
                lambda seed: _generate_did_parameterized(seed=seed, noise_sd=4.0),
            ),
            "severe_stress": AuditSetting(
                "severe_stress",
                "severe",
                lambda seed: _generate_did_parameterized(
                    seed=seed,
                    n=120,
                    n_periods=4,
                    effect_size=-4.0,
                    noise_sd=5.5,
                ),
            ),
        },
        "ERF": {
            "baseline": AuditSetting(
                "baseline",
                "baseline",
                lambda seed: _generate_erf_parameterized(seed=seed),
            ),
            "small_sample": AuditSetting(
                "small_sample",
                "mild",
                lambda seed: _generate_erf_parameterized(seed=seed, n=300),
            ),
            "noisy_outcome": AuditSetting(
                "noisy_outcome",
                "mild",
                lambda seed: _generate_erf_parameterized(seed=seed, outcome_noise=6.0),
            ),
            "severe_stress": AuditSetting(
                "severe_stress",
                "severe",
                lambda seed: _generate_erf_parameterized(
                    seed=seed,
                    n=250,
                    distance_min=2.0,
                    distance_max=15.0,
                    outcome_noise=8.0,
                ),
            ),
        },
        "Granger": {
            "baseline": AuditSetting(
                "baseline",
                "baseline",
                lambda seed: _generate_granger_parameterized(seed=seed),
            ),
            "small_sample": AuditSetting(
                "small_sample",
                "mild",
                lambda seed: _generate_granger_parameterized(seed=seed, n_time=40),
            ),
            "noisy_outcome": AuditSetting(
                "noisy_outcome",
                "mild",
                lambda seed: _generate_granger_parameterized(
                    seed=seed,
                    urban_noise=1.2,
                    farm_noise=2.5,
                ),
            ),
            "severe_stress": AuditSetting(
                "severe_stress",
                "severe",
                lambda seed: _generate_granger_parameterized(
                    seed=seed,
                    n_time=35,
                    urban_noise=1.5,
                    farm_effect=-0.12,
                    farm_noise=3.0,
                ),
            ),
        },
        "GCCM": {
            "baseline": AuditSetting(
                "baseline",
                "baseline",
                lambda seed: _generate_gccm_parameterized(seed=seed),
            ),
            "small_sample": AuditSetting(
                "small_sample",
                "mild",
                lambda seed: _generate_gccm_parameterized(seed=seed, n_side=10),
            ),
            "noisy_outcome": AuditSetting(
                "noisy_outcome",
                "mild",
                lambda seed: _generate_gccm_parameterized(
                    seed=seed,
                    rainfall_noise=15.0,
                    ndvi_noise=0.03,
                ),
            ),
            "severe_stress": AuditSetting(
                "severe_stress",
                "severe",
                lambda seed: _generate_gccm_parameterized(
                    seed=seed,
                    n_side=10,
                    rainfall_noise=18.0,
                    ndvi_noise=0.04,
                    ndvi_coeff=0.0007,
                    gradient_coeff=0.03,
                ),
            ),
        },
        "CausalForest": {
            "baseline": AuditSetting(
                "baseline",
                "baseline",
                lambda seed: _generate_causal_forest_parameterized(seed=seed),
            ),
            "small_sample": AuditSetting(
                "small_sample",
                "mild",
                lambda seed: _generate_causal_forest_parameterized(seed=seed, n=300),
            ),
            "noisy_outcome": AuditSetting(
                "noisy_outcome",
                "mild",
                lambda seed: _generate_causal_forest_parameterized(
                    seed=seed, outcome_noise=60.0
                ),
            ),
            "severe_stress": AuditSetting(
                "severe_stress",
                "severe",
                lambda seed: _generate_causal_forest_parameterized(
                    seed=seed,
                    n=250,
                    outcome_noise=90.0,
                ),
            ),
        },
    }


SETTING_CATALOG = _build_setting_catalog()


def _variants_for_scenario(scenario_name: str) -> list[str]:
    if scenario_name == "PSM":
        return ["standard", "caliper", "kernel", "naive_difference", "ols_adjusted"]
    if scenario_name == "GCCM":
        return ["standard", "knn_k2", "queen"]
    return ["standard"]


def _summarize_group(group: pd.DataFrame) -> dict[str, Any]:
    ok = group[group["status"] == "ok"].copy()
    estimates = pd.to_numeric(ok["estimate"], errors="coerce").dropna()
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


def _coerce_covered(frame: pd.DataFrame) -> pd.DataFrame:
    if "covered" not in frame.columns:
        frame["covered"] = pd.Series([None] * len(frame), dtype=object)
        return frame
    frame["covered"] = frame["covered"].astype(object)
    missing = frame["covered"].isna()
    for idx, row in frame[missing].iterrows():
        true_value = _safe_float(row.get("true_value"))
        if true_value is None:
            continue
        frame.at[idx, "covered"] = _coverage(
            row.get("ci_lower"),
            row.get("ci_upper"),
            true_value,
        )
    return frame


def _direction_metric(metric_name: str) -> bool:
    return metric_name.endswith("direction_accuracy")


def _classify_fragility(row: pd.Series) -> tuple[str, str, float]:
    n_seeds = max(int(row.get("n_seeds", 0) or 0), 1)
    failure_rate = float(row.get("failure_count", 0) or 0) / n_seeds
    coverage_rate = _safe_float(row.get("coverage_rate"))

    if _direction_metric(str(row["metric_name"])):
        accuracy = _safe_float(row.get("estimate_mean")) or 0.0
        score = max(0.0, min(1.0, accuracy - 0.5 * failure_rate))
        if failure_rate > 0.2:
            return "fragile", f"failure_rate={failure_rate:.2f} exceeded 0.20", score
        if accuracy >= 0.85:
            return "robust", f"direction_accuracy={accuracy:.2f} met robust threshold", score
        if accuracy >= 0.5:
            return "bounded", f"direction_accuracy={accuracy:.2f} was mixed", score
        return "fragile", f"direction_accuracy={accuracy:.2f} fell below 0.50", score

    true_value = abs(_safe_float(row.get("true_value")) or 1.0)
    rmse = abs(_safe_float(row.get("rmse")) or math.inf)
    bias = abs(_safe_float(row.get("bias")) or math.inf)
    norm_rmse = rmse / max(true_value, 1.0)
    norm_bias = bias / max(true_value, 1.0)
    coverage_penalty = 0.0
    if coverage_rate is not None and math.isfinite(coverage_rate):
        coverage_penalty = max(0.0, 0.8 - coverage_rate)
    score = 1.0 - min(
        1.0,
        0.6 * norm_rmse + 0.25 * norm_bias + 0.1 * failure_rate + 0.05 * coverage_penalty,
    )
    score = max(0.0, min(1.0, score))

    if failure_rate > 0.2:
        return "fragile", f"failure_rate={failure_rate:.2f} exceeded 0.20", score
    if norm_rmse <= 0.15 and (coverage_rate is None or coverage_rate >= 0.75):
        return "robust", f"normalized_rmse={norm_rmse:.3f} stayed within 0.15", score
    if norm_rmse <= 0.4 and (coverage_rate is None or coverage_rate >= 0.4):
        return "bounded", f"normalized_rmse={norm_rmse:.3f} stayed within 0.40", score
    return "fragile", f"normalized_rmse={norm_rmse:.3f} exceeded 0.40", score


def summarize_audit_details(details: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(details)
    if frame.empty:
        return pd.DataFrame()
    frame = _coerce_covered(frame)

    rows = []
    group_cols = [
        "scenario",
        "setting",
        "stress_level",
        "variant",
        "method",
        "metric_name",
    ]
    for keys, group in frame.groupby(group_cols, dropna=False):
        scenario, setting, stress_level, variant, method, metric_name = keys
        row = {
            "scenario": scenario,
            "setting": setting,
            "stress_level": stress_level,
            "variant": variant,
            "method": method,
            "metric_name": metric_name,
        }
        row.update(_summarize_group(group))
        fragility, fragility_reason, score = _classify_fragility(pd.Series(row))
        row["fragility"] = fragility
        row["fragility_reason"] = fragility_reason
        row["score"] = score
        rows.append(row)

    return pd.DataFrame(rows).sort_values(
        ["scenario", "setting", "variant", "metric_name"]
    ).reset_index(drop=True)


def summarize_fragility(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()

    rows = []
    for scenario, group in summary.groupby("scenario", dropna=False):
        counts = group["fragility"].value_counts()
        rows.append(
            {
                "scenario": scenario,
                "n_summary_rows": int(len(group)),
                "n_robust": int(counts.get("robust", 0)),
                "n_bounded": int(counts.get("bounded", 0)),
                "n_fragile": int(counts.get("fragile", 0)),
                "min_score": float(group["score"].min()),
                "max_score": float(group["score"].max()),
            }
        )
    return pd.DataFrame(rows).sort_values("scenario").reset_index(drop=True)


def _format_row_brief(row: pd.Series) -> str:
    return (
        f"- `{row['scenario']}` / `{row['setting']}` / `{row['variant']}`: "
        f"{row['fragility']}; {row['fragility_reason']}; "
        f"estimate_mean={row['estimate_mean']:.4g}, rmse={row['rmse']:.4g}"
    )


def render_audit_report(summary: pd.DataFrame, scenario_summary: pd.DataFrame) -> str:
    lines = [
        "# Synthetic Benchmark Audit",
        "",
        "This report summarizes which Paper 6 synthetic estimators remained robust under stress and which combinations were fragile.",
        "",
        "## Scenario Summary",
        "",
    ]

    for _, row in scenario_summary.iterrows():
        lines.append(
            f"- `{row['scenario']}`: robust={int(row['n_robust'])}, "
            f"bounded={int(row['n_bounded'])}, fragile={int(row['n_fragile'])}, "
            f"score_range=[{row['min_score']:.2f}, {row['max_score']:.2f}]"
        )

    fragile = summary.sort_values("score", ascending=True).head(8)
    strongest = summary.sort_values("score", ascending=False).head(8)

    lines.extend(["", "## Most Fragile Rows", ""])
    for _, row in fragile.iterrows():
        lines.append(_format_row_brief(row))

    lines.extend(["", "## Strongest Rows", ""])
    for _, row in strongest.iterrows():
        lines.append(_format_row_brief(row))

    for scenario_name in ("PSM", "GCCM"):
        subset = summary[summary["scenario"] == scenario_name].sort_values("score")
        if subset.empty:
            continue
        worst = subset.iloc[0]
        best = subset.iloc[-1]
        lines.extend(
            [
                "",
                f"## {scenario_name} Notes",
                "",
                f"- Weakest audited row: `{worst['setting']}` / `{worst['variant']}` with {worst['fragility']} ({worst['fragility_reason']}).",
                f"- Strongest audited row: `{best['setting']}` / `{best['variant']}` with {best['fragility']} ({best['fragility_reason']}).",
            ]
        )

    return "\n".join(lines) + "\n"


def write_audit_outputs(details: list[dict[str, Any]], output_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = summarize_audit_details(details)
    scenario_summary = summarize_fragility(summary)
    report_text = render_audit_report(summary, scenario_summary)

    summary_path = output_dir / "synthetic_benchmark_audit_summary.csv"
    details_path = output_dir / "synthetic_benchmark_audit_details.json"
    manifest_path = output_dir / "synthetic_benchmark_audit_manifest.json"
    report_path = output_dir / "synthetic_benchmark_audit_report.md"
    scenario_summary_path = output_dir / "scenario_fragility_summary.csv"

    summary.to_csv(summary_path, index=False)
    scenario_summary.to_csv(scenario_summary_path, index=False)
    _dump_portable_json(details, details_path)
    report_path.write_text(report_text, encoding="utf-8")

    manifest = {
        "summary_csv": str(summary_path),
        "details_json": str(details_path),
        "manifest_json": str(manifest_path),
        "report_md": str(report_path),
        "scenario_summary_csv": str(scenario_summary_path),
        "n_rows": len(details),
        "n_summary_rows": int(len(summary)),
        "scenarios": sorted({row["scenario"] for row in details}),
        "settings": sorted({row["setting"] for row in details}),
    }
    _dump_portable_json(manifest, manifest_path)
    return manifest


def run_synthetic_benchmark_audit(
    output_dir: str | Path = DEFAULT_AUDIT_OUTPUT_DIR,
    seeds: Iterable[int] | None = None,
    scenario_names: Iterable[str] | None = None,
    setting_names: Iterable[str] | None = None,
) -> dict[str, Any]:
    if seeds is None:
        seeds = range(30)
    seeds = [int(seed) for seed in seeds]

    if scenario_names is None:
        scenario_names = SCENARIOS.keys()
    scenario_names = list(scenario_names)

    if setting_names is None:
        setting_names = ["baseline", "small_sample", "noisy_outcome", "severe_stress"]
    setting_names = list(setting_names)

    details: list[dict[str, Any]] = []
    for scenario_name in scenario_names:
        if scenario_name not in SCENARIOS:
            raise ValueError(f"Unknown synthetic scenario: {scenario_name}")
        if scenario_name not in SETTING_CATALOG:
            raise ValueError(f"No audit settings registered for scenario: {scenario_name}")

        spec = SCENARIOS[scenario_name]
        variants = _variants_for_scenario(scenario_name)
        scenario_settings = SETTING_CATALOG[scenario_name]

        for setting_name in setting_names:
            if setting_name not in scenario_settings:
                raise ValueError(
                    f"Unknown audit setting '{setting_name}' for scenario '{scenario_name}'"
                )
            setting = scenario_settings[setting_name]
            for seed in seeds:
                data, meta = setting.generator(seed)
                for variant in variants:
                    try:
                        row = spec.runner(data, meta, seed, variant)
                        row["setting"] = setting.name
                        row["stress_level"] = setting.stress_level
                        details.append(row)
                    except Exception as exc:
                        row = _error_row(
                            scenario=spec.name,
                            method=spec.method,
                            seed=seed,
                            metric_name="unknown",
                            variant=variant,
                            error=str(exc),
                        )
                        row["setting"] = setting.name
                        row["stress_level"] = setting.stress_level
                        details.append(row)

    return write_audit_outputs(details, output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Paper 6 synthetic benchmark audit.")
    parser.add_argument("--output-dir", default=str(DEFAULT_AUDIT_OUTPUT_DIR))
    parser.add_argument("--n-seeds", type=int, default=30)
    parser.add_argument(
        "--scenarios",
        default=",".join(SCENARIOS.keys()),
        help="Comma-separated scenario names. Default: all scenarios.",
    )
    parser.add_argument(
        "--settings",
        default="baseline,small_sample,noisy_outcome,severe_stress",
        help="Comma-separated setting names.",
    )
    args = parser.parse_args()

    scenarios = [item.strip() for item in args.scenarios.split(",") if item.strip()]
    settings = [item.strip() for item in args.settings.split(",") if item.strip()]
    manifest = run_synthetic_benchmark_audit(
        output_dir=args.output_dir,
        seeds=range(args.n_seeds),
        scenario_names=scenarios,
        setting_names=settings,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
