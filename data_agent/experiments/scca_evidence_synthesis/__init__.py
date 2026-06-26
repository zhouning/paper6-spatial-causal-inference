"""EPA-aware wrapper around the Paper 6 SCCA evidence synthesis module."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

import pandas as pd


_LEGACY_PATH = Path(__file__).resolve().parent.parent / "scca_evidence_synthesis.py"
_SPEC = importlib.util.spec_from_file_location("_paper6_legacy_scca_evidence_synthesis", _LEGACY_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot load legacy evidence synthesis module at {_LEGACY_PATH}")
_legacy = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_legacy)

RULE_VERSION = _legacy.RULE_VERSION
DEFAULT_RESULTS_DIR = _legacy.DEFAULT_RESULTS_DIR
OUTPUT_FILES = _legacy.OUTPUT_FILES
SYNTHESIS_COLUMNS = _legacy.SYNTHESIS_COLUMNS
render_scca_evidence_report = _legacy.render_scca_evidence_report
write_evidence_rule_outputs = _legacy.write_evidence_rule_outputs


def _fmt_list(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(map(str, value))
    return "" if value is None else str(value)


def _epa_airdata_row(results_dir: Path) -> dict[str, str] | None:
    summary = _legacy._read_json(
        results_dir / "epa_nonattainment_airdata" / "benchmark_summary.json"
    )
    if not summary:
        return None
    real = summary.get("real_data", {})
    synthetic = summary.get("semi_synthetic", {})
    if not isinstance(real, dict) or not isinstance(synthetic, dict):
        return None
    spatial_caution = synthetic.get("spatial_caution_scenarios", [])
    spatial_caution_text = ", ".join(map(str, spatial_caution)) if isinstance(spatial_caution, list) else str(spatial_caution)
    return _legacy._row(
        case="epa_nonattainment_airdata",
        data_type="public spatiotemporal policy benchmark",
        exposure="lagged Clean Air Act nonattainment status",
        outcome="annual county-level pollutant concentration",
        context_source="lagged pollution, monitor coverage, county coordinates, and neighboring nonattainment",
        best_adjustment="GeoCausal SCCA annual county-year panel with semi-synthetic known-effect checks",
        effect_estimate=(
            f"policy-structure semi-synthetic coefficient = {_legacy._fmt_num(real.get('effect_estimate'))}; "
            f"semi-synthetic median absolute error = {_legacy._fmt_num(synthetic.get('median_absolute_error'))}"
        ),
        balance_status=(
            f"{real.get('row_count', 'NA')} county-year rows, "
            f"{real.get('panel_year_min', 'NA')}-{real.get('panel_year_max', 'NA')}"
        ),
        robustness_status=(
            f"{synthetic.get('scenario_count', 'NA')} semi-synthetic scenarios; "
            f"spatial caution scenarios = {spatial_caution_text or 'none'}"
        ),
        evidence_grade=str(real.get("evidence_grade") or "bounded_support"),
        grade_rule_ids=_fmt_list(real.get("grade_rule_ids", [])),
        grade_reasons=_fmt_list(real.get("grade_reasons", [])),
        limitation=(
            "This run uses a deterministic known-effect outcome on real EPA policy geography; it is "
            "not an observational causal policy estimate until AQS AirData acquisition succeeds."
        ),
        manuscript_use=(
            "Use as a public spatiotemporal benchmark; rely on the semi-synthetic known-effect layer "
            "for validation, while treating observational AirData validation as pending."
        ),
    )


def build_scca_evidence_table(
    results_dir: str | Path = DEFAULT_RESULTS_DIR,
) -> pd.DataFrame:
    """Build the evidence matrix and append the EPA benchmark when available."""

    root = Path(results_dir)
    table = _legacy.build_scca_evidence_table(root)
    epa_row = _epa_airdata_row(root)
    if epa_row is None:
        return table
    rows = table.to_dict("records") if not table.empty else []
    rows.append(epa_row)
    combined = pd.DataFrame(rows, columns=SYNTHESIS_COLUMNS)
    order = {
        "synthetic_benchmark_audit": 0,
        "chongqing_uhi": 1,
        "epa_nonattainment_airdata": 2,
        "county_social_capital_spatial_notebook": 3,
    }
    combined["_order"] = combined["case"].map(order).fillna(99)
    return combined.sort_values(["_order", "case"]).drop(columns=["_order"]).reset_index(drop=True)


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
        "grade_counts": table["evidence_grade"].value_counts().to_dict()
        if not table.empty
        else {},
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

