import json

import pandas as pd

from data_agent.experiments.run_arcgis_sci_plus_county import (
    run_arcgis_sci_plus_county,
)


def _county_fixture():
    rows = []
    for i in range(100):
        rows.append(
            {
                "FIPS": 1000 + i,
                "STATE_NAME": f"S{i // 20}",
                "AveAgeDeath": 65.0 + 0.08 * i,
                "SocialAssoc": float(i),
                "UnemployRate": 3.0 + (i % 5),
                "pHHinPoverty": 10.0 + (i % 7),
                "pNoHealthInsur": 8.0 + (i % 4),
                "MentalHealth": 4.0 + (i % 3),
                "pAdultSmoking": 15.0 + (i % 6),
                "pAdultObesity": 30.0 + (i % 5),
                "FastFood": 2.0 + (i % 4),
                "pInsufficientSleep": 31.0 + (i % 4),
                "pAlcohol": 4.0 + (i % 6),
                "pSuicideDeaths": 10.0 + (i % 5),
                "AirPollution": 7.0 + (i % 4),
                "Shape_Length": 100000.0 + i,
                "Shape_Area": 1.0e9 + i,
            }
        )
    return pd.DataFrame(rows)


def test_run_arcgis_sci_plus_county_writes_manifest(tmp_path):
    workbook = tmp_path / "county.xlsx"
    _county_fixture().to_excel(workbook, sheet_name="CountyData", index=False)
    output_dir = tmp_path / "out"

    manifest = run_arcgis_sci_plus_county(workbook, output_dir=output_dir)

    assert manifest["study"] == "county_social_capital_longevity_validation"
    assert manifest["arcgis_sci_plus_report"] == "arcgis_sci_plus_report.json"
    assert manifest["source_workbook"] == workbook.name
    assert manifest["sheet_name"] == "CountyData"
    assert manifest["input_rows"] == 100
    assert manifest["input_columns"] == 17
    assert manifest["generated_at_utc"]
    assert manifest["source_sha256"]
    assert (output_dir / "arcgis_sci_plus_report.json").exists()
    report = json.loads(
        (output_dir / "arcgis_sci_plus_report.json").read_text(encoding="utf-8")
    )
    assert report["arcgis_sci_parity"]["removed_rows"] == 2
    assert report["arcgis_sci_parity"]["algorithm"]["arcgis_mode"] == "continuous_regression_matching_plugin_erf"
    assert report["arcgis_sci_parity"]["algorithm"]["matching"]["ps_method"] == "REGRESSION"
    assert report["arcgis_sci_parity"]["erf"]["n_grid"] == 200
    assert "arcgis_documented_matching_grid" in manifest["files"]
    assert (output_dir / manifest["files"]["arcgis_documented_matching_grid"]).exists()
    assert (output_dir / manifest["files"]["arcgis_documented_balance"]).exists()
    assert (output_dir / manifest["files"]["arcgis_documented_analysis"]).exists()
    assert "county_variable_provenance" in manifest["files"]
    provenance = pd.read_csv(output_dir / manifest["files"]["county_variable_provenance"])
    assert set(provenance["field"]) >= {
        "SocialAssoc",
        "AveAgeDeath",
        "FastFood",
        "UnemployRate",
    }
    source_by_field = provenance.set_index("field")["source_group"].to_dict()
    assert source_by_field["SocialAssoc"] == "County Health Rankings 2019 / ArcGIS Living Atlas"
    assert source_by_field["AveAgeDeath"] == "CDC WONDER Underlying Cause of Death"
    assert source_by_field["FastFood"] == "ArcGIS Pro Enrich / Esri"
    assert "lineage_only" in provenance.set_index("field").loc["UnemployRate", "source_confidence"]
    assert report["data_provenance"]["status"] == "ok"
    assert report["data_provenance"]["file"] == "county_variable_provenance.csv"
    assert report["data_provenance"]["field_count"] >= 17
    assert report["data_provenance"]["unresolved_fields"] == ["UnemployRate"]
    assert "geo_causal_extensions" in report
    spatial_risk = report["geo_causal_extensions"]["spatial_risk"]
    assert spatial_risk["status"] == "unavailable"
    assert spatial_risk["reason"] == "missing_coordinates_or_geometry"


def test_run_arcgis_sci_plus_county_skips_missing_exposure(tmp_path):
    workbook = tmp_path / "county_missing_exposure.xlsx"
    _county_fixture().drop(columns=["SocialAssoc"]).to_excel(
        workbook, sheet_name="CountyData", index=False
    )
    output_dir = tmp_path / "out"

    manifest = run_arcgis_sci_plus_county(workbook, output_dir=output_dir)

    assert manifest["status"] == "skipped"
    assert (output_dir / "arcgis_sci_plus_report.json").exists()
    report = json.loads(
        (output_dir / "arcgis_sci_plus_report.json").read_text(encoding="utf-8")
    )
    assert report["arcgis_sci_parity"]["status"] == "skipped"
    assert not (output_dir / "effect_estimates.csv").exists()


def test_run_arcgis_sci_plus_county_skips_nonfinite_exposure(tmp_path):
    workbook = tmp_path / "county_nonfinite_exposure.xlsx"
    fixture = _county_fixture()
    fixture["SocialAssoc"] = None
    fixture.to_excel(workbook, sheet_name="CountyData", index=False)
    output_dir = tmp_path / "out"

    manifest = run_arcgis_sci_plus_county(workbook, output_dir=output_dir)

    assert manifest["status"] == "skipped"
    report = json.loads(
        (output_dir / "arcgis_sci_plus_report.json").read_text(encoding="utf-8")
    )
    assert report["arcgis_sci_parity"]["status"] == "skipped"
    assert not (output_dir / "effect_estimates.csv").exists()
