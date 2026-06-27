"""Multi-dataset benchmark matrix for Paper 6 ArcGIS-free/ArcGIS-surpassing work."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results"
DEFAULT_OUTPUT_DIR = DEFAULT_RESULTS_DIR / "paper6_multi_dataset_benchmark_matrix"
OUTPUT_FILES = {
    "matrix_csv": "paper6_multi_dataset_benchmark_matrix.csv",
    "report_md": "paper6_multi_dataset_benchmark_matrix.md",
    "surpass_scorecard_csv": "paper6_arcgis_surpass_scorecard.csv",
    "surpass_scorecard_report_md": "paper6_arcgis_surpass_scorecard.md",
    "manifest_json": "paper6_multi_dataset_benchmark_matrix_manifest.json",
}
MATRIX_COLUMNS = [
    "case_id",
    "data_type",
    "benchmark_source",
    "sample_rows",
    "arcgis_available",
    "arcgis_balance",
    "geocausal_default_balance",
    "geocausal_calibrated_balance",
    "default_erf_response_mae",
    "preferred_erf_response_mae",
    "arcgis_style_erf_response_mae",
    "arcgis_style_calibrated_erf_response_mae",
    "baseline_method",
    "enhanced_method",
    "baseline_effect",
    "enhanced_effect",
    "baseline_grade",
    "enhanced_grade",
    "true_effect",
    "absolute_error",
    "scenario_count",
    "median_absolute_error",
    "mean_absolute_error",
    "max_absolute_error",
    "panel_year_min",
    "panel_year_max",
    "synthetic_robust_rows",
    "synthetic_bounded_rows",
    "synthetic_fragile_rows",
    "synthetic_preferred_variant",
    "synthetic_preferred_fragility",
    "synthetic_preferred_fragile_rows",
    "synthetic_diagnostic_fragile_rows",
    "score_min",
    "score_max",
    "evidence_summary",
    "next_action",
]
SCORECARD_COLUMNS = [
    "criterion_id",
    "category",
    "status",
    "metric_value",
    "arcgis_reference",
    "threshold",
    "evidence_case",
    "interpretation",
    "next_action",
]


def _read_json(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    path = Path(path)
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _read_csv(path: str | Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame()
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame()


def _finite_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if np.isfinite(numeric) else None


def _int_or_none(value: Any) -> int | None:
    numeric = _finite_float(value)
    return int(numeric) if numeric is not None else None


def _empty_row(case_id: str, data_type: str, benchmark_source: str) -> dict[str, Any]:
    row = {column: None for column in MATRIX_COLUMNS}
    row.update(
        {
            "case_id": case_id,
            "data_type": data_type,
            "benchmark_source": benchmark_source,
            "arcgis_available": False,
        }
    )
    return row


def _arcgis_comparison_case_id(manifest_path: str | Path | None, manifest: dict[str, Any]) -> str:
    arcgis_manifest = _read_json(manifest.get("arcgis_manifest_path"))
    parameters = arcgis_manifest.get("parameters") if isinstance(arcgis_manifest, dict) else None
    if isinstance(parameters, dict) and parameters.get("output_stem"):
        return str(parameters["output_stem"])
    path_stem = Path(str(manifest_path)).stem.lower() if manifest_path is not None else "arcgis_comparison"
    if path_stem in {"arcgis_comparison_manifest", "arcgis_geocausal_comparison_manifest"}:
        return "county_arcgis_builtin"
    return path_stem.replace("_comparison_manifest", "").replace("arcgis_geocausal_comparison", "arcgis_builtin")


def _arcgis_balance_threshold(manifest: dict[str, Any]) -> float | None:
    arcgis_manifest = _read_json(manifest.get("arcgis_manifest_path"))
    parameters = arcgis_manifest.get("parameters") if isinstance(arcgis_manifest, dict) else None
    if not isinstance(parameters, dict):
        return None
    return _finite_float(parameters.get("balance_threshold"))


def _arcgis_comparison_row(manifest_path: str | Path | None) -> dict[str, Any] | None:
    manifest = _read_json(manifest_path)
    metrics = manifest.get("metrics") if isinstance(manifest, dict) else None
    if not isinstance(metrics, dict) or not metrics:
        return None
    balance_threshold = _arcgis_balance_threshold(manifest)
    evidence_summary = "ArcGIS built-in comparison against GeoCausal Open GIS package."
    if balance_threshold is not None and abs(balance_threshold - 0.1) > 1e-12:
        evidence_summary = (
            "ArcGIS built-in comparison against GeoCausal Open GIS package "
            f"with balance_threshold={balance_threshold}."
        )
    row = _empty_row(
        _arcgis_comparison_case_id(manifest_path, manifest),
        "real_arcgis_benchmark",
        str(manifest_path),
    )
    preferred_erf_response_mae = _finite_float(metrics.get("preferred_erf_response_mae"))
    if preferred_erf_response_mae is None:
        preferred_erf_response_mae = _finite_float(metrics.get("arcgis_style_erf_response_mae"))
    row.update(
        {
            "sample_rows": _int_or_none(metrics.get("geocausal_joined_rows") or metrics.get("arcgis_final_n")),
            "arcgis_available": True,
            "arcgis_balance": _finite_float(metrics.get("arcgis_mean_weighted_correlation")),
            "geocausal_default_balance": _finite_float(
                metrics.get("geocausal_confounder_mean_abs_weighted_correlation")
            ),
            "geocausal_calibrated_balance": _finite_float(
                metrics.get("geocausal_arcgis_style_calibrated_confounder_mean_abs_weighted_correlation")
            ),
            "default_erf_response_mae": _finite_float(metrics.get("erf_response_mae")),
            "preferred_erf_response_mae": preferred_erf_response_mae,
            "arcgis_style_erf_response_mae": _finite_float(metrics.get("arcgis_style_erf_response_mae")),
            "arcgis_style_calibrated_erf_response_mae": _finite_float(
                metrics.get("arcgis_style_calibrated_erf_response_mae")
            ),
            "evidence_summary": evidence_summary,
            "next_action": "Replicate ArcGIS comparison on additional real datasets.",
        }
    )
    return row


def _arcgis_comparison_rows(
    arcgis_comparison_manifest: str | Path | None,
    arcgis_comparison_manifests: Sequence[str | Path] | None,
) -> list[dict[str, Any]]:
    paths: list[str | Path] = []
    if arcgis_comparison_manifest is not None:
        paths.append(arcgis_comparison_manifest)
    if arcgis_comparison_manifests is not None:
        paths.extend(path for path in arcgis_comparison_manifests if path is not None)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        row = _arcgis_comparison_row(path)
        if row is None or row["case_id"] in seen:
            continue
        rows.append(row)
        seen.add(str(row["case_id"]))
    return rows


def _method_rows(method_comparison_csv: str | Path | None) -> list[dict[str, Any]]:
    frame = _read_csv(method_comparison_csv)
    if frame.empty:
        return []
    rows: list[dict[str, Any]] = []
    for _, item in frame.iterrows():
        case_id = str(item.get("case") or item.get("comparison_id") or "unknown_real_case")
        row = _empty_row(case_id, "real_scca_case", str(method_comparison_csv))
        baseline_grade = item.get("baseline_grade")
        enhanced_grade = item.get("enhanced_grade")
        row.update(
            {
                "baseline_method": item.get("baseline_method"),
                "enhanced_method": item.get("enhanced_method"),
                "baseline_effect": _finite_float(item.get("baseline_effect")),
                "enhanced_effect": _finite_float(item.get("enhanced_effect")),
                "baseline_grade": baseline_grade,
                "enhanced_grade": enhanced_grade,
                "evidence_summary": f"SCCA method comparison: {baseline_grade} -> {enhanced_grade}.",
                "next_action": "Use as real-data external validity row; add ArcGIS comparison if ArcPy inputs are available.",
            }
        )
        rows.append(row)
    return rows


def _synthetic_rows(synthetic_scenario_summary_csv: str | Path | None) -> list[dict[str, Any]]:
    frame = _read_csv(synthetic_scenario_summary_csv)
    if frame.empty:
        return []
    rows: list[dict[str, Any]] = []
    for _, item in frame.iterrows():
        scenario = str(item.get("scenario") or "unknown")
        fragile = _int_or_none(item.get("n_fragile")) or 0
        preferred_fragile = _int_or_none(item.get("preferred_fragile_rows"))
        if preferred_fragile is None:
            preferred_fragile = fragile
        diagnostic_fragile = _int_or_none(item.get("diagnostic_fragile_rows"))
        if diagnostic_fragile is None:
            diagnostic_fragile = max(fragile - preferred_fragile, 0)
        preferred_variant_raw = item.get("preferred_variant")
        preferred_variant = None if pd.isna(preferred_variant_raw) else preferred_variant_raw
        preferred_fragility_raw = item.get("preferred_fragility")
        preferred_fragility = None if pd.isna(preferred_fragility_raw) else preferred_fragility_raw
        row = _empty_row(f"synthetic_{scenario}", "synthetic_known_truth", str(synthetic_scenario_summary_csv))
        if preferred_variant:
            evidence_summary = (
                f"Synthetic known-truth scenario with {fragile} raw fragile diagnostic rows; "
                f"preferred variant {preferred_variant} has {preferred_fragile} fragile rows."
            )
        else:
            evidence_summary = (
                f"Synthetic known-truth scenario with {fragile} fragile summary rows."
            )
        row.update(
            {
                "synthetic_robust_rows": _int_or_none(item.get("n_robust")),
                "synthetic_bounded_rows": _int_or_none(item.get("n_bounded")),
                "synthetic_fragile_rows": fragile,
                "synthetic_preferred_variant": preferred_variant,
                "synthetic_preferred_fragility": preferred_fragility,
                "synthetic_preferred_fragile_rows": preferred_fragile,
                "synthetic_diagnostic_fragile_rows": diagnostic_fragile,
                "score_min": _finite_float(item.get("min_score")),
                "score_max": _finite_float(item.get("max_score")),
                "evidence_summary": evidence_summary,
                "next_action": "Prioritize estimator hardening for fragile preferred synthetic scenarios."
                if preferred_fragile > 0
                else "Use as positive-control benchmark; retain diagnostic variants for regression testing.",
            }
        )
        rows.append(row)
    return rows

def _contains_fragile_rule(metric: dict[str, Any]) -> bool:
    rules = metric.get("grade_rule_ids")
    if isinstance(rules, str):
        return "fragile" in rules.lower()
    if isinstance(rules, list):
        return any("fragile" in str(rule).lower() for rule in rules)
    return "fragile" in str(metric.get("evidence_grade", "")).lower()


def _count_scenario_grades(metrics: list[Any], grade: str) -> int:
    return sum(
        1
        for metric in metrics
        if isinstance(metric, dict) and str(metric.get("evidence_grade", "")).lower() == grade
    )


def _epa_policy_structure_row(epa_benchmark_summary_json: str | Path | None) -> dict[str, Any] | None:
    manifest = _read_json(epa_benchmark_summary_json)
    if not manifest:
        return None
    primary = manifest.get("policy_structure_semisynthetic") or manifest.get("real_data")
    semi_synthetic = manifest.get("semi_synthetic") if isinstance(manifest.get("semi_synthetic"), dict) else {}
    if not isinstance(primary, dict) or not primary:
        return None
    scca_manifest = manifest.get("scca_manifest") if isinstance(manifest.get("scca_manifest"), dict) else {}
    case_id = str(scca_manifest.get("case_name") or "epa_nonattainment_airdata")
    scenario_metrics = semi_synthetic.get("scenario_metrics")
    scenario_metrics = scenario_metrics if isinstance(scenario_metrics, list) else []
    scenario_count = _int_or_none(semi_synthetic.get("scenario_count")) or len(scenario_metrics) or None
    fragile_count = sum(1 for metric in scenario_metrics if isinstance(metric, dict) and _contains_fragile_rule(metric))
    row = _empty_row(case_id, "semi_synthetic_policy_structure", str(epa_benchmark_summary_json))
    row.update(
        {
            "sample_rows": _int_or_none(primary.get("row_count")),
            "baseline_method": "known true effect",
            "enhanced_method": "GeoCausal SCCA policy-structure semi-synthetic",
            "baseline_effect": _finite_float(primary.get("true_effect")),
            "enhanced_effect": _finite_float(primary.get("effect_estimate")),
            "baseline_grade": "known_truth",
            "enhanced_grade": primary.get("evidence_grade"),
            "true_effect": _finite_float(primary.get("true_effect")),
            "absolute_error": _finite_float(primary.get("absolute_error")),
            "scenario_count": scenario_count,
            "median_absolute_error": _finite_float(semi_synthetic.get("median_absolute_error")),
            "mean_absolute_error": _finite_float(semi_synthetic.get("mean_absolute_error")),
            "max_absolute_error": _finite_float(semi_synthetic.get("max_absolute_error")),
            "panel_year_min": _int_or_none(primary.get("panel_year_min")),
            "panel_year_max": _int_or_none(primary.get("panel_year_max")),
            "synthetic_robust_rows": _count_scenario_grades(scenario_metrics, "core_support"),
            "synthetic_bounded_rows": _count_scenario_grades(scenario_metrics, "bounded_support"),
            "synthetic_fragile_rows": fragile_count,
            "evidence_summary": "Semi-synthetic known-effect benchmark on real EPA policy geography.",
            "next_action": (
                "Replace the deterministic pollution outcome with direct AQS AirData observational estimates "
                "when downloads are stable."
            ),
        }
    )
    return row


def build_paper6_benchmark_matrix(
    *,
    arcgis_comparison_manifest: str | Path | None = None,
    arcgis_comparison_manifests: Sequence[str | Path] | None = None,
    method_comparison_csv: str | Path | None = None,
    synthetic_scenario_summary_csv: str | Path | None = None,
    epa_benchmark_summary_json: str | Path | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    rows.extend(_arcgis_comparison_rows(arcgis_comparison_manifest, arcgis_comparison_manifests))
    rows.extend(_method_rows(method_comparison_csv))
    rows.extend(_synthetic_rows(synthetic_scenario_summary_csv))
    epa_row = _epa_policy_structure_row(epa_benchmark_summary_json)
    if epa_row is not None:
        rows.append(epa_row)
    matrix = pd.DataFrame(rows, columns=MATRIX_COLUMNS)
    if matrix.empty:
        return matrix
    matrix["arcgis_available"] = matrix["arcgis_available"].astype(object)
    return matrix


def _scorecard_row(
    *,
    criterion_id: str,
    category: str,
    status: str,
    metric_value: float | int | None = None,
    arcgis_reference: float | int | None = None,
    threshold: str | float | int | None = None,
    evidence_case: str | None = None,
    interpretation: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "criterion_id": criterion_id,
        "category": category,
        "status": status,
        "metric_value": metric_value,
        "arcgis_reference": arcgis_reference,
        "threshold": threshold,
        "evidence_case": evidence_case,
        "interpretation": interpretation,
        "next_action": next_action,
    }


def _row_float(row: pd.Series | None, column: str) -> float | None:
    if row is None:
        return None
    return _finite_float(row.get(column))


def _case_row(matrix: pd.DataFrame, case_id: str) -> pd.Series | None:
    if matrix.empty or "case_id" not in matrix.columns:
        return None
    rows = matrix.loc[matrix["case_id"] == case_id]
    return None if rows.empty else rows.iloc[0]


def _overall_blocker_next_action(blocking: list[dict[str, Any]]) -> str:
    blocker_ids = {str(row.get("criterion_id")) for row in blocking}
    actions: list[str] = []
    if "synthetic_fragility" in blocker_ids:
        actions.append("Close remaining synthetic robustness gaps.")
    if "direct_arcgis_real_dataset_coverage" in blocker_ids:
        actions.append("Add additional real ArcGIS comparisons before broad superiority claims.")
    if "epa_known_truth_recovery" in blocker_ids:
        actions.append("Restore EPA known-truth recovery evidence.")
    if "arcgis_runtime_reproducibility" in blocker_ids:
        actions.append("Restore ArcGIS runtime reproducibility evidence.")
    direct_metric_blockers = blocker_ids.intersection(
        {
            "county_calibrated_balance",
            "county_preferred_erf",
            "county_arcgis_style_erf",
        }
    )
    if direct_metric_blockers:
        actions.append("Close remaining direct ArcGIS metric gaps.")
    if not actions:
        actions.append("Close remaining scorecard blockers before a broad superiority claim.")
    return " ".join(actions)

def build_arcgis_surpass_scorecard(
    matrix: pd.DataFrame,
    *,
    required_arcgis_real_rows: int = 3,
    arcgis_style_erf_near_parity_mae: float = 0.05,
    default_erf_gap_mae: float = 0.25,
    known_truth_absolute_error_tolerance: float = 1e-6,
    arcgis_runtime_audit: dict[str, Any] | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    county = _case_row(matrix, "county_arcgis_builtin")
    arcgis_balance = _row_float(county, "arcgis_balance")
    calibrated_balance = _row_float(county, "geocausal_calibrated_balance")
    balance_status = (
        "surpasses_arcgis"
        if calibrated_balance is not None and arcgis_balance is not None and calibrated_balance < arcgis_balance
        else "missing_evidence"
        if calibrated_balance is None or arcgis_balance is None
        else "open_gap"
    )
    rows.append(
        _scorecard_row(
            criterion_id="county_calibrated_balance",
            category="direct_arcgis_metric",
            status=balance_status,
            metric_value=calibrated_balance,
            arcgis_reference=arcgis_balance,
            threshold="lower than ArcGIS weighted correlation",
            evidence_case="county_arcgis_builtin",
            interpretation="GeoCausal calibrated ArcGIS-style weights beat the ArcGIS balance score on the county benchmark."
            if balance_status == "surpasses_arcgis"
            else "GeoCausal calibrated balance has not beaten the ArcGIS balance reference.",
            next_action="Replicate the calibrated-balance win on additional real ArcGIS comparisons.",
        )
    )

    preferred_erf = _row_float(county, "preferred_erf_response_mae")
    preferred_erf_status = (
        "near_parity"
        if preferred_erf is not None and preferred_erf <= arcgis_style_erf_near_parity_mae
        else "missing_evidence"
        if preferred_erf is None
        else "open_gap"
    )
    rows.append(
        _scorecard_row(
            criterion_id="county_preferred_erf",
            category="direct_arcgis_metric",
            status=preferred_erf_status,
            metric_value=preferred_erf,
            threshold=f"MAE <= {arcgis_style_erf_near_parity_mae}",
            evidence_case="county_arcgis_builtin",
            interpretation="Preferred Open GIS ERF closely reproduces the ArcGIS ERF curve."
            if preferred_erf_status == "near_parity"
            else "Preferred Open GIS ERF is not yet close enough to the ArcGIS reference.",
            next_action="Keep the preferred ERF as the user-facing ArcGIS-compatible curve and test it on more real datasets.",
        )
    )

    arcgis_style_erf = _row_float(county, "arcgis_style_erf_response_mae")
    erf_status = (
        "near_parity"
        if arcgis_style_erf is not None and arcgis_style_erf <= arcgis_style_erf_near_parity_mae
        else "missing_evidence"
        if arcgis_style_erf is None
        else "open_gap"
    )
    rows.append(
        _scorecard_row(
            criterion_id="county_arcgis_style_erf",
            category="direct_arcgis_metric",
            status=erf_status,
            metric_value=arcgis_style_erf,
            threshold=f"MAE <= {arcgis_style_erf_near_parity_mae}",
            evidence_case="county_arcgis_builtin",
            interpretation="ArcGIS-style open ERF closely reproduces the ArcGIS ERF curve."
            if erf_status == "near_parity"
            else "ArcGIS-style ERF is not yet close enough to the ArcGIS reference.",
            next_action="Keep this as parity benchmark output while improving the default GeoCausal ERF.",
        )
    )

    calibrated_arcgis_style_erf = _row_float(county, "arcgis_style_calibrated_erf_response_mae")
    calibrated_erf_status = (
        "near_parity"
        if calibrated_arcgis_style_erf is not None
        and calibrated_arcgis_style_erf <= arcgis_style_erf_near_parity_mae
        else "missing_evidence"
        if calibrated_arcgis_style_erf is None
        else "diagnostic_gap"
    )
    rows.append(
        _scorecard_row(
            criterion_id="county_arcgis_style_calibrated_erf",
            category="direct_arcgis_metric",
            status=calibrated_erf_status,
            metric_value=calibrated_arcgis_style_erf,
            threshold=f"MAE <= {arcgis_style_erf_near_parity_mae}",
            evidence_case="county_arcgis_builtin",
            interpretation="Calibrated ArcGIS-style open ERF closely reproduces the ArcGIS ERF curve."
            if calibrated_erf_status == "near_parity"
            else "Calibrated ArcGIS-style ERF is retained as a diagnostic curve and is not the preferred user-facing ERF.",
            next_action="Keep calibrated weights for balance gains, but do not promote calibrated ERF unless real ArcGIS parity improves.",
        )
    )


    default_erf = _row_float(county, "default_erf_response_mae")
    default_erf_status = (
        "diagnostic_gap"
        if default_erf is not None and default_erf > default_erf_gap_mae
        else "missing_evidence"
        if default_erf is None
        else "acceptable"
    )
    rows.append(
        _scorecard_row(
            criterion_id="county_default_erf_gap",
            category="direct_arcgis_metric",
            status=default_erf_status,
            metric_value=default_erf,
            threshold=f"MAE <= {default_erf_gap_mae}",
            evidence_case="county_arcgis_builtin",
            interpretation="Legacy default GeoCausal ERF is numerically far from the ArcGIS ERF reference, so preferred ERF is used for Open GIS workflows."
            if default_erf_status == "diagnostic_gap"
            else "Default GeoCausal ERF is within the configured ArcGIS-reference gap threshold.",
            next_action="Keep this row as a legacy diagnostic while improving the preferred ERF across datasets.",
        )
    )

    arcgis_rows = 0
    direct_arcgis = pd.DataFrame()
    if not matrix.empty and "arcgis_available" in matrix.columns:
        direct_arcgis = matrix.loc[matrix["arcgis_available"] == True].copy()  # noqa: E712
        arcgis_rows = int(len(direct_arcgis))
    coverage_status = "sufficient_evidence" if arcgis_rows >= required_arcgis_real_rows else "insufficient_evidence"
    rows.append(
        _scorecard_row(
            criterion_id="direct_arcgis_real_dataset_coverage",
            category="evidence_coverage",
            status=coverage_status,
            metric_value=arcgis_rows,
            threshold=required_arcgis_real_rows,
            evidence_case="all_arcgis_available_rows",
            interpretation="Direct ArcGIS comparisons cover enough real datasets for a stronger claim."
            if coverage_status == "sufficient_evidence"
            else "Only a small number of real datasets have direct ArcGIS built-in comparisons.",
            next_action="Add additional real ArcGIS comparisons before claiming broad superiority.",
        )
    )

    balance_win_count = 0
    balance_total = 0
    if not direct_arcgis.empty:
        arcgis_balance_values = pd.to_numeric(direct_arcgis["arcgis_balance"], errors="coerce")
        calibrated_values = pd.to_numeric(direct_arcgis["geocausal_calibrated_balance"], errors="coerce")
        valid = pd.DataFrame({"arcgis": arcgis_balance_values, "geocausal": calibrated_values}).dropna()
        balance_total = int(len(valid))
        balance_win_count = int((valid["geocausal"] < valid["arcgis"]).sum())
    balance_win_status = (
        "surpasses_arcgis"
        if balance_total > 0 and balance_win_count == balance_total
        else "missing_evidence"
        if balance_total == 0
        else "open_gap"
    )
    rows.append(
        _scorecard_row(
            criterion_id="direct_arcgis_calibrated_balance_wins",
            category="direct_arcgis_metric",
            status=balance_win_status,
            metric_value=balance_win_count,
            arcgis_reference=balance_total,
            threshold="GeoCausal calibrated balance lower on every direct ArcGIS row",
            evidence_case="all_arcgis_available_rows",
            interpretation="GeoCausal calibrated balance beats ArcGIS on every direct ArcGIS comparison row."
            if balance_win_status == "surpasses_arcgis"
            else "GeoCausal calibrated balance does not yet beat ArcGIS on every direct comparison row.",
            next_action="Keep adding real ArcGIS comparisons and preserve the calibrated-balance win rate.",
        )
    )

    if arcgis_runtime_audit:
        runtime_available = bool(arcgis_runtime_audit.get("runtime_available"))
        runtime_rows = _int_or_none(arcgis_runtime_audit.get("n_direct_comparison_manifests")) or 0
        runtime_wins = _int_or_none(arcgis_runtime_audit.get("n_calibrated_balance_wins")) or 0
        runtime_status = (
            "passes_runtime_audit"
            if runtime_available and runtime_rows >= required_arcgis_real_rows and runtime_wins == runtime_rows
            else "open_gap"
        )
        arcgis_version = arcgis_runtime_audit.get("arcgis_version") or "unknown"
        product = arcgis_runtime_audit.get("product") or "unknown"
        rows.append(
            _scorecard_row(
                criterion_id="arcgis_runtime_reproducibility",
                category="runtime_reproducibility",
                status=runtime_status,
                metric_value=runtime_rows,
                arcgis_reference=runtime_wins,
                threshold=(
                    f"ArcGIS runtime available and >= {required_arcgis_real_rows} "
                    "direct manifests with calibrated-balance wins"
                ),
                evidence_case="arcgis_runtime_audit",
                interpretation=(
                    f"ArcGIS Pro {arcgis_version} ({product}) runtime audit verified "
                    f"{runtime_rows} direct comparison manifests and {runtime_wins} calibrated-balance wins."
                )
                if runtime_status == "passes_runtime_audit"
                else "ArcGIS runtime audit is missing required runtime availability, direct manifests, or balance wins.",
                next_action="Refresh this audit whenever ArcGIS Pro, ArcPy, or benchmark manifests change.",
            )
        )
    synthetic_fragile = 0
    synthetic_raw_fragile = 0
    if not matrix.empty and {"data_type", "synthetic_fragile_rows"}.issubset(matrix.columns):
        synthetic_matrix = matrix.loc[matrix["data_type"] == "synthetic_known_truth"].copy()
        synthetic_raw_fragile = int(
            pd.to_numeric(synthetic_matrix["synthetic_fragile_rows"], errors="coerce").fillna(0).sum()
        )
        if "synthetic_preferred_fragile_rows" in synthetic_matrix.columns:
            preferred_values = pd.to_numeric(
                synthetic_matrix["synthetic_preferred_fragile_rows"], errors="coerce"
            )
            raw_values = pd.to_numeric(synthetic_matrix["synthetic_fragile_rows"], errors="coerce")
            synthetic_fragile = int(preferred_values.fillna(raw_values).fillna(0).sum())
        else:
            synthetic_fragile = synthetic_raw_fragile
    synthetic_status = "open_gap" if synthetic_fragile > 0 else "passes_known_truth"
    rows.append(
        _scorecard_row(
            criterion_id="synthetic_fragility",
            category="known_truth_robustness",
            status=synthetic_status,
            metric_value=synthetic_fragile,
            arcgis_reference=synthetic_raw_fragile,
            threshold="preferred fragile rows = 0",
            evidence_case="synthetic_known_truth_rows",
            interpretation="Synthetic known-truth audit still contains fragile preferred/champion method rows."
            if synthetic_status == "open_gap"
            else "Synthetic known-truth preferred/champion rows have no fragile failures; raw fragile variants remain diagnostic.",
            next_action="Prioritize fragile preferred synthetic scenarios before claiming robust algorithmic superiority."
            if synthetic_status == "open_gap"
            else "Keep diagnostic fragile variants visible while expanding known-truth stress tests.",
        )
    )
    epa = _case_row(matrix, "epa_nonattainment_airdata")
    epa_error = _row_float(epa, "absolute_error")
    epa_status = (
        "passes_known_truth"
        if epa_error is not None and epa_error <= known_truth_absolute_error_tolerance
        else "missing_evidence"
        if epa_error is None
        else "open_gap"
    )
    rows.append(
        _scorecard_row(
            criterion_id="epa_known_truth_recovery",
            category="policy_structure_known_truth",
            status=epa_status,
            metric_value=epa_error,
            threshold=known_truth_absolute_error_tolerance,
            evidence_case="epa_nonattainment_airdata",
            interpretation="GeoCausal recovers the known EPA policy-structure semi-synthetic effect within tolerance."
            if epa_status == "passes_known_truth"
            else "EPA policy-structure known-effect recovery is not within tolerance or is unavailable.",
            next_action="Replace the deterministic outcome with direct AQS AirData observational estimates when available.",
        )
    )

    blocking_statuses = {"open_gap", "insufficient_evidence", "missing_evidence"}
    blocking = [row for row in rows if row["status"] in blocking_statuses]
    overall_status = "not_yet_claimable" if blocking else "claimable_with_current_evidence"
    rows.append(
        _scorecard_row(
            criterion_id="overall_arcgis_surpass_readiness",
            category="overall_gate",
            status=overall_status,
            metric_value=len(blocking),
            threshold=0,
            evidence_case="all_scorecard_rows",
            interpretation="Evidence supports partial wins, but not a broad ArcGIS-superiority claim yet."
            if blocking
            else "No configured scorecard gates block a current ArcGIS-superiority claim.",
            next_action=_overall_blocker_next_action(blocking)
            if blocking
            else "Maintain the gate as new datasets and metrics are added.",
        )
    )
    return pd.DataFrame(rows, columns=SCORECARD_COLUMNS)

def _render_surpass_scorecard_report(scorecard: pd.DataFrame) -> str:
    lines = [
        "# Paper 6 ArcGIS Surpass Scorecard",
        "",
        "This scorecard converts the benchmark matrix into explicit gates for judging ArcGIS replacement and superiority claims.",
        "",
    ]
    if scorecard.empty:
        lines.append("No scorecard rows were available.")
        return "\n".join(lines) + "\n"

    overall_rows = scorecard.loc[scorecard["criterion_id"] == "overall_arcgis_surpass_readiness"]
    overall_status = "unknown" if overall_rows.empty else str(overall_rows.iloc[0]["status"])
    blocking = scorecard[scorecard["status"].isin(["open_gap", "insufficient_evidence", "missing_evidence"])]
    lines.extend(
        [
            f"- Overall status: `{overall_status}`",
            f"- Blocking gates: `{len(blocking)}`",
            f"- Surpassing gates: `{int((scorecard['status'] == 'surpasses_arcgis').sum())}`",
            f"- Near-parity gates: `{int((scorecard['status'] == 'near_parity').sum())}`",
            f"- Known-truth passes: `{int((scorecard['status'] == 'passes_known_truth').sum())}`",
            "",
            "## Blocking Gates",
            "",
        ]
    )
    if blocking.empty:
        lines.append("- No blocking gates under the current configured scorecard.")
    else:
        for _, row in blocking.iterrows():
            lines.append(f"- `{row['criterion_id']}`: `{row['status']}` - {row['next_action']}")
    lines.extend(["", "## Scorecard", "", scorecard.to_markdown(index=False), ""])
    return "\n".join(lines)

def _render_report(matrix: pd.DataFrame) -> str:
    lines = [
        "# Paper 6 Multi-Dataset Benchmark Matrix",
        "",
        "This report inventories real and synthetic datasets available for judging whether GeoCausal can replace or exceed ArcGIS.",
        "",
    ]
    if matrix.empty:
        lines.append("No benchmark rows were available.")
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            f"- Benchmark rows: `{len(matrix)}`",
            f"- Real rows: `{int((matrix['data_type'].astype(str).str.startswith('real')).sum())}`",
            f"- Synthetic rows: `{int((matrix['data_type'] == 'synthetic_known_truth').sum())}`",
            f"- Policy-structure semi-synthetic rows: `{int((matrix['data_type'] == 'semi_synthetic_policy_structure').sum())}`",
            "",
            "## ArcGIS Parity Rows",
            "",
        ]
    )
    arcgis_rows = matrix[matrix["arcgis_available"] == True]  # noqa: E712
    if arcgis_rows.empty:
        lines.append("- No ArcGIS comparison rows were available.")
    for _, row in arcgis_rows.iterrows():
        lines.append(
            f"- `{row['case_id']}`: ArcGIS balance `{row['arcgis_balance']}`, "
            f"GeoCausal calibrated balance `{row['geocausal_calibrated_balance']}`, "
            f"preferred ERF MAE `{row['preferred_erf_response_mae']}`, "
            f"ArcGIS-style ERF MAE `{row['arcgis_style_erf_response_mae']}`, "
            f"calibrated ArcGIS-style ERF MAE `{row['arcgis_style_calibrated_erf_response_mae']}`."
        )

    lines.extend(["", "## Matrix", "", matrix.to_markdown(index=False), ""])
    return "\n".join(lines)


def write_paper6_benchmark_matrix(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    arcgis_comparison_manifest: str | Path | None = None,
    arcgis_comparison_manifests: Sequence[str | Path] | None = None,
    method_comparison_csv: str | Path | None = None,
    synthetic_scenario_summary_csv: str | Path | None = None,
    epa_benchmark_summary_json: str | Path | None = None,
    arcgis_runtime_audit_json: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    matrix = build_paper6_benchmark_matrix(
        arcgis_comparison_manifest=arcgis_comparison_manifest,
        arcgis_comparison_manifests=arcgis_comparison_manifests,
        method_comparison_csv=method_comparison_csv,
        synthetic_scenario_summary_csv=synthetic_scenario_summary_csv,
        epa_benchmark_summary_json=epa_benchmark_summary_json,
    )
    matrix_path = output_dir / OUTPUT_FILES["matrix_csv"]
    report_path = output_dir / OUTPUT_FILES["report_md"]
    scorecard_path = output_dir / OUTPUT_FILES["surpass_scorecard_csv"]
    scorecard_report_path = output_dir / OUTPUT_FILES["surpass_scorecard_report_md"]
    manifest_path = output_dir / OUTPUT_FILES["manifest_json"]
    arcgis_runtime_audit = _read_json(arcgis_runtime_audit_json)
    scorecard = build_arcgis_surpass_scorecard(
        matrix,
        arcgis_runtime_audit=arcgis_runtime_audit if arcgis_runtime_audit else None,
    )
    matrix.to_csv(matrix_path, index=False)
    report_path.write_text(_render_report(matrix), encoding="utf-8")
    scorecard.to_csv(scorecard_path, index=False)
    scorecard_report_path.write_text(_render_surpass_scorecard_report(scorecard), encoding="utf-8")
    manifest = {
        "matrix_csv": str(matrix_path),
        "report_md": str(report_path),
        "manifest_json": str(manifest_path),
        "surpass_scorecard_csv": str(scorecard_path),
        "surpass_scorecard_report_md": str(scorecard_report_path),
        "n_rows": int(len(matrix)),
        "scorecard_rows": int(len(scorecard)),
        "case_ids": matrix["case_id"].tolist() if not matrix.empty else [],
        "surpass_scorecard_status": (
            None
            if scorecard.empty
            else str(
                scorecard.loc[
                    scorecard["criterion_id"] == "overall_arcgis_surpass_readiness", "status"
                ].iloc[0]
            )
        ),
        "inputs": {
            "arcgis_comparison_manifest": str(arcgis_comparison_manifest) if arcgis_comparison_manifest else None,
            "arcgis_comparison_manifests": [str(path) for path in arcgis_comparison_manifests]
            if arcgis_comparison_manifests
            else None,
            "method_comparison_csv": str(method_comparison_csv) if method_comparison_csv else None,
            "synthetic_scenario_summary_csv": str(synthetic_scenario_summary_csv)
            if synthetic_scenario_summary_csv
            else None,
            "epa_benchmark_summary_json": str(epa_benchmark_summary_json) if epa_benchmark_summary_json else None,
            "arcgis_runtime_audit_json": str(arcgis_runtime_audit_json) if arcgis_runtime_audit_json else None,
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Write Paper 6 multi-dataset benchmark matrix.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--arcgis-comparison-manifest", action="append")
    parser.add_argument(
        "--method-comparison-csv",
        default=str(DEFAULT_RESULTS_DIR / "scca_method_comparison.csv"),
    )
    parser.add_argument(
        "--synthetic-scenario-summary-csv",
        default=str(DEFAULT_RESULTS_DIR / "synthetic_benchmark_audit" / "scenario_fragility_summary.csv"),
    )
    parser.add_argument("--epa-benchmark-summary-json")
    parser.add_argument("--arcgis-runtime-audit-json")
    args = parser.parse_args()
    manifest = write_paper6_benchmark_matrix(
        output_dir=args.output_dir,
        arcgis_comparison_manifests=args.arcgis_comparison_manifest,
        method_comparison_csv=args.method_comparison_csv,
        synthetic_scenario_summary_csv=args.synthetic_scenario_summary_csv,
        epa_benchmark_summary_json=args.epa_benchmark_summary_json,
        arcgis_runtime_audit_json=args.arcgis_runtime_audit_json,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
