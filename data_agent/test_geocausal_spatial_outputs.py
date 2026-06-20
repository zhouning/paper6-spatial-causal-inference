from __future__ import annotations

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
    assert Path(manifest["manifest"]).exists()
    for key in ("gpkg", "geojson", "shp"):
        assert Path(manifest["spatial_files"][key]).exists()
    for key in (
        "erf_curve_png",
        "effect_estimates_png",
        "target_exposure_change_histogram_png",
        "target_exposure_change_map_png",
        "target_exposure_change_map_html",
    ):
        assert Path(manifest["visualizations"][key]).exists()

    spatial_joined = gpd.read_file(Path(manifest["spatial_files"]["geojson"]))
    assert len(spatial_joined) == 3108
