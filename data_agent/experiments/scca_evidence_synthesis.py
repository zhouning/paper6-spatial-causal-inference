"""Unified SCCA evidence synthesis for the Paper 6 manuscript rebuild."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from data_agent.scca.evidence_rules import (
    RULE_VERSION,
    assess_scca_evidence_grade,
    write_evidence_rule_outputs,
)


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
    "grade_rule_ids",
    "grade_reasons",
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
    grade_rule_ids: str = "",
    grade_reasons: str = "",
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
        "grade_rule_ids": grade_rule_ids,
        "grade_reasons": grade_reasons,
        "limitation": limitation,
        "manuscript_use": manuscript_use,
    }


def _assessment_text(assessment: dict[str, Any]) -> tuple[str, str, str]:
    rules = assessment.get("triggered_rules", [])
    reasons = assessment.get("reasons", [])
    rule_text = "; ".join(map(str, rules)) if isinstance(rules, list) else str(rules)
    reason_text = "; ".join(map(str, reasons)) if isinstance(reasons, list) else str(reasons)
    return str(assessment.get("evidence_grade", "bounded_support")), rule_text, reason_text


def _spatial_summary_from_chongqing(results_dir: Path, variant: str) -> dict[str, Any]:
    residuals = _read_csv(results_dir / "chongqing_residual_spatial_diagnostics.csv")
    if residuals.empty:
        return {}
    rows = residuals.loc[residuals.get("variant").astype(str) == variant]
    if rows.empty:
        rows = residuals.head(1)
    record = rows.iloc[0]
    return {
        "residual_moran_i": record.get("moran_i"),
        "residual_moran_p_value": record.get("permutation_p_value"),
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
        rule_ids = "synthetic_fragility"
        grade_reasons = (
            "At least one controlled scenario produced fragile estimator behavior."
        )
        robustness = f"{n_robust}/{n_rows} robust rows; {n_fragile} fragile rows"
        limitation = "Stress audit found fragile estimator settings, especially for direction-recovery cases."
    else:
        grade = "core_support"
        rule_ids = ""
        grade_reasons = ""
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
        grade_rule_ids=rule_ids,
        grade_reasons=grade_reasons,
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
    assessment = assess_scca_evidence_grade(
        credibility_decision="strong_support" if balance_pass else "moderate_support",
        robustness_interpretation="robust_support",
        spatial_summary=_spatial_summary_from_chongqing(results_dir, str(record.get("variant"))),
    )
    grade, rule_ids, grade_reasons = _assessment_text(assessment)
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
        grade_rule_ids=rule_ids,
        grade_reasons=grade_reasons,
        limitation="MODIS LST scale, building-level treatment assignment, and spatial interference limit causal strength.",
        manuscript_use="Use as the main real-data SCCA ablation; report the modest positive balanced estimate.",
    )


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

    spatial_summary = {
        "residual_moran_i": diagnostics.get("residual_moran_i"),
        "residual_moran_p_value": diagnostics.get("residual_moran_p_value"),
        "neighbor_exposure_p_value": spatial_lag.get("neighbor_exposure_p_value")
        or result_summary.get("spatial_neighbor_adjusted_ols", {}).get("neighbor_exposure_p_value"),
        "spatial_lag_relative_change": spatial_lag.get("relative_change"),
        "neighbor_adjusted_relative_change_max": graph.get("neighbor_adjusted_relative_change_max"),
        "neighbor_adjusted_sign_stability": graph.get("neighbor_adjusted_sign_stability"),
        "spatial_lag_sign_stability": graph.get("spatial_lag_sign_stability"),
    }
    assessment = assess_scca_evidence_grade(
        credibility_decision="strong_support",
        robustness_interpretation="robust_support"
        if bootstrap.get("sign_stability") == 1.0 and graph.get("neighbor_adjusted_sign_stability") is True
        else "bounded_support",
        spatial_summary=spatial_summary,
    )
    grade, rule_ids, grade_reasons = _assessment_text(assessment)

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
        evidence_grade=grade,
        grade_rule_ids=rule_ids,
        grade_reasons=grade_reasons,
        limitation=(
            "Residual spatial autocorrelation and a significant neighboring-exposure term remain, "
            "so this is spatially cautioned external evidence rather than definitive identification."
        ),
        manuscript_use=(
            "Use as the GIS/notebook spatial-output demonstration and as spatially bounded external SCCA evidence."
        ),
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
        _county_spatial_notebook_row(root),
    ):
        if optional_row is not None:
            rows.append(optional_row)
    table = pd.DataFrame(rows, columns=SYNTHESIS_COLUMNS)
    if table.empty:
        return table
    order = {
        "synthetic_benchmark_audit": 0,
        "chongqing_uhi": 1,
        "county_social_capital_spatial_notebook": 2,
    }
    table["_order"] = table["case"].map(order).fillna(99)
    return table.sort_values(["_order", "case"]).drop(columns=["_order"]).reset_index(drop=True)


def render_scca_evidence_report(table: pd.DataFrame) -> str:
    """Render a concise Markdown report for manuscript rewriting."""
    lines = [
        "# SCCA Evidence Synthesis Report",
        "",
        "This report is the evidence boundary for the revised Paper 6 manuscript.",
        f"The grade rule version is `{RULE_VERSION}`.",
        "The main paper should use the Chongqing row as the main empirical case,",
        "the synthetic row as estimator stress-test evidence,",
        "and the county row as a GIS/notebook reproducibility and spatial-diagnostic boundary check.",
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
                f"- Grade rules: `{record['grade_rule_ids']}`",
                f"- Grade reasons: {record['grade_reasons'] or 'No downgrade rules triggered.'}",
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
    grade_rule_manifest = write_evidence_rule_outputs(target)

    table.to_csv(synthesis_path, index=False)
    report_path.write_text(render_scca_evidence_report(table), encoding="utf-8")

    manifest = {
        "synthesis_csv": str(synthesis_path),
        "report_md": str(report_path),
        "manifest_json": str(manifest_path),
        "grade_rules_json": grade_rule_manifest["rules_json"],
        "grade_rules_md": grade_rule_manifest["rules_md"],
        "results_dir": str(Path(results_dir)),
        "n_rows": int(len(table)),
        "grade_counts": table["evidence_grade"].value_counts().to_dict() if not table.empty else {},
        "rule_version": grade_rule_manifest["rule_version"],
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
