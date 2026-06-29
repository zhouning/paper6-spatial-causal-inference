"""ArcGIS Causal Inference Analysis parity benchmark for Paper 6 SCCA."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results"
DEFAULT_OUTPUT_DIR = DEFAULT_RESULTS_DIR / "arcgis_causal_inference_parity"
OFFICIAL_ARCGIS_URL = (
    "https://pro.arcgis.com/en/pro-app/latest/tool-reference/"
    "spatial-statistics/causal-inference-analysis.htm"
)
PARITY_COLUMNS = [
    "arcgis_capability",
    "arcgis_product_meaning",
    "scca_status",
    "commercial_priority",
    "evidence_artifact",
    "next_action",
]


def build_arcgis_parity_matrix() -> pd.DataFrame:
    """Return the documented ArcGIS-to-SCCA commercial parity matrix."""

    rows = [
        {
            "arcgis_capability": "continuous_exposure_outcome_workflow",
            "arcgis_product_meaning": "Continuous exposure with continuous or binary outcome causal workflow.",
            "scca_status": "matched",
            "commercial_priority": "P0",
            "evidence_artifact": "county social-capital notebook and SCCA AnalysisRequest workflow",
            "next_action": "Keep as the primary ArcGIS-facing commercial parity benchmark.",
        },
        {
            "arcgis_capability": "user_declared_confounders",
            "arcgis_product_meaning": "User-selected adjustment variables define the causal design.",
            "scca_status": "matched",
            "commercial_priority": "P0",
            "evidence_artifact": "AnalysisRequest.confounders",
            "next_action": "Expose the same design vocabulary in GIS-facing product docs.",
        },
        {
            "arcgis_capability": "ols_or_gradient_boosting_propensity_score",
            "arcgis_product_meaning": "OLS propensity score by default, with gradient boosting fallback.",
            "scca_status": "matched",
            "commercial_priority": "P0",
            "evidence_artifact": "OLS/GBM GPS grid search, Open GIS score aliases, and nonlinear balance benchmark",
            "next_action": "Keep arcgis_gps_balance_benchmark refreshed as GPS method selection changes.",
        },
        {
            "arcgis_capability": "propensity_score_matching",
            "arcgis_product_meaning": "Balance observations through propensity-score matching.",
            "scca_status": "partial",
            "commercial_priority": "P0",
            "evidence_artifact": "binary case matching modules",
            "next_action": "Define a continuous-exposure matching output contract.",
        },
        {
            "arcgis_capability": "inverse_propensity_score_weighting",
            "arcgis_product_meaning": "Use inverse propensity score weights as a faster balancing method.",
            "scca_status": "partial",
            "commercial_priority": "P0",
            "evidence_artifact": "ERF weighting outputs",
            "next_action": "Write ArcGIS-compatible score and weight aliases to GIS tables.",
        },
        {
            "arcgis_capability": "one_to_ninetynine_exposure_trimming",
            "arcgis_product_meaning": "Trim observations outside the 1st and 99th exposure percentiles.",
            "scca_status": "matched",
            "commercial_priority": "P0",
            "evidence_artifact": "county workflow retains 3,044 of 3,108 rows",
            "next_action": "Keep row accounting visible in every generated report.",
        },
        {
            "arcgis_capability": "weighted_correlation_balance_threshold",
            "arcgis_product_meaning": "Judge confounder balance with weighted correlation and a threshold.",
            "scca_status": "matched",
            "commercial_priority": "P0",
            "evidence_artifact": "Open GIS balance summaries expose mean/median/max absolute weighted-correlation fields",
            "next_action": "Keep mean/median/max balance fields stable in every Open GIS package.",
        },
        {
            "arcgis_capability": "erf_table",
            "arcgis_product_meaning": "Exposure-response function table over exposure support.",
            "scca_status": "matched",
            "commercial_priority": "P0",
            "evidence_artifact": "SCCA ERF curve outputs",
            "next_action": "Add a fixed 200-point ArcGIS parity option if product demos require it.",
        },
        {
            "arcgis_capability": "target_exposure_and_target_outcome_fields",
            "arcgis_product_meaning": "What-if outcome and required-exposure fields for target values.",
            "scca_status": "partial",
            "commercial_priority": "P0",
            "evidence_artifact": "county target-exposure spatial outputs",
            "next_action": "Verify and document target-outcome output contract.",
        },
        {
            "arcgis_capability": "local_erf_popups",
            "arcgis_product_meaning": "Per-feature local ERF chart interaction in the GIS interface.",
            "scca_status": "gap",
            "commercial_priority": "P2",
            "evidence_artifact": "notebook and HTML map alternatives",
            "next_action": "Defer ArcGIS-native popup parity until after CLI/toolbox MVP.",
        },
        {
            "arcgis_capability": "spatial_residual_diagnostics",
            "arcgis_product_meaning": "Spatial diagnostic and evidence-boundary layer beyond the ArcGIS causal workflow.",
            "scca_status": "scca_only_differentiator",
            "commercial_priority": "P0",
            "evidence_artifact": "residual Moran's I and evidence-grade downgrade rules",
            "next_action": "Make this the main product differentiation, not an overclaim of identification.",
        },
    ]
    return pd.DataFrame(rows, columns=PARITY_COLUMNS)

def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _nested(mapping: dict[str, Any], *keys: str) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _has_recorded_files(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, list):
        return bool(value)
    return bool(value)


def inspect_county_parity_artifacts(results_dir: str | Path) -> dict[str, Any]:
    """Extract ArcGIS-facing metrics from the county social-capital result summary."""

    root = Path(results_dir)
    summary = _read_json(root / "county_social_capital_spatial_notebook_summary.json")
    if not summary:
        summary = _read_json(
            root
            / "examples"
            / "county_social_capital_notebook_demo"
            / "notebook_demo_summary.json"
        )
    result_summary = summary.get("result_summary", {}) if isinstance(summary, dict) else {}
    spatial_manifest = summary.get("spatial_manifest", {}) if isinstance(summary, dict) else {}

    return {
        "input_rows": spatial_manifest.get("row_count"),
        "included_rows": spatial_manifest.get("matched_count"),
        "baseline_coef": _nested(result_summary, "baseline_adjusted_ols", "coef"),
        "spatial_neighbor_adjusted_coef": _nested(
            result_summary,
            "spatial_neighbor_adjusted_ols",
            "coef",
        ),
        "spatial_lag_adjusted_coef": _nested(
            result_summary,
            "spatial_lag_adjusted_ols",
            "coef",
        ),
        "residual_moran_i": _nested(
            result_summary,
            "spatial_diagnostics",
            "residual_moran_i",
        ),
        "residual_moran_p_value": _nested(
            result_summary,
            "spatial_diagnostics",
            "residual_moran_p_value",
        ),
        "spatial_files_available": _has_recorded_files(
            spatial_manifest.get("spatial_files")
        ),
        "visualization_files_available": _has_recorded_files(
            spatial_manifest.get("visualization_files")
            or spatial_manifest.get("visualizations")
        ),
    }

def _fmt_value(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def render_arcgis_parity_summary(matrix: pd.DataFrame, county_metrics: dict[str, Any]) -> str:
    """Render the commercial ArcGIS parity benchmark as a Markdown report."""

    status_counts = matrix["scca_status"].value_counts().to_dict()
    lines = [
        "# ArcGIS Causal Inference Analysis Parity Benchmark",
        "",
        f"Official ArcGIS baseline: {OFFICIAL_ARCGIS_URL}",
        "",
        "## Positioning",
        "",
        "SCCA is positioned as an open spatial-diagnostic enhancement layer for GIS causal workflows.",
        "The benchmark does not claim that SCCA reproduces proprietary ArcGIS internals or fully replaces ArcGIS Pro.",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in sorted(status_counts.items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend(
        [
            "",
            "## County Parity Metrics",
            "",
            f"- Input rows: {_fmt_value(county_metrics.get('input_rows'))}",
            f"- Included rows after support trimming: {_fmt_value(county_metrics.get('included_rows'))}",
            f"- Baseline adjusted coefficient: {_fmt_value(county_metrics.get('baseline_coef'))}",
            f"- Neighbor-adjusted coefficient: {_fmt_value(county_metrics.get('spatial_neighbor_adjusted_coef'))}",
            f"- Spatial-lag adjusted coefficient: {_fmt_value(county_metrics.get('spatial_lag_adjusted_coef'))}",
            f"- Residual Moran's I: {_fmt_value(county_metrics.get('residual_moran_i'))}",
            f"- Residual Moran p-value: {_fmt_value(county_metrics.get('residual_moran_p_value'))}",
            f"- Spatial files available: {_fmt_value(county_metrics.get('spatial_files_available'))}",
            f"- Visualization files available: {_fmt_value(county_metrics.get('visualization_files_available'))}",
            "",
            "## Capability Matrix",
            "",
            "| ArcGIS capability | Product meaning | SCCA status | Priority | Evidence | Next action |",
            "|---|---|---:|---:|---|---|",
        ]
    )
    for _, record in matrix.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    str(record["arcgis_capability"]),
                    str(record["arcgis_product_meaning"]),
                    str(record["scca_status"]),
                    str(record["commercial_priority"]),
                    str(record["evidence_artifact"]),
                    str(record["next_action"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Commercial Interpretation",
            "",
            "The county benchmark demonstrates ArcGIS-style row accounting and continuous-exposure output shape, while the residual spatial diagnostics define the evidence boundary. This is the product-facing SCCA value: make GIS causal workflows auditable under spatial dependence rather than presenting an unchecked causal estimate.",
            "",
        ]
    )
    return "\n".join(lines)


def write_arcgis_commercial_benchmark(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    results_dir: str | Path = DEFAULT_RESULTS_DIR,
) -> dict[str, Any]:
    """Write ArcGIS-facing commercial benchmark artifacts for Paper 6 SCCA."""

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    matrix = build_arcgis_parity_matrix()
    county_metrics = inspect_county_parity_artifacts(results_dir)

    matrix_path = target / "arcgis_parity_matrix.csv"
    summary_path = target / "arcgis_parity_summary.md"
    manifest_path = target / "arcgis_commercial_benchmark_manifest.json"

    matrix.to_csv(matrix_path, index=False)
    summary_path.write_text(
        render_arcgis_parity_summary(matrix, county_metrics),
        encoding="utf-8",
    )

    manifest: dict[str, Any] = {
        "parity_matrix_csv": str(matrix_path),
        "parity_summary_md": str(summary_path),
        "manifest_json": str(manifest_path),
        "results_dir": str(Path(results_dir)),
        "official_arcgis_url": OFFICIAL_ARCGIS_URL,
        "status_counts": matrix["scca_status"].value_counts().to_dict(),
        "county_metrics": county_metrics,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write the Paper 6 SCCA ArcGIS commercial parity benchmark."
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR))
    args = parser.parse_args()
    manifest = write_arcgis_commercial_benchmark(
        output_dir=args.output_dir,
        results_dir=args.results_dir,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
