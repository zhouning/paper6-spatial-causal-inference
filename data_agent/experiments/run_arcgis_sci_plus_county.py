from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
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


def _generated_at_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _source_sha256(workbook_path: Path) -> str:
    return hashlib.sha256(workbook_path.read_bytes()).hexdigest()


def _spatial_risk_unavailable() -> dict[str, object]:
    return {
        "status": "unavailable",
        "reason": "missing_coordinates_or_geometry",
        "residual_moran": None,
        "neighbor_exposure_p": None,
        "note": (
            "Spatial diagnostics are attached when geometry or coordinates are "
            "available."
        ),
    }


def _skipped_erf_summary() -> dict[str, object]:
    return {
        "status": "skipped",
        "range_effect": None,
        "monotonic_direction": "unknown",
    }


def _skipped_target_summary(target_response: float) -> dict[str, object]:
    return {
        "status": "skipped",
        "target_response": float(target_response),
        "target_exposure": None,
        "target_prediction": None,
        "warnings": [
            "Target analysis skipped because ArcGIS quantile trim produced no "
            "analyzable rows."
        ],
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _manifest(
    *,
    spec: StudySpec,
    paths: SCCAPaths,
    workbook_path: Path,
    report_path: Path,
    sheet_name: str,
    raw: pd.DataFrame,
    status: str,
    include_model_files: bool,
) -> dict[str, object]:
    files = {
        "manifest": paths.manifest.name,
        "arcgis_sci_plus_report": report_path.name,
    }
    if include_model_files:
        files.update(
            {
                "effect_estimates": paths.effect_estimates.name,
                "erf_curve": paths.erf_curve.name,
                "scale_summary": paths.scale_summary.name,
            }
        )
    return {
        "study": spec.name,
        "status": status,
        "source_workbook": str(workbook_path),
        "source_sha256": _source_sha256(workbook_path),
        "sheet_name": sheet_name,
        "input_rows": int(raw.shape[0]),
        "input_columns": int(raw.shape[1]),
        "generated_at_utc": _generated_at_utc(),
        "arcgis_sci_plus_report": report_path.name,
        "files": files,
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

    source_path = Path(workbook_path)
    raw = load_county_social_capital_workbook(source_path, sheet_name=sheet_name)
    prepared = prepare_county_social_capital_table(raw)
    trimmed, trim_summary = arcgis_quantile_trim(prepared, spec.exposure)
    report_path = paths.output_dir / "arcgis_sci_plus_report.json"

    if trim_summary.get("status") == "skipped" or trimmed.empty:
        report = build_arcgis_sci_plus_report(
            study=spec.name,
            arcgis_trim_summary=trim_summary,
            erf_summary=_skipped_erf_summary(),
            target_summary=_skipped_target_summary(target_response),
            spatial_risk={
                **_spatial_risk_unavailable(),
                "reason": "arcgis_quantile_trim_skipped",
            },
            role_risk={"status": "unavailable", "post_treatment_warnings": []},
            scale_risk={
                "scale_status": "unavailable",
                "reason": "arcgis_quantile_trim_skipped",
            },
        )
        _write_json(report_path, report)
        manifest = _manifest(
            spec=spec,
            paths=paths,
            workbook_path=source_path,
            report_path=report_path,
            sheet_name=sheet_name,
            raw=raw,
            status="skipped",
            include_model_files=False,
        )
        _write_json(paths.manifest, manifest)
        return manifest

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
        spatial_risk=_spatial_risk_unavailable(),
        role_risk={"post_treatment_warnings": []},
        scale_risk=scale_summary,
    )

    _write_json(report_path, report)
    manifest = _manifest(
        spec=spec,
        paths=paths,
        workbook_path=source_path,
        report_path=report_path,
        sheet_name=sheet_name,
        raw=raw,
        status="ok",
        include_model_files=True,
    )
    _write_json(paths.manifest, manifest)
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
