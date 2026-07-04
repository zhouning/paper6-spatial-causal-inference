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
    arcgis_documented_causal_analysis,
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


COUNTY_VARIABLE_PROVENANCE_FILE = "county_variable_provenance.csv"
COUNTY_VARIABLE_PROVENANCE: tuple[dict[str, str], ...] = (
    {
        "field": "FIPS",
        "analysis_role": "unit_id",
        "display_name": "FIPS county code",
        "source_group": "County geometry / identifiers",
        "upstream_field_or_table": "USA_Counties.FIPS",
        "source_detail": "Esri county layer with Census and NOAA/NOS/NGS credits in CountyData metadata.",
        "lineage_evidence": "CountyData.shp.xml idCredit; JoinField USA_Counties FIPS NAME.",
        "source_confidence": "metadata_explicit",
    },
    {
        "field": "STATE_NAME",
        "analysis_role": "bootstrap_group",
        "display_name": "State",
        "source_group": "County geometry / identifiers",
        "upstream_field_or_table": "CountyData.STATE_NAME",
        "source_detail": "State attribute carried by the Esri county training/demo layer.",
        "lineage_evidence": "CountyData.shp.xml export field mapping.",
        "source_confidence": "metadata_explicit",
    },
    {
        "field": "CountyCode",
        "analysis_role": "identifier",
        "display_name": "County Code",
        "source_group": "County geometry / identifiers",
        "upstream_field_or_table": "calculated from FIPS",
        "source_detail": "County code calculated from FIPS during the ArcGIS package lineage.",
        "lineage_evidence": "CountyData.shp.xml CalculateField CountyCode !FIPS!.",
        "source_confidence": "metadata_explicit",
    },
    {
        "field": "County",
        "analysis_role": "label",
        "display_name": "County",
        "source_group": "County geometry / identifiers",
        "upstream_field_or_table": "USA_Counties.NAME",
        "source_detail": "County name joined from the USA_Counties layer.",
        "lineage_evidence": "CountyData.shp.xml JoinField USA_Counties FIPS NAME and CalculateField County !NAME!.",
        "source_confidence": "metadata_explicit",
    },
    {
        "field": "SocialAssoc",
        "analysis_role": "exposure",
        "display_name": "Social capital",
        "source_group": "County Health Rankings 2019 / ArcGIS Living Atlas",
        "upstream_field_or_table": "2019 County Health Rankings via ArcGIS Living Atlas",
        "source_detail": "Social-capital variable credited to 2019 County Health Rankings, ArcGIS Living Atlas, UWPHI, and RWJF.",
        "lineage_evidence": "CountyData.shp.xml idCredit and final export field mapping.",
        "source_confidence": "metadata_explicit_grouped",
    },
    {
        "field": "AveAgeDeath",
        "analysis_role": "outcome",
        "display_name": "Average age at death",
        "source_group": "CDC WONDER Underlying Cause of Death",
        "upstream_field_or_table": "CountyAveAgeOfDeath.AveAgeDeath",
        "source_detail": "Average age at death derived from CDC WONDER Underlying Cause of Death data for 1999-2019.",
        "lineage_evidence": "CountyData.shp.xml JoinField CountyAveAgeOfDeath and CDC WONDER idCredit.",
        "source_confidence": "metadata_explicit",
    },
    {
        "field": "UnemployRate",
        "analysis_role": "confounder",
        "display_name": "Unemployment Rate",
        "source_group": "Esri training/demo package lineage",
        "upstream_field_or_table": "CountyDataUnemployment.industry_UNEMPRT_CY",
        "source_detail": "Unemployment rate joined from CountyDataUnemployment; the local metadata records the table and field but not a separate external producer citation.",
        "lineage_evidence": "CountyData.shp.xml JoinField CountyDataUnemployment and AlterField industry_UNEMPRT_CY to UnemploymentRate/UnemployRate.",
        "source_confidence": "lineage_only_external_source_unresolved",
    },
    {
        "field": "pHHinPoverty",
        "analysis_role": "confounder",
        "display_name": "% HH living in poverty",
        "source_group": "ArcGIS Pro Enrich / Esri",
        "upstream_field_or_table": "households_ACSHHBPOV_P",
        "source_detail": "ACS household below-poverty percentage appended through ArcGIS Pro Enrich/Esri lineage.",
        "lineage_evidence": "CountyData.shp.xml export alias ACS HHs: Inc Below Poverty Level : Percent and AlterField to pHHinPoverty.",
        "source_confidence": "metadata_explicit_lineage",
    },
    {
        "field": "pNoHealthInsur",
        "analysis_role": "confounder",
        "display_name": "% No Health Insurance",
        "source_group": "ArcGIS Pro Enrich / Esri",
        "upstream_field_or_table": "CountyDataEnrich1.pNoHealthInsurance",
        "source_detail": "No-health-insurance percentage appended through ArcGIS Pro Enrich/Esri lineage.",
        "lineage_evidence": "CountyData.shp.xml JoinField CountyDataEnrich1 pNoHealthInsurance and final export field pNoHealthInsur.",
        "source_confidence": "metadata_explicit_lineage",
    },
    {
        "field": "MentalHealth",
        "analysis_role": "confounder",
        "display_name": "Poor Mental Health Days",
        "source_group": "County Health Rankings 2019 / ArcGIS Living Atlas",
        "upstream_field_or_table": "County Health Rankings 2019 v042_rawvalue",
        "source_detail": "Poor mental health days from 2019 County Health Rankings via ArcGIS Living Atlas.",
        "lineage_evidence": "CountyData.shp.xml JoinField County Health Rankings 2019 v042_rawvalue and AlterField to MentalHealth.",
        "source_confidence": "metadata_explicit_lineage",
    },
    {
        "field": "pAdultSmoking",
        "analysis_role": "confounder",
        "display_name": "Adult smoking (%)",
        "source_group": "County Health Rankings 2019 / ArcGIS Living Atlas",
        "upstream_field_or_table": "CountyHealthRankings2019.v009_rawvalue",
        "source_detail": "Adult smoking percentage from 2019 County Health Rankings via ArcGIS Living Atlas.",
        "lineage_evidence": "CountyData.shp.xml JoinField CountyHealthRankings2019 v009_rawvalue and AlterField to pAdultSmoking.",
        "source_confidence": "metadata_explicit_lineage",
    },
    {
        "field": "pAdultObesity",
        "analysis_role": "confounder",
        "display_name": "Adult obesity (%)",
        "source_group": "County Health Rankings 2019 / ArcGIS Living Atlas",
        "upstream_field_or_table": "CountyHealthRankings2019.v011_rawvalue",
        "source_detail": "Adult obesity percentage from 2019 County Health Rankings via ArcGIS Living Atlas.",
        "lineage_evidence": "CountyData.shp.xml JoinField CountyHealthRankings2019 v011_rawvalue and AlterField to pAdultObesity.",
        "source_confidence": "metadata_explicit_lineage",
    },
    {
        "field": "FastFood",
        "analysis_role": "confounder",
        "display_name": "High fast food spending",
        "source_group": "ArcGIS Pro Enrich / Esri",
        "upstream_field_or_table": "restaurants_MP29044a_B_P",
        "source_detail": "Fast-food spending variable appended through ArcGIS Pro Enrich/Esri lineage.",
        "lineage_evidence": "CountyData.shp.xml AlterField restaurants_MP29044a_B_P to FastFood and final export field mapping.",
        "source_confidence": "metadata_explicit_lineage",
    },
    {
        "field": "pInsufficientSleep",
        "analysis_role": "confounder",
        "display_name": "% insufficient sleep",
        "source_group": "County Health Rankings 2019 / ArcGIS Living Atlas",
        "upstream_field_or_table": "County Health Rankings 2019 v143_rawvalue",
        "source_detail": "Insufficient sleep percentage from 2019 County Health Rankings via ArcGIS Living Atlas.",
        "lineage_evidence": "CountyData.shp.xml JoinField County Health Rankings 2019 v143_rawvalue, AlterField to InsufficientSleep, then pInsufficientSleep.",
        "source_confidence": "metadata_explicit_lineage",
    },
    {
        "field": "pAlcohol",
        "analysis_role": "confounder",
        "display_name": "Alcohol related deaths",
        "source_group": "CDC WONDER Underlying Cause of Death",
        "upstream_field_or_table": "AlcoholDeathsByCounty.pAlcohol",
        "source_detail": "Alcohol-related deaths per 100,000 from CDC WONDER Underlying Cause of Death data for 1999-2019.",
        "lineage_evidence": "CountyData.shp.xml JoinField AlcoholDeathsByCounty and CDC WONDER idCredit.",
        "source_confidence": "metadata_explicit",
    },
    {
        "field": "pSuicideDeaths",
        "analysis_role": "confounder",
        "display_name": "Suicide deaths",
        "source_group": "CDC WONDER Underlying Cause of Death",
        "upstream_field_or_table": "SuicidesByCounty.pSuicideDeaths",
        "source_detail": "Suicide deaths per 100,000 from CDC WONDER Underlying Cause of Death data for 1999-2019.",
        "lineage_evidence": "CountyData.shp.xml JoinField SuicidesByCounty and CDC WONDER idCredit.",
        "source_confidence": "metadata_explicit",
    },
    {
        "field": "AirPollution",
        "analysis_role": "confounder",
        "display_name": "Air pollution PM density",
        "source_group": "County Health Rankings 2019 / ArcGIS Living Atlas",
        "upstream_field_or_table": "2019 County Health Rankings via ArcGIS Living Atlas",
        "source_detail": "Air-pollution variable credited to 2019 County Health Rankings, ArcGIS Living Atlas, UWPHI, and RWJF.",
        "lineage_evidence": "CountyData.shp.xml idCredit and final export field mapping.",
        "source_confidence": "metadata_explicit_grouped",
    },
    {
        "field": "Shape_Length",
        "analysis_role": "spatial_context",
        "display_name": "Shape length",
        "source_group": "County geometry / identifiers",
        "upstream_field_or_table": "CountyData geometry",
        "source_detail": "Geometry-derived length from the Esri county training/demo layer.",
        "lineage_evidence": "CountyData.shp.xml final export field mapping.",
        "source_confidence": "metadata_explicit",
    },
    {
        "field": "Shape_Area",
        "analysis_role": "spatial_context",
        "display_name": "Shape area",
        "source_group": "County geometry / identifiers",
        "upstream_field_or_table": "CountyData geometry",
        "source_detail": "Geometry-derived area from the Esri county training/demo layer.",
        "lineage_evidence": "CountyData.shp.xml final export field mapping.",
        "source_confidence": "metadata_explicit",
    },
)

def _erf_summary(erf_curve: pd.DataFrame, extra: dict[str, object] | None = None) -> dict[str, object]:
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
    summary = {
        "status": "ok",
        "range_effect": response_delta,
        "monotonic_direction": "increasing" if response_delta >= 0 else "decreasing",
    }
    if extra:
        summary.update(extra)
    return summary


def _generated_at_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _source_sha256(workbook_path: Path) -> str:
    return hashlib.sha256(workbook_path.read_bytes()).hexdigest()


def _write_county_variable_provenance(output_dir: Path) -> Path:
    path = output_dir / COUNTY_VARIABLE_PROVENANCE_FILE
    pd.DataFrame(COUNTY_VARIABLE_PROVENANCE).to_csv(path, index=False)
    return path


def _county_variable_provenance_summary(output_dir: Path) -> dict[str, object]:
    path = output_dir / COUNTY_VARIABLE_PROVENANCE_FILE
    source_groups = sorted(
        {record["source_group"] for record in COUNTY_VARIABLE_PROVENANCE}
    )
    unresolved_fields = sorted(
        record["field"]
        for record in COUNTY_VARIABLE_PROVENANCE
        if "unresolved" in record["source_confidence"]
    )
    summary: dict[str, object] = {
        "status": "ok" if path.exists() else "missing_file",
        "file": COUNTY_VARIABLE_PROVENANCE_FILE,
        "field_count": len(COUNTY_VARIABLE_PROVENANCE),
        "source_groups": source_groups,
        "unresolved_fields": unresolved_fields,
    }
    if unresolved_fields:
        summary["warnings"] = [
            f"{field} has lineage-only external source evidence."
            for field in unresolved_fields
        ]
    return summary


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
    arcgis_documented_files: dict[str, str] | None = None,
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
    if arcgis_documented_files:
        files.update(arcgis_documented_files)
    provenance = paths.output_dir / COUNTY_VARIABLE_PROVENANCE_FILE
    if provenance.exists():
        files["county_variable_provenance"] = provenance.name
    native_parity = paths.output_dir / "arcgis_native_parity_metrics.json"
    if native_parity.exists():
        files["arcgis_native_parity_metrics"] = native_parity.name
    return {
        "study": spec.name,
        "status": status,
        "source_workbook": workbook_path.name,
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
    _write_county_variable_provenance(paths.output_dir)
    data_provenance = _county_variable_provenance_summary(paths.output_dir)

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
            data_provenance=data_provenance,
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

    documented = arcgis_documented_causal_analysis(
        features,
        exposure=spec.exposure,
        outcome=spec.outcome,
        confounders=list(spec.confounders),
        balance_threshold=0.1,
        num_bins=25,
        scale=0.8,
    )
    arcgis_documented_files: dict[str, str] = {}
    arcgis_algorithm_summary = None
    if documented.get("status") == "ok":
        documented_analysis = paths.output_dir / "arcgis_documented_analysis.csv"
        documented_matching_grid = paths.output_dir / "arcgis_documented_matching_grid.csv"
        documented_balance = paths.output_dir / "arcgis_documented_balance.csv"
        documented_erf = paths.output_dir / "arcgis_documented_erf_curve.csv"
        documented["analysis_frame"].to_csv(documented_analysis, index=False)
        documented["matching_grid"].to_csv(documented_matching_grid, index=False)
        documented["balance_table"].to_csv(documented_balance, index=False)
        documented["erf_curve"].to_csv(documented_erf, index=False)
        documented["erf_curve"].to_csv(paths.erf_curve, index=False)
        arcgis_documented_files = {
            "arcgis_documented_analysis": documented_analysis.name,
            "arcgis_documented_matching_grid": documented_matching_grid.name,
            "arcgis_documented_balance": documented_balance.name,
            "arcgis_documented_erf_curve": documented_erf.name,
        }
        erf_curve = documented["erf_curve"]
        erf = _erf_summary(erf_curve, extra=documented["erf_summary"])
        arcgis_algorithm_summary = {
            "arcgis_mode": documented["arcgis_mode"],
            "matching": documented["matching_summary"],
            "balance": documented["balance_summary"],
            "erf": documented["erf_summary"],
        }
    else:
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
        arcgis_algorithm_summary=arcgis_algorithm_summary,
        data_provenance=data_provenance,
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
        arcgis_documented_files=arcgis_documented_files,
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
