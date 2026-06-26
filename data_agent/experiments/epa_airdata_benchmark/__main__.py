from __future__ import annotations

import argparse
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

from geocausal.config import load_config
from geocausal.pipeline import run_analysis

from . import (
    add_neighbor_exposure,
    make_semisynthetic_scenarios,
    write_geocausal_config,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "epa_airdata"
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results" / "epa_nonattainment_airdata"
)


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    try:
        import numpy as np

        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, (np.floating, float)):
            numeric = float(value)
            return numeric if pd.notna(numeric) else None
    except Exception:
        pass
    return value


def _county_fips(state: object, county: object) -> str:
    state_text = str(int(state)).zfill(2) if pd.notna(state) else ""
    county_text = str(int(county)).zfill(3) if pd.notna(county) else ""
    return state_text + county_text


def load_greenbook_pm25_status(nayro_path: Path, *, years: list[int]) -> pd.DataFrame:
    raw = pd.read_excel(nayro_path, sheet_name="nayro")
    raw.columns = [str(column).strip().lower() for column in raw.columns]
    pm25 = raw[raw["pollutant"].astype(str).str.contains("PM-2.5", case=False, na=False)].copy()
    pm25["county_fips"] = [_county_fips(s, c) for s, c in zip(pm25["fips_state"], pm25["fips_cnty"], strict=False)]
    rows: list[dict[str, Any]] = []
    for county_fips, group in pm25.groupby("county_fips"):
        for year in years:
            col = f"yr{year}"
            value = 0
            if col in group.columns:
                value = int(group[col].notna().any())
            rows.append({"county_fips": county_fips, "year": int(year), "nonattainment": value})
    return pd.DataFrame(rows)


def load_county_centroids_and_adjacency(county_zip: Path) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    with zipfile.ZipFile(county_zip) as zf:
        shp_names = [name for name in zf.namelist() if name.endswith(".shp")]
    if not shp_names:
        raise ValueError(f"No shapefile found in {county_zip}")
    counties = gpd.read_file(f"zip://{county_zip}!{shp_names[0]}")
    counties = counties.to_crs("EPSG:5070")
    counties["county_fips"] = counties["GEOID"].astype(str).str.zfill(5)
    representative = counties.geometry.representative_point()
    centroids = pd.DataFrame(
        {
            "county_fips": counties["county_fips"],
            "x": representative.x,
            "y": representative.y,
        }
    )

    contiguous = counties[~counties["STATEFP"].astype(str).isin({"02", "15", "60", "66", "69", "72", "78"})].copy()
    adjacency: dict[str, list[str]] = {fips: [] for fips in contiguous["county_fips"]}
    spatial_index = contiguous.sindex
    geometries = contiguous.geometry.reset_index(drop=True)
    fips_values = contiguous["county_fips"].reset_index(drop=True)
    for idx, geometry in enumerate(geometries):
        candidates = list(spatial_index.query(geometry, predicate="intersects"))
        source_fips = str(fips_values.iloc[idx])
        neighbors = []
        for candidate in candidates:
            if candidate == idx:
                continue
            target_fips = str(fips_values.iloc[candidate])
            if geometry.touches(geometries.iloc[candidate]) or geometry.intersects(geometries.iloc[candidate]):
                neighbors.append(target_fips)
        adjacency[source_fips] = sorted(set(neighbors))
    return centroids, adjacency




def _baseline_effect_from_run(run_dir: Path) -> float:
    estimates = pd.read_csv(run_dir / "effect_estimates.csv")
    baseline = estimates.loc[estimates["estimator"] == "baseline_adjusted_ols"]
    if not baseline.empty:
        return float(baseline.iloc[0]["coef"])
    return float(estimates.iloc[0]["coef"])


def summarize_semisynthetic_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    metrics: list[dict[str, Any]] = []
    for record in records:
        true_effect = float(record["true_effect"])
        effect = float(record["effect_estimate"])
        metric = dict(record)
        metric["absolute_error"] = abs(effect - true_effect)
        metrics.append(metric)
    errors = pd.Series([metric["absolute_error"] for metric in metrics], dtype="float64")
    spatial_caution = [
        str(metric["scenario"])
        for metric in metrics
        if str(metric.get("scenario")) != "stable_known_effect"
        or str(metric.get("evidence_grade")) == "bounded_support"
    ]
    return {
        "scenario_count": len(metrics),
        "median_absolute_error": float(errors.median()) if not errors.empty else None,
        "mean_absolute_error": float(errors.mean()) if not errors.empty else None,
        "max_absolute_error": float(errors.max()) if not errors.empty else None,
        "spatial_caution_scenarios": sorted(set(spatial_caution)),
        "scenario_metrics": metrics,
    }


def _run_scca_scenario(
    *,
    scenario: str,
    panel_path: Path,
    output_dir: Path,
    config_path: Path,
    true_effect: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    write_geocausal_config(
        panel_path=panel_path,
        output_dir=output_dir,
        config_path=config_path,
    )
    manifest = run_analysis(load_config(config_path))
    effect = _baseline_effect_from_run(output_dir)
    metric = {
        "scenario": scenario,
        "effect_estimate": effect,
        "true_effect": true_effect,
        "absolute_error": abs(effect - true_effect),
        "evidence_grade": manifest.get("evidence_grade"),
        "grade_rule_ids": manifest.get("evidence_grade_rule_ids", []),
        "grade_reasons": manifest.get("evidence_grade_reasons", []),
        "run_dir": str(output_dir),
        "config_path": str(config_path),
    }
    return manifest, metric
def build_policy_structure_panel(
    *,
    raw_dir: Path,
    output_dir: Path,
    years: list[int],
    true_effect: float,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    status = load_greenbook_pm25_status(raw_dir / "nayro.xls", years=years)
    centroids, adjacency = load_county_centroids_and_adjacency(raw_dir / "cb_2024_us_county_500k.zip")
    panel = status.merge(centroids, on="county_fips", how="inner")
    panel = panel.sort_values(["county_fips", "year"]).reset_index(drop=True)
    panel["nonattainment_lag1"] = panel.groupby("county_fips")["nonattainment"].shift(1).fillna(0)
    panel = add_neighbor_exposure(
        panel,
        adjacency,
        exposure_col="nonattainment_lag1",
        output_col="neighbor_nonattainment_lag1",
    )
    panel["year_index"] = panel["year"] - min(years)
    panel["monitor_count"] = 1.0
    panel["baseline_annual_mean"] = (
        9.0
        - 0.04 * panel["year_index"]
        + 0.0000015 * (panel["x"] - panel["x"].mean())
        + 0.0000010 * (panel["y"] - panel["y"].mean())
        + 0.15 * panel["neighbor_nonattainment_lag1"]
    )
    scenarios = make_semisynthetic_scenarios(panel, true_effect=true_effect)
    stable = scenarios["stable_known_effect"].frame.copy()
    stable["annual_mean"] = stable["synthetic_outcome"]
    stable["pollutant_code"] = 88101
    stable["observation_count"] = 365
    stable["county_year_id"] = stable["county_fips"] + "_" + stable["year"].astype(str)
    analysis_columns = [
        "county_year_id",
        "county_fips",
        "year",
        "pollutant_code",
        "annual_mean",
        "baseline_annual_mean",
        "nonattainment",
        "nonattainment_lag1",
        "neighbor_nonattainment_lag1",
        "monitor_count",
        "observation_count",
        "year_index",
        "x",
        "y",
    ]
    panel_path = output_dir / "epa_policy_structure_semisynthetic_panel.csv"
    stable[analysis_columns].to_csv(panel_path, index=False)
    scenario_dir = output_dir / "semi_synthetic"
    scenario_dir.mkdir(exist_ok=True)
    scenario_rows = []
    for name, scenario in scenarios.items():
        frame = scenario.frame.copy()
        frame["annual_mean"] = frame["synthetic_outcome"]
        frame["pollutant_code"] = 88101
        frame["observation_count"] = 365
        frame["county_year_id"] = frame["county_fips"] + "_" + frame["year"].astype(str)
        scenario_path = scenario_dir / f"{name}.csv"
        frame[[*analysis_columns, "synthetic_outcome"]].to_csv(scenario_path, index=False)
        scenario_rows.append(
            {
                "scenario": name,
                "path": str(scenario_path),
                **scenario.metadata,
            }
        )
    pd.DataFrame(scenario_rows).to_csv(output_dir / "semi_synthetic_scenarios.csv", index=False)
    scenario_metrics: list[dict[str, Any]] = []
    scenario_manifest_paths: dict[str, str] = {}
    stable_manifest: dict[str, Any] | None = None
    stable_metric: dict[str, Any] | None = None
    for scenario_row in scenario_rows:
        scenario_name = str(scenario_row["scenario"])
        scenario_path = Path(str(scenario_row["path"]))
        if scenario_name == "stable_known_effect":
            run_dir = output_dir / "scca_run"
            scenario_config_path = output_dir / "epa_policy_structure_semisynthetic.yaml"
        else:
            run_dir = output_dir / f"scca_run_{scenario_name}"
            scenario_config_path = output_dir / f"epa_policy_structure_semisynthetic_{scenario_name}.yaml"
        scenario_manifest, scenario_metric = _run_scca_scenario(
            scenario=scenario_name,
            panel_path=scenario_path,
            output_dir=run_dir,
            config_path=scenario_config_path,
            true_effect=float(scenario_row.get("true_effect", true_effect)),
        )
        for key, value in scenario_row.items():
            if key not in {"scenario", "path", "true_effect"}:
                scenario_metric[key] = value
        scenario_metrics.append(scenario_metric)
        scenario_manifest_paths[scenario_name] = str(run_dir / "manifest.json")
        if scenario_name == "stable_known_effect":
            stable_manifest = scenario_manifest
            stable_metric = scenario_metric
    if stable_manifest is None or stable_metric is None:
        raise RuntimeError("stable_known_effect scenario did not run")
    pd.DataFrame(scenario_metrics).to_csv(output_dir / "semi_synthetic_scenario_metrics.csv", index=False)
    semisynthetic_summary = summarize_semisynthetic_metrics(scenario_metrics)
    manifest = stable_manifest
    effect = float(stable_metric["effect_estimate"])
    abs_error = float(stable_metric["absolute_error"])
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "benchmark_role": "policy_structure_semisynthetic_until_airdata_download_recovers",
        "airdata_status": "AQS AirData downloads and API timed out from this environment; Green Book and Census inputs were acquired.",
        "raw_sources": {
            "greenbook_nayro": str(raw_dir / "nayro.xls"),
            "census_counties": str(raw_dir / "cb_2024_us_county_500k.zip"),
        },
        "real_data": {
            "effect_estimate": effect,
            "evidence_grade": manifest.get("evidence_grade"),
            "grade_rule_ids": manifest.get("evidence_grade_rule_ids", []),
            "grade_reasons": manifest.get("evidence_grade_reasons", []),
            "row_count": int(len(stable)),
            "panel_year_min": int(stable["year"].min()),
            "panel_year_max": int(stable["year"].max()),
            "true_effect": true_effect,
            "absolute_error": abs_error,
        },
        "semi_synthetic": {
            **semisynthetic_summary,
            "scenario_csv": str(output_dir / "semi_synthetic_scenarios.csv"),
            "scenario_metrics_csv": str(output_dir / "semi_synthetic_scenario_metrics.csv"),
            "scenario_manifest_paths": scenario_manifest_paths,
        },
        "policy_structure_semisynthetic": {
            "effect_estimate": effect,
            "evidence_grade": manifest.get("evidence_grade"),
            "grade_rule_ids": manifest.get("evidence_grade_rule_ids", []),
            "grade_reasons": manifest.get("evidence_grade_reasons", []),
            "row_count": int(len(stable)),
            "panel_year_min": int(stable["year"].min()),
            "panel_year_max": int(stable["year"].max()),
            "true_effect": true_effect,
            "absolute_error": abs_error,
        },
        "scca_manifest": manifest,
    }
    (output_dir / "benchmark_summary.json").write_text(
        json.dumps(_json_ready(summary), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report = [
        "# EPA Nonattainment AirData Benchmark",
        "",
        "AQS AirData downloads timed out in this environment, so this run uses acquired",
        "EPA Green Book PM2.5 county-year nonattainment structure and Census county",
        "geometry with a deterministic known-effect pollution outcome.",
        "",
        f"- Rows: {len(stable)}",
        f"- Years: {int(stable['year'].min())}-{int(stable['year'].max())}",
        f"- True effect: {true_effect:.3f}",
        f"- Estimated baseline coefficient: {effect:.3f}",
        f"- Stable known-effect absolute error: {abs_error:.3f}",
        f"- Median scenario absolute error: {semisynthetic_summary['median_absolute_error']:.3f}",
        f"- Max scenario absolute error: {semisynthetic_summary['max_absolute_error']:.3f}",
        f"- Evidence grade: `{manifest.get('evidence_grade')}`",
        "",
        "This artifact is a semi-synthetic SCCA validation benchmark on real EPA policy",
        "geography, not a completed observational AirData policy estimate.",
        "",
    ]
    (output_dir / "benchmark_summary.md").write_text("\n".join(report), encoding="utf-8")
    return summary


def _parse_years(value: str) -> list[int]:
    if "-" in value:
        start, end = value.split("-", 1)
        return list(range(int(start), int(end) + 1))
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the EPA policy-structure SCCA benchmark.")
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--years", default="2005-2024")
    parser.add_argument("--true-effect", type=float, default=-1.0)
    args = parser.parse_args()
    summary = build_policy_structure_panel(
        raw_dir=Path(args.raw_dir),
        output_dir=Path(args.output_dir),
        years=_parse_years(args.years),
        true_effect=args.true_effect,
    )
    print(json.dumps(_json_ready(summary), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
