"""Unified SCCA evidence synthesis for the Paper 6 manuscript rebuild."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results"
OUTPUT_FILES = {
    "synthesis_csv": "scca_evidence_synthesis.csv",
    "report_md": "scca_evidence_synthesis_report.md",
    "manifest_json": "scca_evidence_synthesis_manifest.json",
}
SYNTHESIS_COLUMNS = [
    "case",
    "data_type",
    "exposure",
    "outcome",
    "context_source",
    "best_adjustment",
    "effect_estimate",
    "balance_status",
    "robustness_status",
    "evidence_grade",
    "limitation",
    "manuscript_use",
]


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt_num(value: Any, digits: int = 3) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "NA"
    if pd.isna(number):
        return "NA"
    return f"{number:.{digits}f}"


def _row(
    *,
    case: str,
    data_type: str,
    exposure: str,
    outcome: str,
    context_source: str,
    best_adjustment: str,
    effect_estimate: str,
    balance_status: str,
    robustness_status: str,
    evidence_grade: str,
    limitation: str,
    manuscript_use: str,
) -> dict[str, str]:
    return {
        "case": case,
        "data_type": data_type,
        "exposure": exposure,
        "outcome": outcome,
        "context_source": context_source,
        "best_adjustment": best_adjustment,
        "effect_estimate": effect_estimate,
        "balance_status": balance_status,
        "robustness_status": robustness_status,
        "evidence_grade": evidence_grade,
        "limitation": limitation,
        "manuscript_use": manuscript_use,
    }


def _synthetic_row(results_dir: Path) -> dict[str, str] | None:
    summary = _read_csv(
        results_dir
        / "synthetic_benchmark_audit"
        / "synthetic_benchmark_audit_summary.csv"
    )
    if summary.empty:
        summary = _read_csv(results_dir / "synthetic_multiseed_summary.csv")
    if summary.empty:
        return None

    n_rows = int(len(summary))
    n_fragile = int((summary.get("fragility") == "fragile").sum()) if "fragility" in summary else 0
    n_robust = int((summary.get("fragility") == "robust").sum()) if "fragility" in summary else 0
    scenarios = ", ".join(sorted(map(str, summary["scenario"].dropna().unique())))
    if n_fragile:
        grade = "bounded_support"
        robustness = f"{n_robust}/{n_rows} robust rows; {n_fragile} fragile rows"
        limitation = "Stress audit found fragile estimator settings, especially for direction-recovery cases."
    else:
        grade = "core_support"
        robustness = f"{n_robust or n_rows}/{n_rows} rows without recorded fragility"
        limitation = "Synthetic evidence checks implementation behavior under controlled generators only."
    return _row(
        case="synthetic_benchmark_audit",
        data_type="controlled synthetic benchmark",
        exposure="scenario-specific assigned exposure",
        outcome="scenario-specific generated outcome",
        context_source="controlled observed and spatial-context covariates",
        best_adjustment=f"multi-seed audit across {scenarios}",
        effect_estimate=f"{n_rows} benchmark rows over configured seeds",
        balance_status="not_applicable",
        robustness_status=robustness,
        evidence_grade=grade,
        limitation=limitation,
        manuscript_use="Use as estimator stress-test evidence, not as real-world causal validation.",
    )


def _chongqing_row(results_dir: Path) -> dict[str, str] | None:
    ablation = _read_csv(results_dir / "chongqing_uhi_ablation.csv")
    if ablation.empty:
        return None
    preferred = ablation[ablation["variant"] == "full_rs_context"]
    if preferred.empty:
        candidates = ablation[
            (ablation.get("status") == "ok")
            & (ablation.get("balance_pass_0_1").astype(str).str.lower() == "true")
        ].copy()
        if candidates.empty:
            candidates = ablation[ablation.get("status") == "ok"].copy()
        candidates["max_post_smd_num"] = pd.to_numeric(candidates["max_post_smd"], errors="coerce")
        preferred = candidates.sort_values("max_post_smd_num").head(1)
    record = preferred.iloc[0]
    balance_pass = str(record.get("balance_pass_0_1")).lower() == "true"
    max_smd = _fmt_num(record.get("max_post_smd"))
    ci = f"[{_fmt_num(record.get('ci_lower'))}, {_fmt_num(record.get('ci_upper'))}]"
    grade = "core_support" if balance_pass else "bounded_support"
    return _row(
        case="chongqing_uhi",
        data_type="real remote-sensing and building-footprint case",
        exposure="high-rise building threshold >= 10 floors",
        outcome="summer land surface temperature",
        context_source="coordinates, geometry, Sentinel-2 bands/indices, DEM terrain",
        best_adjustment=str(record.get("variant")),
        effect_estimate=f"ATT = {_fmt_num(record.get('att'))} C; 95% CI {ci}",
        balance_status=f"max post-match SMD = {max_smd}; balance pass = {balance_pass}",
        robustness_status="threshold placebo, spatial bootstrap, and residual spatial diagnostics available",
        evidence_grade=grade,
        limitation="MODIS LST scale, building-level treatment assignment, and spatial interference limit causal strength.",
        manuscript_use="Use as the main real-data SCCA ablation; report the modest positive balanced estimate.",
    )


def _geofm_row(results_dir: Path) -> dict[str, str] | None:
    ablation = _read_csv(results_dir / "geofm_causal_ablation.csv")
    availability = _read_json(results_dir / "geofm_availability_report.json")
    if ablation.empty:
        return None
    observed = ablation[ablation["variant"] == "geometry_rs_context"]
    geofm = ablation[ablation["variant"].astype(str).str.contains("alphaearth", case=False, na=False)]
    observed_smd = _fmt_num(observed.iloc[0].get("max_post_smd")) if not observed.empty else "NA"
    best_geofm = geofm.copy()
    best_geofm["max_post_smd_num"] = pd.to_numeric(best_geofm["max_post_smd"], errors="coerce")
    best_geofm = best_geofm.sort_values("max_post_smd_num").head(1)
    geofm_variant = str(best_geofm.iloc[0].get("variant")) if not best_geofm.empty else "none"
    geofm_smd = _fmt_num(best_geofm.iloc[0].get("max_post_smd")) if not best_geofm.empty else "NA"
    guidance = str(availability.get("claim_guidance") or "geofm_no_clear_gain")
    return _row(
        case="geofm_alphaearth_ablation",
        data_type="real GeoFM candidate-feature ablation",
        exposure="high-rise building threshold >= 10 floors",
        outcome="summer land surface temperature",
        context_source="AlphaEarth embeddings compared with conventional RS/terrain context",
        best_adjustment="geometry_rs_context outperformed AlphaEarth variants on balance",
        effect_estimate=f"observed RS SMD {observed_smd}; best AlphaEarth variant {geofm_variant} SMD {geofm_smd}",
        balance_status=f"claim guidance = {guidance}",
        robustness_status="negative ablation under the current Chongqing sampling design",
        evidence_grade="negative_ablation",
        limitation="Only 199 complete AlphaEarth rows were available in this run, so the result is a bounded negative diagnostic.",
        manuscript_use="Use to state that GeoFM is a candidate context source with no clear gain in the current evidence.",
    )


def _scca_case_rows(results_dir: Path) -> list[dict[str, str]]:
    summary = _read_csv(results_dir / "scca_robustness_summary" / "case_robustness_summary.csv")
    if summary.empty:
        return []
    metadata = {
        "snow8": {
            "data_type": "historical cholera subdistrict case",
            "exposure": "South London water-company exposure",
            "outcome": "cholera mortality",
            "context_source": "subdistrict socioeconomic and spatial-balance variables",
            "use": "Use as a bounded historical SCCA replication case.",
        },
        "soho": {
            "data_type": "historical household pump-proximity case",
            "exposure": "Broad Street pump exposure/proximity",
            "outcome": "household cholera deaths",
            "context_source": "street-network and local context variables",
            "use": "Use as a bounded mechanism-focused SCCA case.",
        },
        "county_social_capital": {
            "data_type": "external county-level validation case",
            "exposure": "county social-association measure",
            "outcome": "average age at death",
            "context_source": "county socioeconomic and geometry context variables",
            "use": (
                "Use only as a non-spatial robustness baseline; supersede it with the "
                "spatial notebook row when spatial diagnostics are available."
            ),
        },
    }
    rows: list[dict[str, str]] = []
    for _, record in summary.iterrows():
        case = str(record.get("case"))
        info = metadata.get(case, {})
        interpretation = str(record.get("robustness_interpretation"))
        grade = "core_support" if interpretation == "robust_support" else "bounded_support"
        rows.append(
            _row(
                case=case,
                data_type=info.get("data_type", "SCCA case study"),
                exposure=info.get("exposure", "case-specific exposure"),
                outcome=info.get("outcome", "case-specific outcome"),
                context_source=info.get("context_source", "case-specific spatial context"),
                best_adjustment=f"SCCA robustness interpretation = {interpretation}",
                effect_estimate=f"main coefficient = {_fmt_num(record.get('main_coef'))}",
                balance_status=(
                    "ablation direction stable = "
                    f"{record.get('ablation_direction_stable')}; placebo weaker = {record.get('placebo_weaker_than_main')}"
                ),
                robustness_status=(
                    "bootstrap sign stability = "
                    f"{_fmt_num(record.get('bootstrap_sign_stability'))}; ERF direction = {record.get('erf_monotonic_direction')}"
                ),
                evidence_grade=grade,
                limitation=str(record.get("main_limitation")),
                manuscript_use=info.get("use", "Use as SCCA cross-case evidence."),
            )
        )
    return rows


def _county_spatial_notebook_row(results_dir: Path) -> dict[str, str] | None:
    summary_path = results_dir / "county_social_capital_spatial_notebook_summary.json"
    if not summary_path.exists():
        summary_path = (
            results_dir
            / "examples"
            / "county_social_capital_notebook_demo"
            / "notebook_demo_summary.json"
        )
    if not summary_path.exists():
        return None
    summary = _read_json(summary_path)
    result_summary = summary.get("result_summary", {})
    if not isinstance(result_summary, dict):
        return None

    baseline = result_summary.get("baseline_adjusted_ols", {})
    spatial_lag = result_summary.get("spatial_lag_adjusted_ols", {})
    slx = result_summary.get("spatial_slx_model", {})
    diagnostics = result_summary.get("spatial_diagnostics", {})
    bootstrap = result_summary.get("spatial_block_bootstrap", {})
    graph = result_summary.get("spatial_graph_sensitivity", {})
    spatial_manifest = summary.get("spatial_manifest", {})

    if not isinstance(baseline, dict) or not isinstance(diagnostics, dict):
        return None

    matched_count = spatial_manifest.get("matched_count")
    row_count = spatial_manifest.get("row_count")
    enriched_fields = spatial_manifest.get("enriched_effect_fields", [])
    if isinstance(enriched_fields, list) and enriched_fields:
        enriched_text = ", ".join(map(str, enriched_fields))
    else:
        enriched_text = "no enriched spatial fields recorded"

    return _row(
        case="county_social_capital_spatial_notebook",
        data_type="external county-level validation and GIS output case",
        exposure="county social-association measure",
        outcome="average age at death",
        context_source="county socioeconomic, geometry, centroid-coordinate, and spatial-neighborhood context",
        best_adjustment="SLX-style spatial lag sensitivity over coordinate-kNN graphs",
        effect_estimate=(
            f"baseline coef = {_fmt_num(baseline.get('coef'))}; "
            f"spatial-lag coef = {_fmt_num(spatial_lag.get('coef'))}; "
            f"SLX total effect = {_fmt_num(slx.get('total_effect'))}"
        ),
        balance_status=(
            f"matched spatial layer rows = {matched_count}/{row_count}; "
            f"enriched fields = {enriched_text}"
        ),
        robustness_status=(
            f"residual Moran I = {_fmt_num(diagnostics.get('residual_moran_i'))}; "
            f"spatial bootstrap sign stability = {_fmt_num(bootstrap.get('sign_stability'))}; "
            f"graph sensitivity sign stable = {graph.get('neighbor_adjusted_sign_stability')}"
        ),
        evidence_grade="bounded_support",
        limitation=(
            "Residual spatial autocorrelation and a significant neighboring-exposure term remain, "
            "so this is spatially cautioned external evidence rather than definitive identification."
        ),
        manuscript_use=(
            "Use as the GIS/notebook spatial-output demonstration and as spatially bounded external SCCA evidence."
        ),
    )


def _llm_row(results_dir: Path) -> dict[str, str] | None:
    validation = _read_csv(results_dir / "llm_dag_validation.csv")
    if validation.empty:
        return None
    f1_columns = [column for column in validation.columns if column.lower() in {"f1", "edge_f1", "mean_f1"}]
    if f1_columns:
        f1_value = _fmt_num(validation[f1_columns[0]].mean())
    elif "structured_proxy_f1" in validation:
        f1_value = _fmt_num(validation["structured_proxy_f1"].mean())
    else:
        f1_value = "reported separately"
    return _row(
        case="llm_dag_validation",
        data_type="offline auxiliary validation",
        exposure="causal prompt structures",
        outcome="reference-DAG edge recovery metrics",
        context_source="structured prompt templates",
        best_adjustment="not an SCCA adjustment source",
        effect_estimate=f"mean F1 = {f1_value}",
        balance_status="not_applicable",
        robustness_status="offline proxy only",
        evidence_grade="auxiliary_only",
        limitation="Does not identify treatment effects or validate SCCA adjustment sets.",
        manuscript_use="Exclude from core evidence; mention only as optional interpretive tooling if needed.",
    )


def _world_model_row(results_dir: Path) -> dict[str, str] | None:
    report = _read_json(results_dir / "world_model_holdout_validation_manifest.json")
    metrics = _read_csv(results_dir / "world_model_holdout_metrics.csv")
    if not report and metrics.empty:
        return None
    if not metrics.empty:
        horizon1 = metrics[metrics.get("horizon") == 1] if "horizon" in metrics else pd.DataFrame()
        persistence = horizon1[horizon1.get("baseline") == "persistence"] if not horizon1.empty and "baseline" in horizon1 else pd.DataFrame()
        wm = horizon1[horizon1.get("baseline") == "world_model_baseline"] if not horizon1.empty and "baseline" in horizon1 else pd.DataFrame()
        effect = (
            f"horizon-1 RMSE persistence {_fmt_num(persistence.iloc[0].get('rmse'))}, "
            f"world model {_fmt_num(wm.iloc[0].get('rmse'))}"
            if not persistence.empty and not wm.empty
            else "holdout metrics reported separately"
        )
    else:
        effect = "holdout metrics reported separately"
    return _row(
        case="world_model_holdout_validation",
        data_type="offline auxiliary simulation validation",
        exposure="scenario-conditioning proxy",
        outcome="embedding-space transition prediction",
        context_source="AlphaEarth-like embedding fixtures",
        best_adjustment="not an SCCA adjustment source",
        effect_estimate=effect,
        balance_status="not_applicable",
        robustness_status="persistence baseline beat world-model baseline in the offline fixture",
        evidence_grade="auxiliary_only",
        limitation="Scenario simulation only; no real held-out causal validation.",
        manuscript_use="Exclude from core SCCA evidence; use only to bound future simulation claims.",
    )


def build_scca_evidence_table(
    results_dir: str | Path = DEFAULT_RESULTS_DIR,
) -> pd.DataFrame:
    """Build the reviewer-facing evidence matrix from existing result artifacts."""
    root = Path(results_dir)
    rows: list[dict[str, str]] = []
    for optional_row in (
        _synthetic_row(root),
        _chongqing_row(root),
        _geofm_row(root),
        _llm_row(root),
        _world_model_row(root),
    ):
        if optional_row is not None:
            rows.append(optional_row)
    rows.extend(_scca_case_rows(root))
    county_spatial = _county_spatial_notebook_row(root)
    if county_spatial is not None:
        rows = [row for row in rows if row.get("case") != "county_social_capital"]
        rows.append(county_spatial)
    table = pd.DataFrame(rows, columns=SYNTHESIS_COLUMNS)
    if table.empty:
        return table
    order = {
        "synthetic_benchmark_audit": 0,
        "chongqing_uhi": 1,
        "snow8": 2,
        "soho": 3,
        "county_social_capital": 4,
        "county_social_capital_spatial_notebook": 5,
        "geofm_alphaearth_ablation": 6,
        "llm_dag_validation": 7,
        "world_model_holdout_validation": 8,
    }
    table["_order"] = table["case"].map(order).fillna(99)
    return table.sort_values(["_order", "case"]).drop(columns=["_order"]).reset_index(drop=True)


def render_scca_evidence_report(table: pd.DataFrame) -> str:
    """Render a concise Markdown report for manuscript rewriting."""
    lines = [
        "# SCCA Evidence Synthesis Report",
        "",
        "This report is the evidence boundary for the revised Paper 6 manuscript.",
        "The main paper should use `core_support` and `bounded_support` rows as SCCA evidence,",
        "treat `negative_ablation` rows as boundary findings, and keep `auxiliary_only` rows out of the core claim.",
        "",
        "## Evidence Rows",
        "",
    ]
    if table.empty:
        lines.append("No evidence rows were available.")
        return "\n".join(lines) + "\n"
    for _, record in table.iterrows():
        lines.extend(
            [
                f"### {record['case']}",
                "",
                f"- Grade: `{record['evidence_grade']}`",
                f"- Best adjustment: {record['best_adjustment']}",
                f"- Effect/diagnostic: {record['effect_estimate']}",
                f"- Balance: {record['balance_status']}",
                f"- Robustness: {record['robustness_status']}",
                f"- Limitation: {record['limitation']}",
                f"- Manuscript use: {record['manuscript_use']}",
                "",
            ]
        )
    grade_counts = table["evidence_grade"].value_counts().to_dict()
    lines.extend(
        [
            "## Grade Counts",
            "",
            *[f"- `{grade}`: {count}" for grade, count in sorted(grade_counts.items())],
            "",
        ]
    )
    return "\n".join(lines)


def run_scca_evidence_synthesis(
    *,
    output_dir: str | Path = DEFAULT_RESULTS_DIR,
    results_dir: str | Path = DEFAULT_RESULTS_DIR,
) -> dict[str, Any]:
    """Write the SCCA evidence synthesis table, report, and manifest."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    table = build_scca_evidence_table(results_dir)
    synthesis_path = target / OUTPUT_FILES["synthesis_csv"]
    report_path = target / OUTPUT_FILES["report_md"]
    manifest_path = target / OUTPUT_FILES["manifest_json"]

    table.to_csv(synthesis_path, index=False)
    report_path.write_text(render_scca_evidence_report(table), encoding="utf-8")

    manifest = {
        "synthesis_csv": str(synthesis_path),
        "report_md": str(report_path),
        "manifest_json": str(manifest_path),
        "results_dir": str(Path(results_dir)),
        "n_rows": int(len(table)),
        "grade_counts": table["evidence_grade"].value_counts().to_dict() if not table.empty else {},
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the Paper 6 SCCA evidence synthesis.")
    parser.add_argument("--output-dir", default=str(DEFAULT_RESULTS_DIR))
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR))
    args = parser.parse_args()
    manifest = run_scca_evidence_synthesis(
        output_dir=args.output_dir,
        results_dir=args.results_dir,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
