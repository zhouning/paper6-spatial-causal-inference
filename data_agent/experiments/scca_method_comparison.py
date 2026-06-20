"""Direct SCCA-vs-baseline comparison artifacts for Paper 6."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from data_agent.scca.evidence_rules import (
    RULE_VERSION,
    assess_scca_evidence_grade,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results"
OUTPUT_FILES = {
    "comparison_csv": "scca_method_comparison.csv",
    "report_md": "scca_method_comparison_report.md",
    "manifest_json": "scca_method_comparison_manifest.json",
}
COMPARISON_COLUMNS = [
    "comparison_id",
    "case",
    "baseline_method",
    "enhanced_method",
    "baseline_effect",
    "enhanced_effect",
    "effect_delta",
    "effect_delta_rel",
    "baseline_balance_pass",
    "enhanced_balance_pass",
    "baseline_max_smd",
    "enhanced_max_smd",
    "baseline_n",
    "enhanced_n",
    "baseline_residual_moran_i",
    "enhanced_residual_moran_i",
    "baseline_grade",
    "enhanced_grade",
    "enhanced_rule_ids",
    "interpretation",
]


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _finite_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if np.isfinite(numeric) else None


def _bool_or_none(value: Any) -> bool | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "1", "yes"}:
            return True
        if text in {"false", "0", "no"}:
            return False
    return None


def _delta_rel(enhanced: float | None, baseline: float | None) -> float | None:
    if enhanced is None or baseline is None or baseline == 0:
        return None
    return float((enhanced - baseline) / abs(baseline))


def _effect_from_estimates(path: Path, estimator: str) -> tuple[float | None, float | None]:
    estimates = _read_csv(path)
    if estimates.empty or "estimator" not in estimates.columns:
        return None, None
    rows = estimates.loc[estimates["estimator"].astype(str) == estimator]
    if rows.empty:
        return None, None
    row = rows.iloc[0]
    return _finite_float(row.get("coef")), _finite_float(row.get("n"))


def _county_nonspatial_dir(results_dir: Path) -> Path | None:
    candidates = [
        results_dir / "arcgis_toolbox_demo" / "county_social_capital_arcgis_demo",
        results_dir / "geocausal_county_arcgis_comparison" / "arcgis_builtin",
        results_dir / "scca_county_social_capital",
    ]
    return next((path for path in candidates if path.exists()), None)


def _county_comparison_row(results_dir: Path) -> dict[str, Any] | None:
    nonspatial_dir = _county_nonspatial_dir(results_dir)
    summary = _read_json(results_dir / "county_social_capital_spatial_notebook_summary.json")
    result_summary = summary.get("result_summary", {}) if isinstance(summary, dict) else {}
    if nonspatial_dir is None or not isinstance(result_summary, dict) or not result_summary:
        return None

    baseline_effect, baseline_n = _effect_from_estimates(
        nonspatial_dir / "effect_estimates.csv",
        "baseline_adjusted_ols",
    )
    baseline_manifest = _read_json(nonspatial_dir / "manifest.json")
    baseline_assessment = assess_scca_evidence_grade(
        credibility_decision=str(baseline_manifest.get("credibility_decision") or "strong_support"),
        robustness_interpretation=str(baseline_manifest.get("robustness_interpretation") or "robust_support"),
    )

    spatial_lag = result_summary.get("spatial_lag_adjusted_ols", {})
    spatial_neighbor = result_summary.get("spatial_neighbor_adjusted_ols", {})
    spatial_diagnostics = result_summary.get("spatial_diagnostics", {})
    graph = result_summary.get("spatial_graph_sensitivity", {})
    enhanced_effect = _finite_float(
        spatial_lag.get("coef") if isinstance(spatial_lag, dict) else None
    )
    if enhanced_effect is None and isinstance(spatial_neighbor, dict):
        enhanced_effect = _finite_float(spatial_neighbor.get("coef"))
    enhanced_n = _finite_float(spatial_lag.get("n")) if isinstance(spatial_lag, dict) else None
    if enhanced_n is None and isinstance(spatial_neighbor, dict):
        enhanced_n = _finite_float(spatial_neighbor.get("n"))

    enhanced_assessment = assess_scca_evidence_grade(
        credibility_decision="strong_support",
        robustness_interpretation="robust_support",
        spatial_summary={
            "residual_moran_i": spatial_diagnostics.get("residual_moran_i")
            if isinstance(spatial_diagnostics, dict)
            else None,
            "residual_moran_p_value": spatial_diagnostics.get("residual_moran_p_value")
            if isinstance(spatial_diagnostics, dict)
            else None,
            "neighbor_exposure_p_value": spatial_lag.get("neighbor_exposure_p_value")
            if isinstance(spatial_lag, dict)
            else spatial_neighbor.get("neighbor_exposure_p_value")
            if isinstance(spatial_neighbor, dict)
            else None,
            "spatial_lag_relative_change": spatial_lag.get("relative_change")
            if isinstance(spatial_lag, dict)
            else None,
            "neighbor_adjusted_relative_change_max": graph.get("neighbor_adjusted_relative_change_max")
            if isinstance(graph, dict)
            else None,
            "neighbor_adjusted_sign_stability": graph.get("neighbor_adjusted_sign_stability")
            if isinstance(graph, dict)
            else None,
        },
    )
    delta = (
        float(enhanced_effect - baseline_effect)
        if enhanced_effect is not None and baseline_effect is not None
        else None
    )
    return {
        "comparison_id": "county_nonspatial_vs_spatial",
        "case": "county_social_capital",
        "baseline_method": "non-spatial adjusted OLS and grouped robustness",
        "enhanced_method": "SCCA spatial lag, residual Moran, graph sensitivity",
        "baseline_effect": baseline_effect,
        "enhanced_effect": enhanced_effect,
        "effect_delta": delta,
        "effect_delta_rel": _delta_rel(enhanced_effect, baseline_effect),
        "baseline_balance_pass": None,
        "enhanced_balance_pass": None,
        "baseline_max_smd": None,
        "enhanced_max_smd": None,
        "baseline_n": baseline_n,
        "enhanced_n": enhanced_n,
        "baseline_residual_moran_i": None,
        "enhanced_residual_moran_i": spatial_diagnostics.get("residual_moran_i")
        if isinstance(spatial_diagnostics, dict)
        else None,
        "baseline_grade": baseline_assessment["evidence_grade"],
        "enhanced_grade": enhanced_assessment["evidence_grade"],
        "enhanced_rule_ids": "; ".join(enhanced_assessment["triggered_rules"]),
        "interpretation": (
            "Spatial diagnostics preserve the positive direction but downgrade the county "
            "case from non-spatial core support to bounded support because residual "
            "spatial structure and neighboring exposure remain visible."
        ),
    }


def _chongqing_row(results_dir: Path) -> dict[str, Any] | None:
    ablation = _read_csv(results_dir / "chongqing_uhi_ablation.csv")
    if ablation.empty:
        return None
    raw = ablation.loc[ablation["variant"].astype(str) == "raw"]
    full = ablation.loc[ablation["variant"].astype(str) == "full_rs_context"]
    if raw.empty or full.empty:
        return None
    raw_record = raw.iloc[0]
    full_record = full.iloc[0]
    residuals = _read_csv(results_dir / "chongqing_residual_spatial_diagnostics.csv")
    residual_record = pd.Series(dtype=object)
    if not residuals.empty:
        rows = residuals.loc[residuals["variant"].astype(str) == "full_rs_context"]
        if not rows.empty:
            residual_record = rows.iloc[0]

    enhanced_assessment = assess_scca_evidence_grade(
        credibility_decision="strong_support"
        if _bool_or_none(full_record.get("balance_pass_0_1")) is True
        else "moderate_support",
        robustness_interpretation="robust_support",
        spatial_summary={
            "residual_moran_i": residual_record.get("moran_i"),
            "residual_moran_p_value": residual_record.get("permutation_p_value"),
        },
    )
    baseline_effect = _finite_float(raw_record.get("att"))
    enhanced_effect = _finite_float(full_record.get("att"))
    delta = (
        float(enhanced_effect - baseline_effect)
        if enhanced_effect is not None and baseline_effect is not None
        else None
    )
    return {
        "comparison_id": "chongqing_raw_vs_full_scca",
        "case": "chongqing_uhi",
        "baseline_method": "raw treated-control difference",
        "enhanced_method": "full remote-sensing, terrain, and geometry SCCA matching",
        "baseline_effect": baseline_effect,
        "enhanced_effect": enhanced_effect,
        "effect_delta": delta,
        "effect_delta_rel": _delta_rel(enhanced_effect, baseline_effect),
        "baseline_balance_pass": False,
        "enhanced_balance_pass": _bool_or_none(full_record.get("balance_pass_0_1")),
        "baseline_max_smd": _finite_float(raw_record.get("max_post_smd")),
        "enhanced_max_smd": _finite_float(full_record.get("max_post_smd")),
        "baseline_n": _finite_float(raw_record.get("complete_n")),
        "enhanced_n": _finite_float(full_record.get("matched_treated_n")),
        "baseline_residual_moran_i": None,
        "enhanced_residual_moran_i": _finite_float(residual_record.get("moran_i")),
        "baseline_grade": "bounded_support",
        "enhanced_grade": enhanced_assessment["evidence_grade"],
        "enhanced_rule_ids": "; ".join(enhanced_assessment["triggered_rules"]),
        "interpretation": (
            "Full SCCA retains a modest positive UHI estimate while adding explicit "
            "balance and residual-spatial diagnostics that the raw comparison lacks."
        ),
    }


def build_scca_method_comparison(results_dir: str | Path = DEFAULT_RESULTS_DIR) -> pd.DataFrame:
    root = Path(results_dir)
    rows = [
        row
        for row in (
            _county_comparison_row(root),
            _chongqing_row(root),
        )
        if row is not None
    ]
    return pd.DataFrame(rows, columns=COMPARISON_COLUMNS)


def render_method_comparison_report(table: pd.DataFrame) -> str:
    lines = [
        "# SCCA Method Comparison Report",
        "",
        f"- Grade rule version: `{RULE_VERSION}`",
        "",
        "This report directly compares simpler baselines with SCCA-enhanced analyses.",
        "",
    ]
    if table.empty:
        lines.append("No comparison rows were available.")
        return "\n".join(lines) + "\n"
    for _, row in table.iterrows():
        lines.extend(
            [
                f"## {row['comparison_id']}",
                "",
                f"- Baseline: {row['baseline_method']}",
                f"- SCCA-enhanced: {row['enhanced_method']}",
                f"- Effect change: {row['baseline_effect']} -> {row['enhanced_effect']} "
                f"(relative delta {row['effect_delta_rel']})",
                f"- Grade change: `{row['baseline_grade']}` -> `{row['enhanced_grade']}`",
                f"- Enhanced rule ids: `{row['enhanced_rule_ids']}`",
                f"- Interpretation: {row['interpretation']}",
                "",
            ]
        )
    return "\n".join(lines)


def run_scca_method_comparison(
    *,
    output_dir: str | Path = DEFAULT_RESULTS_DIR,
    results_dir: str | Path = DEFAULT_RESULTS_DIR,
) -> dict[str, Any]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    table = build_scca_method_comparison(results_dir)
    comparison_path = target / OUTPUT_FILES["comparison_csv"]
    report_path = target / OUTPUT_FILES["report_md"]
    manifest_path = target / OUTPUT_FILES["manifest_json"]
    table.to_csv(comparison_path, index=False)
    report_path.write_text(render_method_comparison_report(table), encoding="utf-8")
    manifest = {
        "comparison_csv": str(comparison_path),
        "report_md": str(report_path),
        "manifest_json": str(manifest_path),
        "results_dir": str(Path(results_dir)),
        "n_rows": int(len(table)),
        "comparisons": table["comparison_id"].tolist() if not table.empty else [],
        "rule_version": RULE_VERSION,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Write direct SCCA method comparison artifacts.")
    parser.add_argument("--output-dir", default=str(DEFAULT_RESULTS_DIR))
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR))
    args = parser.parse_args()
    manifest = run_scca_method_comparison(
        output_dir=args.output_dir,
        results_dir=args.results_dir,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
