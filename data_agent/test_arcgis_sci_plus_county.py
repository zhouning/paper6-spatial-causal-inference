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
    assert (output_dir / "arcgis_sci_plus_report.json").exists()
    report = json.loads(
        (output_dir / "arcgis_sci_plus_report.json").read_text(encoding="utf-8")
    )
    assert report["arcgis_sci_parity"]["removed_rows"] == 2
    assert "geo_causal_extensions" in report
