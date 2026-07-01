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
    "threshold_sensitivity_csv": "scca_grade_threshold_sensitivity.csv",
    "threshold_sensitivity_md": "scca_grade_threshold_sensitivity.md",
    "chongqing_variable_role_audit_csv": "chongqing_variable_role_audit.csv",
    "chongqing_variable_role_audit_md": "chongqing_variable_role_audit.md",
    "chongqing_reviewer_audit_package_csv": "chongqing_reviewer_audit_package.csv",
    "chongqing_reviewer_audit_package_json": "chongqing_reviewer_audit_package.json",
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
THRESHOLD_SENSITIVITY_COLUMNS = [
    "case",
    "residual_moran_i",
    "residual_moran_p_value",
    "residual_moran_abs_threshold",
    "evidence_grade",
    "grade_rule_ids",
    "residual_moran_status",
    "diagnostic_flags",
]
DEFAULT_RESIDUAL_MORAN_THRESHOLDS = (0.10, 0.15, 0.20)
CHONGQING_VARIABLE_ROLE_COLUMNS = [
    "context_group",
    "variables",
    "causal_role",
    "main_model_use",
    "post_treatment_risk",
    "sensitivity_variant",
    "sensitivity_att_c",
    "sensitivity_max_post_smd",
    "sensitivity_balance_pass",
    "interpretation",
]
CHONGQING_REVIEWER_AUDIT_COLUMNS = [
    "item",
    "value",
    "source_file",
    "privacy_status",
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


def _joined_text(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(map(str, value))
    if value is None:
        return ""
    return str(value)


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
    # Primary causal specification is the pre-treatment confounder-only set
    # (coordinates + geometry + terrain), chosen on causal-validity grounds
    # rather than on post-match balance. full_rs_context is retained only as an
    # over-adjustment comparison because Sentinel surfaces may be mediators.
    primary_variant = "pre_treatment"
    preferred = ablation[ablation["variant"] == primary_variant]
    if preferred.empty:
        preferred = ablation[ablation["variant"] == "terrain"]
        primary_variant = "terrain"
    if preferred.empty:
        candidates = ablation[ablation.get("status") == "ok"].copy()
        candidates["max_post_smd_num"] = pd.to_numeric(candidates["max_post_smd"], errors="coerce")
        preferred = candidates.sort_values("max_post_smd_num").head(1)
        primary_variant = str(preferred.iloc[0].get("variant")) if not preferred.empty else primary_variant
    record = preferred.iloc[0]
    balance_pass = str(record.get("balance_pass_0_1")).lower() == "true"
    max_smd = _fmt_num(record.get("max_post_smd"))
    ci = f"[{_fmt_num(record.get('ci_lower'))}, {_fmt_num(record.get('ci_upper'))}]"

    # Over-adjustment comparison row.
    full = ablation[ablation["variant"] == "full_rs_context"]
    full_att = _fmt_num(full.iloc[0].get("att")) if not full.empty else "NA"

    # Change-of-support consequence (pixel-aggregated estimand vs building-level).
    cos = _read_csv(results_dir / "chongqing_change_of_support.csv")
    cos_text = ""
    if not cos.empty:
        prim = cos[(cos["variant"] == primary_variant) | (cos["variant"] == "pre_treatment")]
        naive = prim[prim["estimand"] == "building_cluster_robust"]
        pixel = prim[prim["estimand"] == "pixel_aggregated"]
        if not naive.empty and not pixel.empty:
            cos_text = (
                f"; cluster-robust building ATT = {_fmt_num(naive.iloc[0].get('att'))} "
                f"(CR SE {_fmt_num(naive.iloc[0].get('se'))}), "
                f"pixel-aggregated ATT = {_fmt_num(pixel.iloc[0].get('att'))}"
            )

    # Credibility: pre-treatment set has weaker post-match balance
    # (max SMD ~0.10) than the over-adjusted full set, so we do not overstate.
    credibility = "strong_support" if balance_pass else "moderate_support"
    assessment = assess_scca_evidence_grade(
        credibility_decision=credibility,
        robustness_interpretation="robust_support",
        spatial_summary=_spatial_summary_from_chongqing(results_dir, primary_variant),
    )
    grade, rule_ids, grade_reasons = _assessment_text(assessment)
    return _row(
        case="chongqing_uhi",
        data_type="real remote-sensing and building-footprint case",
        exposure="high-rise building threshold >= 10 floors",
        outcome="summer land surface temperature (MODIS MOD11A2, ~1 km)",
        context_source="coordinates, geometry, DEM terrain (pre-treatment); Sentinel-2 as over-adjustment comparison",
        best_adjustment=f"{primary_variant} (pre-treatment confounder set)",
        effect_estimate=(
            f"ATT = {_fmt_num(record.get('att'))} C; 95% CI {ci}; "
            f"over-adjusted full-RS ATT = {full_att} C{cos_text}"
        ),
        balance_status=f"max post-match SMD = {max_smd}; balance pass = {balance_pass}",
        robustness_status="threshold placebo, spatial bootstrap, residual spatial, and change-of-support diagnostics available",
        evidence_grade=grade,
        grade_rule_ids=rule_ids,
        grade_reasons=grade_reasons,
        limitation=(
            "Outcome retrieved at ~1 km while treatment is building-level (change-of-support), "
            "residual spatial structure remains, and Sentinel surfaces may be post-treatment; "
            "these bound the causal strength."
        ),
        manuscript_use="Use as the main real-data SCCA case; report the pre-treatment estimate with change-of-support and residual-spatial caution.",
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
            "so this is spatially cautioned external evidence rather than identification evidence."
        ),
        manuscript_use=(
            "Use as the GIS/notebook spatial-output demonstration and as spatially bounded external SCCA evidence."
        ),
    )


def _county_threshold_sensitivity_input(results_dir: Path) -> dict[str, Any] | None:
    summary_path = results_dir / "county_social_capital_spatial_notebook_summary.json"
    if not summary_path.exists():
        return None
    summary = _read_json(summary_path)
    result_summary = summary.get("result_summary", {})
    if not isinstance(result_summary, dict):
        return None
    spatial_lag = result_summary.get("spatial_lag_adjusted_ols", {})
    diagnostics = result_summary.get("spatial_diagnostics", {})
    bootstrap = result_summary.get("spatial_block_bootstrap", {})
    graph = result_summary.get("spatial_graph_sensitivity", {})
    if not isinstance(diagnostics, dict):
        return None
    return {
        "case": "county_social_capital_spatial_notebook",
        "credibility_decision": "strong_support",
        "robustness_interpretation": (
            "robust_support"
            if bootstrap.get("sign_stability") == 1.0 and graph.get("neighbor_adjusted_sign_stability") is True
            else "bounded_support"
        ),
        "spatial_summary": {
            "residual_moran_i": diagnostics.get("residual_moran_i"),
            "residual_moran_p_value": diagnostics.get("residual_moran_p_value"),
            "neighbor_exposure_p_value": spatial_lag.get("neighbor_exposure_p_value")
            or result_summary.get("spatial_neighbor_adjusted_ols", {}).get("neighbor_exposure_p_value"),
            "spatial_lag_relative_change": spatial_lag.get("relative_change"),
            "neighbor_adjusted_relative_change_max": graph.get("neighbor_adjusted_relative_change_max"),
            "neighbor_adjusted_sign_stability": graph.get("neighbor_adjusted_sign_stability"),
            "spatial_lag_sign_stability": graph.get("spatial_lag_sign_stability"),
        },
    }


def build_residual_moran_threshold_sensitivity(
    results_dir: str | Path = DEFAULT_RESULTS_DIR,
    thresholds: tuple[float, ...] = DEFAULT_RESIDUAL_MORAN_THRESHOLDS,
) -> pd.DataFrame:
    """Re-grade cases after varying only the material residual Moran threshold."""
    root = Path(results_dir)
    cases: list[dict[str, Any]] = []
    chongqing_spatial = _spatial_summary_from_chongqing(root, "pre_treatment")
    if not chongqing_spatial:
        chongqing_spatial = _spatial_summary_from_chongqing(root, "full_rs_context")
    if chongqing_spatial:
        cases.append(
            {
                "case": "chongqing_pre_treatment",
                "credibility_decision": "strong_support",
                "robustness_interpretation": "robust_support",
                "spatial_summary": chongqing_spatial,
            }
        )
    county_case = _county_threshold_sensitivity_input(root)
    if county_case is not None:
        cases.append(county_case)

    rows: list[dict[str, Any]] = []
    for case in cases:
        spatial_summary = case["spatial_summary"]
        for threshold in thresholds:
            assessment = assess_scca_evidence_grade(
                credibility_decision=case["credibility_decision"],
                robustness_interpretation=case["robustness_interpretation"],
                spatial_summary=spatial_summary,
                thresholds={"material_residual_moran_abs": threshold},
            )
            rows.append(
                {
                    "case": case["case"],
                    "residual_moran_i": _finite_or_none(spatial_summary.get("residual_moran_i")),
                    "residual_moran_p_value": _finite_or_none(spatial_summary.get("residual_moran_p_value")),
                    "residual_moran_abs_threshold": float(threshold),
                    "evidence_grade": assessment["evidence_grade"],
                    "grade_rule_ids": _joined_text(assessment.get("triggered_rules")),
                    "residual_moran_status": assessment.get("residual_moran_status", ""),
                    "diagnostic_flags": _joined_text(assessment.get("diagnostic_flags")),
                }
            )
    return pd.DataFrame(rows, columns=THRESHOLD_SENSITIVITY_COLUMNS)


def _finite_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if pd.notna(number) else None


def render_residual_moran_threshold_report(table: pd.DataFrame) -> str:
    lines = [
        "# SCCA Residual Moran Threshold Sensitivity",
        "",
        "This report varies only `material_residual_moran_abs`; all other grade rules remain unchanged.",
        "",
    ]
    if table.empty:
        lines.append("No residual Moran sensitivity rows were available.")
        return "\n".join(lines) + "\n"
    lines.extend(
        [
            "| Case | Residual Moran I | p-value | Threshold | Grade | Residual status | Grade rules | Flags |",
            "|---|---:|---:|---:|---|---|---|---|",
        ]
    )
    for _, record in table.iterrows():
        lines.append(
            "| "
            f"{record['case']} | "
            f"{_fmt_num(record['residual_moran_i'])} | "
            f"{_fmt_num(record['residual_moran_p_value'])} | "
            f"{_fmt_num(record['residual_moran_abs_threshold'], 2)} | "
            f"{record['evidence_grade']} | "
            f"{record['residual_moran_status']} | "
            f"{record['grade_rule_ids'] or 'none'} | "
            f"{record['diagnostic_flags'] or 'none'} |"
        )
    lines.append("")
    return "\n".join(lines)


def _variant_row(table: pd.DataFrame, variant: str) -> pd.Series | None:
    if table.empty or "variant" not in table:
        return None
    rows = table.loc[table["variant"].astype(str) == variant]
    if rows.empty:
        return None
    return rows.iloc[0]


def build_chongqing_variable_role_audit(
    results_dir: str | Path = DEFAULT_RESULTS_DIR,
) -> pd.DataFrame:
    """Summarise the causal role and sensitivity evidence for Chongqing context variables."""
    root = Path(results_dir)
    ablation = _read_csv(root / "chongqing_uhi_ablation.csv")
    if ablation.empty:
        return pd.DataFrame(columns=CHONGQING_VARIABLE_ROLE_COLUMNS)

    specs = [
        {
            "context_group": "Coordinates",
            "variables": "building centroid x/y",
            "causal_role": "spatial proxy confounder",
            "main_model_use": "retained as core spatial context",
            "post_treatment_risk": "low",
            "sensitivity_variant": "coordinates_only",
            "interpretation": (
                "Coordinates absorb broad spatial gradients but do not by themselves "
                "control surface material or vegetation context."
            ),
        },
        {
            "context_group": "Building geometry",
            "variables": "footprint area and shape descriptors",
            "causal_role": "proxy confounder or pre-treatment morphology",
            "main_model_use": "retained as built-form context",
            "post_treatment_risk": "medium",
            "sensitivity_variant": "geometry",
            "interpretation": (
                "Geometry captures morphology correlated with both floor count and "
                "microclimate exposure, but standalone balance was weaker."
            ),
        },
        {
            "context_group": "Terrain",
            "variables": "elevation and slope",
            "causal_role": "pre-treatment confounder",
            "main_model_use": "part of the preferred pre-treatment set",
            "post_treatment_risk": "low",
            "sensitivity_variant": "terrain",
            "interpretation": (
                "Terrain is plausibly fixed before building treatment assignment and "
                "tests topographic confounding."
            ),
        },
        {
            "context_group": "Pre-treatment set",
            "variables": "coordinates, geometry, terrain (no Sentinel surfaces)",
            "causal_role": "confounder-only adjustment set",
            "main_model_use": "PREFERRED causal specification",
            "post_treatment_risk": "low",
            "sensitivity_variant": "pre_treatment",
            "interpretation": (
                "Uses only plausibly pre-treatment context and is the manuscript's "
                "primary causal specification, chosen on causal-validity grounds "
                "rather than on minimum post-match SMD."
            ),
        },
        {
            "context_group": "Sentinel indices",
            "variables": "NDVI, NDBI, NDWI, MNDWI",
            "causal_role": "ambiguous proxy or mediator",
            "main_model_use": "over-adjustment comparison only",
            "post_treatment_risk": "high",
            "sensitivity_variant": "sentinel_indices",
            "interpretation": (
                "Spectral indices improve environmental context but may partly encode "
                "post-construction land-cover responses, so they are excluded from the "
                "preferred set."
            ),
        },
        {
            "context_group": "Sentinel bands",
            "variables": "Sentinel-2 reflectance bands",
            "causal_role": "ambiguous proxy or mediator",
            "main_model_use": "over-adjustment comparison only",
            "post_treatment_risk": "medium",
            "sensitivity_variant": "sentinel_bands",
            "interpretation": (
                "Raw bands provide surface context with less semantic processing than "
                "indices, but they still may reflect treatment-adjacent surfaces."
            ),
        },
        {
            "context_group": "Full RS context",
            "variables": "coordinates, geometry, terrain, Sentinel bands and indices",
            "causal_role": "over-adjusted mixed set (possible mediators)",
            "main_model_use": "over-adjustment sensitivity comparison",
            "post_treatment_risk": "medium",
            "sensitivity_variant": "full_rs_context",
            "interpretation": (
                "Adds Sentinel surfaces on top of the pre-treatment set. It has the "
                "best post-match balance but conditions on possible mediators, so it "
                "is reported as an over-adjustment comparison, not the preferred design."
            ),
        },
    ]

    rows: list[dict[str, Any]] = []
    for spec in specs:
        record = _variant_row(ablation, spec["sensitivity_variant"])
        rows.append(
            {
                **spec,
                "sensitivity_att_c": _finite_or_none(record.get("att")) if record is not None else None,
                "sensitivity_max_post_smd": (
                    _finite_or_none(record.get("max_post_smd")) if record is not None else None
                ),
                "sensitivity_balance_pass": (
                    str(record.get("balance_pass_0_1")).lower() == "true"
                    if record is not None
                    else None
                ),
            }
        )
    return pd.DataFrame(rows, columns=CHONGQING_VARIABLE_ROLE_COLUMNS)


def render_chongqing_variable_role_report(table: pd.DataFrame) -> str:
    lines = [
        "# Chongqing Context Variable Role Audit",
        "",
        "This table separates context variables by their assumed causal role and by the",
        "observed Chongqing ablation result. It is intended to keep post-treatment",
        "proxy risk explicit in the manuscript.",
        "",
    ]
    if table.empty:
        lines.append("No Chongqing variable-role rows were available.")
        return "\n".join(lines) + "\n"
    lines.extend(
        [
            "| Context group | Causal role | Risk | Variant | ATT (C) | Max post SMD | Balance pass |",
            "|---|---|---|---|---:|---:|---|",
        ]
    )
    for _, record in table.iterrows():
        lines.append(
            "| "
            f"{record['context_group']} | "
            f"{record['causal_role']} | "
            f"{record['post_treatment_risk']} | "
            f"{record['sensitivity_variant']} | "
            f"{_fmt_num(record['sensitivity_att_c'])} | "
            f"{_fmt_num(record['sensitivity_max_post_smd'])} | "
            f"{record['sensitivity_balance_pass']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _audit_row(item: str, value: Any, source_file: str) -> dict[str, str]:
    return {
        "item": item,
        "value": "" if value is None else str(value),
        "source_file": source_file,
        "privacy_status": "non_sensitive_aggregate",
    }


def build_chongqing_reviewer_audit_package(
    results_dir: str | Path = DEFAULT_RESULTS_DIR,
) -> pd.DataFrame:
    """Build a non-sensitive aggregate audit table for reviewer verification."""
    root = Path(results_dir)
    manifest = _read_json(root / "chongqing_uhi_analysis_manifest.json")
    metadata = manifest.get("metadata", {}) if isinstance(manifest.get("metadata"), dict) else {}
    ablation = _read_csv(root / "chongqing_uhi_ablation.csv")
    matched = _read_csv(root / "chongqing_uhi_matched_counts.csv")
    residuals = _read_csv(root / "chongqing_residual_spatial_diagnostics.csv")
    placebo = _read_csv(root / "chongqing_placebo_thresholds.csv")

    rows: list[dict[str, str]] = []
    manifest_file = "chongqing_uhi_analysis_manifest.json"
    for item in (
        "sample_size",
        "buildings_total",
        "treatment_threshold",
        "caliper",
        "n_bootstrap",
        "n_spatial_bootstrap",
        "data_source",
        "balance_interpretation",
    ):
        if item in metadata:
            rows.append(_audit_row(item, metadata.get(item), manifest_file))

    full = _variant_row(ablation, "full_rs_context")
    if full is not None:
        ablation_file = "chongqing_uhi_ablation.csv"
        for item, column in (
            ("full_rs_context_att_c", "att"),
            ("full_rs_context_ci_lower", "ci_lower"),
            ("full_rs_context_ci_upper", "ci_upper"),
            ("full_rs_context_max_pre_smd", "max_pre_smd"),
            ("full_rs_context_max_post_smd", "max_post_smd"),
            ("full_rs_context_balance_pass_0_1", "balance_pass_0_1"),
            ("full_rs_context_matched_treated_n", "matched_treated_n"),
            ("full_rs_context_matched_control_n", "matched_control_n"),
        ):
            rows.append(_audit_row(item, full.get(column), ablation_file))

    full_matched = _variant_row(matched, "full_rs_context")
    if full_matched is not None:
        matched_file = "chongqing_uhi_matched_counts.csv"
        for item, column in (
            ("full_rs_context_n_total", "n_total"),
            ("full_rs_context_common_support_n", "common_support_n"),
            ("full_rs_context_unmatched_treated_n", "unmatched_treated_n"),
            ("full_rs_context_drop_rate", "drop_rate"),
        ):
            rows.append(_audit_row(item, full_matched.get(column), matched_file))

    full_residual = _variant_row(residuals, "full_rs_context")
    if full_residual is not None:
        residual_file = "chongqing_residual_spatial_diagnostics.csv"
        for item, column in (
            ("full_rs_context_residual_moran_i", "moran_i"),
            ("full_rs_context_residual_moran_p_value", "permutation_p_value"),
            ("full_rs_context_residual_moran_n", "n"),
            ("full_rs_context_residual_distance_band", "distance_band"),
        ):
            rows.append(_audit_row(item, full_residual.get(column), residual_file))

    if not placebo.empty and "variant" in placebo and "threshold" in placebo:
        placebo_rows = placebo.loc[placebo["variant"].astype(str) == "full_rs_context"]
        for _, record in placebo_rows.sort_values("threshold").iterrows():
            threshold = record.get("threshold")
            item_prefix = f"full_rs_context_threshold_{threshold}"
            rows.append(_audit_row(f"{item_prefix}_att_c", record.get("att"), "chongqing_placebo_thresholds.csv"))
            rows.append(
                _audit_row(
                    f"{item_prefix}_max_post_smd",
                    record.get("max_post_smd"),
                    "chongqing_placebo_thresholds.csv",
                )
            )

    return pd.DataFrame(rows, columns=CHONGQING_REVIEWER_AUDIT_COLUMNS)


def _core_support_control_row(results_dir: Path) -> dict[str, str] | None:
    """Positive-control row: a clean synthetic case graded core_support.

    Included so the evidence table exercises the core/bounded distinction on an
    evidence row, demonstrating the grade engine is discriminative rather than
    always returning bounded_support.
    """
    payload = _read_json(results_dir / "core_support_positive_control.json")
    if not payload:
        return None
    diag = payload.get("diagnostics", {})
    grade = str(payload.get("evidence_grade", "bounded_support"))
    return _row(
        case="synthetic_core_support_control",
        data_type="controlled positive-control synthetic case",
        exposure="near-randomised binary treatment",
        outcome="continuous outcome with measured confounders only",
        context_source="fully measured confounders; no unmeasured spatial process",
        best_adjustment="adjusted OLS on the correct measured set",
        effect_estimate=(
            f"ATT_hat = {_fmt_num(diag.get('att_hat'))} (true 0.5); "
            f"rel. bias = {_fmt_num(diag.get('rel_bias'))}"
        ),
        balance_status=f"max post-adjust SMD = {_fmt_num(diag.get('max_post_smd'))}",
        robustness_status=(
            f"residual Moran I = {_fmt_num(diag.get('residual_moran_i'))} "
            f"(p = {_fmt_num(diag.get('residual_moran_p_value'))}); "
            f"neighbor-exposure p = {_fmt_num(diag.get('neighbor_exposure_p_value'))}"
        ),
        evidence_grade=grade,
        grade_rule_ids=_joined_text(payload.get("triggered_rules")),
        grade_reasons="No downgrade rules fire on a clean, well-identified design.",
        limitation="Synthetic positive control only; demonstrates grade discrimination, not real-world validity.",
        manuscript_use="Use as the core_support positive control that exercises the grade engine.",
    )


def build_scca_evidence_table(
    results_dir: str | Path = DEFAULT_RESULTS_DIR,
) -> pd.DataFrame:
    """Build the reviewer-facing evidence matrix from existing result artifacts."""
    root = Path(results_dir)
    rows: list[dict[str, str]] = []
    for optional_row in (
        _synthetic_row(root),
        _core_support_control_row(root),
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
        "synthetic_core_support_control": 1,
        "chongqing_uhi": 2,
        "county_social_capital_spatial_notebook": 3,
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
    threshold_table = build_residual_moran_threshold_sensitivity(results_dir)
    variable_role_table = build_chongqing_variable_role_audit(results_dir)
    reviewer_audit_table = build_chongqing_reviewer_audit_package(results_dir)
    synthesis_path = target / OUTPUT_FILES["synthesis_csv"]
    report_path = target / OUTPUT_FILES["report_md"]
    manifest_path = target / OUTPUT_FILES["manifest_json"]
    threshold_sensitivity_path = target / OUTPUT_FILES["threshold_sensitivity_csv"]
    threshold_sensitivity_report_path = target / OUTPUT_FILES["threshold_sensitivity_md"]
    variable_role_path = target / OUTPUT_FILES["chongqing_variable_role_audit_csv"]
    variable_role_report_path = target / OUTPUT_FILES["chongqing_variable_role_audit_md"]
    reviewer_audit_path = target / OUTPUT_FILES["chongqing_reviewer_audit_package_csv"]
    reviewer_audit_json_path = target / OUTPUT_FILES["chongqing_reviewer_audit_package_json"]
    grade_rule_manifest = write_evidence_rule_outputs(target)

    table.to_csv(synthesis_path, index=False)
    threshold_table.to_csv(threshold_sensitivity_path, index=False)
    variable_role_table.to_csv(variable_role_path, index=False)
    reviewer_audit_table.to_csv(reviewer_audit_path, index=False)
    report_path.write_text(render_scca_evidence_report(table), encoding="utf-8")
    threshold_sensitivity_report_path.write_text(
        render_residual_moran_threshold_report(threshold_table),
        encoding="utf-8",
    )
    variable_role_report_path.write_text(
        render_chongqing_variable_role_report(variable_role_table),
        encoding="utf-8",
    )
    reviewer_audit_json_path.write_text(
        json.dumps(
            {"records": reviewer_audit_table.to_dict(orient="records")},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manifest = {
        "synthesis_csv": str(synthesis_path),
        "report_md": str(report_path),
        "manifest_json": str(manifest_path),
        "threshold_sensitivity_csv": str(threshold_sensitivity_path),
        "threshold_sensitivity_md": str(threshold_sensitivity_report_path),
        "chongqing_variable_role_audit_csv": str(variable_role_path),
        "chongqing_variable_role_audit_md": str(variable_role_report_path),
        "chongqing_reviewer_audit_package_csv": str(reviewer_audit_path),
        "chongqing_reviewer_audit_package_json": str(reviewer_audit_json_path),
        "grade_rules_json": grade_rule_manifest["rules_json"],
        "grade_rules_md": grade_rule_manifest["rules_md"],
        "results_dir": str(Path(results_dir)),
        "n_rows": int(len(table)),
        "n_threshold_sensitivity_rows": int(len(threshold_table)),
        "n_chongqing_variable_role_rows": int(len(variable_role_table)),
        "n_chongqing_reviewer_audit_rows": int(len(reviewer_audit_table)),
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
