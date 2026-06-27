from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

from geocausal.spatial_outputs import (
    COUNTY_ANALYSIS_COLUMNS,
    build_spatial_analysis_outputs,
    prepare_county_analysis_table_from_shapefile,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
COUNTY_PATH = REPO_ROOT / "data" / "CountyData.shp"
STATES_PATH = REPO_ROOT / "data" / "States.shp"


def test_prepare_county_analysis_table_from_shapefile_restores_expected_fields(tmp_path):
    output_csv = tmp_path / "county_analysis_input.csv"
    result = prepare_county_analysis_table_from_shapefile(
        county_path=COUNTY_PATH,
        output_csv=output_csv,
    )

    assert result == output_csv
    frame = pd.read_csv(output_csv, dtype={"FIPS": "string"})
    assert list(frame.columns) == list(COUNTY_ANALYSIS_COLUMNS)
    assert frame["FIPS"].iloc[0] == "01001"
    assert frame["_gc_x"].notna().all()
    assert frame["_gc_y"].notna().all()
    assert len(frame) == 3108


def test_build_spatial_analysis_outputs_writes_spatial_files_and_visuals(tmp_path):
    analysis_dir = tmp_path / "analysis_case"
    analysis_dir.mkdir(parents=True)
    analysis_joined_csv = analysis_dir / "analysis_joined.csv"
    pd.DataFrame(
        {
            "FIPS": ["01001", "01003", "01005"],
            "gc_target_70_required_exposure": [11.5, 1.83, 1.83],
            "gc_target_70_exposure_change": [-1.1, -8.9, -6.6],
            "gc_target_70_status": ["ok", "outside_erf_support", "outside_erf_support"],
        }
    ).to_csv(analysis_joined_csv, index=False, encoding="utf-8-sig")
    pd.DataFrame(
        {
            "estimator": ["baseline_adjusted_ols", "generalized_propensity_erf"],
            "coef": [0.18, 6.84],
            "ci_lower": [0.16, None],
            "ci_upper": [0.20, None],
        }
    ).to_csv(analysis_dir / "effect_estimates.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        {
            "exposure": [1.8, 8.0, 14.0],
            "response": [74.2, 75.5, 76.8],
        }
    ).to_csv(analysis_dir / "erf_curve.csv", index=False, encoding="utf-8-sig")
    (analysis_dir / "spatial_slx_summary.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "model": "SLX",
                "direct_effect": 0.14,
                "direct_ci_lower": 0.10,
                "direct_ci_upper": 0.18,
                "indirect_effect": 0.07,
                "indirect_ci_lower": 0.03,
                "indirect_ci_upper": 0.11,
                "total_effect": 0.21,
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "unit_id": ["01001", "01003", "01005"],
            "direct_effect": [0.14, 0.14, 0.14],
            "indirect_effect": [0.06, 0.07, 0.08],
            "total_effect": [0.20, 0.21, 0.22],
            "out_neighbor_count": [4, 5, 3],
            "incoming_weight_sum": [0.9, 1.0, 1.1],
        }
    ).to_csv(analysis_dir / "spatial_exposure_mapping.csv", index=False, encoding="utf-8-sig")

    output_dir = tmp_path / "spatial_outputs"
    manifest = build_spatial_analysis_outputs(
        boundary_path=COUNTY_PATH,
        analysis_joined_csv=analysis_joined_csv,
        analysis_dir=analysis_dir,
        output_dir=output_dir,
        states_path=STATES_PATH,
        output_stem="county_analysis_smoke",
    )

    assert manifest["row_count"] == 3108
    assert manifest["matched_count"] == 3
    assert "gc_spatial_indirect_effect" in manifest["enriched_effect_fields"]
    assert Path(manifest["manifest"]).exists()
    for key in ("gpkg", "geojson", "shp"):
        assert Path(manifest["spatial_files"][key]).exists()
    for key in (
        "erf_curve_png",
        "effect_estimates_png",
        "spatial_slx_effects_png",
        "target_exposure_change_histogram_png",
        "target_exposure_change_map_png",
        "target_exposure_change_map_html",
        "spatial_indirect_effect_map_png",
        "spatial_indirect_effect_map_html",
    ):
        assert Path(manifest["visualizations"][key]).exists()
    for key in (
        "target_exposure_change_qml",
        "spatial_indirect_effect_qml",
        "spatial_total_effect_qml",
    ):
        assert Path(manifest["qgis_styles"][key]).exists()

    spatial_joined = gpd.read_file(Path(manifest["spatial_files"]["geojson"]))
    assert len(spatial_joined) == 3108
    assert "gc_spatial_indirect_effect" in spatial_joined.columns
    assert spatial_joined["gc_spatial_indirect_effect"].notna().sum() == 3
    qml_text = Path(manifest["qgis_styles"]["spatial_indirect_effect_qml"]).read_text(encoding="utf-8")
    assert "gc_spatial_indirect_effect" in qml_text

    report_path = Path(manifest["open_report"])
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "GeoCausal Open Spatial Report" in report_text
    assert "Matched analysis units" in report_text
    assert "county_analysis_smoke.gpkg" in report_text
    assert "target_exposure_change_map.html" in report_text
