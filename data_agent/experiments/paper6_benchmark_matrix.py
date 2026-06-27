"""Multi-dataset benchmark matrix for Paper 6 ArcGIS-free/ArcGIS-surpassing work."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results"
DEFAULT_OUTPUT_DIR = DEFAULT_RESULTS_DIR / "paper6_multi_dataset_benchmark_matrix"
OUTPUT_FILES = {
    "matrix_csv": "paper6_multi_dataset_benchmark_matrix.csv",
    "report_md": "paper6_multi_dataset_benchmark_matrix.md",
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
    "arcgis_style_erf_response_mae",
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
    "score_min",
    "score_max",
    "evidence_summary",
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


def _arcgis_county_row(manifest_path: str | Path | None) -> dict[str, Any] | None:
    manifest = _read_json(manifest_path)
    metrics = manifest.get("metrics") if isinstance(manifest, dict) else None
    if not isinstance(metrics, dict) or not metrics:
        return None
    row = _empty_row(
        "county_arcgis_builtin",
        "real_arcgis_benchmark",
        str(manifest_path),
    )
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
            "arcgis_style_erf_response_mae": _finite_float(metrics.get("arcgis_style_erf_response_mae")),
            "evidence_summary": "ArcGIS built-in comparison against GeoCausal Open GIS package.",
            "next_action": "Replicate ArcGIS comparison on additional real datasets.",
        }
    )
    return row


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
        row = _empty_row(f"synthetic_{scenario}", "synthetic_known_truth", str(synthetic_scenario_summary_csv))
        row.update(
            {
                "synthetic_robust_rows": _int_or_none(item.get("n_robust")),
                "synthetic_bounded_rows": _int_or_none(item.get("n_bounded")),
                "synthetic_fragile_rows": fragile,
                "score_min": _finite_float(item.get("min_score")),
                "score_max": _finite_float(item.get("max_score")),
                "evidence_summary": (
                    f"Synthetic known-truth scenario with {fragile} fragile summary rows."
                ),
                "next_action": "Prioritize estimator hardening for fragile synthetic scenarios."
                if fragile > 0
                else "Use as positive-control benchmark for regression testing.",
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
    method_comparison_csv: str | Path | None = None,
    synthetic_scenario_summary_csv: str | Path | None = None,
    epa_benchmark_summary_json: str | Path | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    arcgis_row = _arcgis_county_row(arcgis_comparison_manifest)
    if arcgis_row is not None:
        rows.append(arcgis_row)
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
            f"ArcGIS-style ERF MAE `{row['arcgis_style_erf_response_mae']}`."
        )

    lines.extend(["", "## Matrix", "", matrix.to_markdown(index=False), ""])
    return "\n".join(lines)


def write_paper6_benchmark_matrix(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    arcgis_comparison_manifest: str | Path | None = None,
    method_comparison_csv: str | Path | None = None,
    synthetic_scenario_summary_csv: str | Path | None = None,
    epa_benchmark_summary_json: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    matrix = build_paper6_benchmark_matrix(
        arcgis_comparison_manifest=arcgis_comparison_manifest,
        method_comparison_csv=method_comparison_csv,
        synthetic_scenario_summary_csv=synthetic_scenario_summary_csv,
        epa_benchmark_summary_json=epa_benchmark_summary_json,
    )
    matrix_path = output_dir / OUTPUT_FILES["matrix_csv"]
    report_path = output_dir / OUTPUT_FILES["report_md"]
    manifest_path = output_dir / OUTPUT_FILES["manifest_json"]
    matrix.to_csv(matrix_path, index=False)
    report_path.write_text(_render_report(matrix), encoding="utf-8")
    manifest = {
        "matrix_csv": str(matrix_path),
        "report_md": str(report_path),
        "manifest_json": str(manifest_path),
        "n_rows": int(len(matrix)),
        "case_ids": matrix["case_id"].tolist() if not matrix.empty else [],
        "inputs": {
            "arcgis_comparison_manifest": str(arcgis_comparison_manifest) if arcgis_comparison_manifest else None,
            "method_comparison_csv": str(method_comparison_csv) if method_comparison_csv else None,
            "synthetic_scenario_summary_csv": str(synthetic_scenario_summary_csv)
            if synthetic_scenario_summary_csv
            else None,
            "epa_benchmark_summary_json": str(epa_benchmark_summary_json) if epa_benchmark_summary_json else None,
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Write Paper 6 multi-dataset benchmark matrix.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--arcgis-comparison-manifest")
    parser.add_argument(
        "--method-comparison-csv",
        default=str(DEFAULT_RESULTS_DIR / "scca_method_comparison.csv"),
    )
    parser.add_argument(
        "--synthetic-scenario-summary-csv",
        default=str(DEFAULT_RESULTS_DIR / "synthetic_benchmark_audit" / "scenario_fragility_summary.csv"),
    )
    parser.add_argument("--epa-benchmark-summary-json")
    args = parser.parse_args()
    manifest = write_paper6_benchmark_matrix(
        output_dir=args.output_dir,
        arcgis_comparison_manifest=args.arcgis_comparison_manifest,
        method_comparison_csv=args.method_comparison_csv,
        synthetic_scenario_summary_csv=args.synthetic_scenario_summary_csv,
        epa_benchmark_summary_json=args.epa_benchmark_summary_json,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()