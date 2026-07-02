from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from data_agent.experiments.run_scca_county_social_capital import (
    DEFAULT_SHEET_NAME,
    load_county_social_capital_workbook,
    prepare_county_social_capital_table,
)
from data_agent.scca.arcgis_sci_plus import (
    arcgis_quantile_trim,
    build_arcgis_sci_plus_report,
    solve_target_exposure,
)
from data_agent.scca.context import build_context_features
from data_agent.scca.design import select_design
from data_agent.scca.estimators import estimate_effects
from data_agent.scca.scale import build_scale_summary
from data_agent.scca.specs import SCCAPaths, StudySpec


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "paper"
    / "ijgis_submission_20260605"
    / "07_results"
    / "arcgis_sci_plus_county"
)


def _erf_summary(erf_curve: pd.DataFrame) -> dict[str, object]:
    frame = erf_curve[["exposure", "response"]].apply(
        pd.to_numeric, errors="coerce"
    )
    frame = frame.dropna()
    if frame.empty:
        return {
            "status": "skipped",
            "range_effect": None,
            "monotonic_direction": "unknown",
        }
    response_delta = float(frame["response"].iloc[-1] - frame["response"].iloc[0])
    return {
        "status": "ok",
        "range_effect": response_delta,
        "monotonic_direction": "increasing" if response_delta >= 0 else "decreasing",
    }


def run_arcgis_sci_plus_county(
    workbook_path: str | Path,
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    sheet_name: str = DEFAULT_SHEET_NAME,
    target_response: float = 70.0,
) -> dict[str, object]:
    spec = StudySpec.county_social_capital_default()
    paths = SCCAPaths(output_dir=Path(output_dir))
    paths.ensure()

    raw = load_county_social_capital_workbook(workbook_path, sheet_name=sheet_name)
    prepared = prepare_county_social_capital_table(raw)
    trimmed, trim_summary = arcgis_quantile_trim(prepared, spec.exposure)

    features, _ = build_context_features(trimmed, spec, paths)
    select_design(features, spec, paths)
    estimate_effects(features, spec, paths)
    scale_summary = build_scale_summary(features, spec, paths)

    erf_curve = pd.read_csv(paths.erf_curve)
    erf = _erf_summary(erf_curve)
    target = solve_target_exposure(erf_curve, target_response=target_response)
    report = build_arcgis_sci_plus_report(
        study=spec.name,
        arcgis_trim_summary=trim_summary,
        erf_summary=erf,
        target_summary=target,
        spatial_risk={
            "residual_moran": None,
            "neighbor_exposure_p": None,
            "note": (
                "Spatial diagnostics are attached when geometry or coordinates are "
                "available."
            ),
        },
        role_risk={"post_treatment_warnings": []},
        scale_risk=scale_summary,
    )

    report_path = paths.output_dir / "arcgis_sci_plus_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    manifest = {
        "study": spec.name,
        "source_workbook": str(workbook_path),
        "arcgis_sci_plus_report": report_path.name,
        "files": {
            "effect_estimates": paths.effect_estimates.name,
            "erf_curve": paths.erf_curve.name,
            "scale_summary": paths.scale_summary.name,
            "manifest": paths.manifest.name,
        },
    }
    paths.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run ArcGIS SCI Plus county comparison."
    )
    parser.add_argument("--workbook-path", required=True)
    parser.add_argument("--sheet-name", default=DEFAULT_SHEET_NAME)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--target-response", type=float, default=70.0)
    args = parser.parse_args()
    manifest = run_arcgis_sci_plus_county(
        args.workbook_path,
        output_dir=args.output_dir,
        sheet_name=args.sheet_name,
        target_response=args.target_response,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
