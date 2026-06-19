import pandas as pd
import pytest

from geocausal.config import load_config
from geocausal.errors import GeoCausalInputError
from geocausal.io import load_dataset


def _write_config(tmp_path, input_block: str):
    path = tmp_path / "analysis.yaml"
    path.write_text(
        f"""
case_name: io_case
input:
{input_block}
variables:
  exposure: exposure
  outcome: outcome
output:
  directory: results/io
""",
        encoding="utf-8",
    )
    return load_config(path)


def test_load_dataset_csv_adds_default_unit_id(tmp_path):
    csv_path = tmp_path / "fixture.csv"
    pd.DataFrame(
        {
            "x": [0.0, 1.0],
            "y": [2.0, 3.0],
            "exposure": [0.1, 0.2],
            "outcome": [5.0, 6.0],
        }
    ).to_csv(csv_path, index=False)
    config = _write_config(
        tmp_path,
        f"""
  path: {csv_path.name}
  x: x
  y: y
""",
    )
    loaded = load_dataset(config)
    assert list(loaded.frame["_gc_unit_id"]) == ["1", "2"]
    assert loaded.geometry_available is False
    assert loaded.columns == {"_gc_unit_id", "x", "y", "exposure", "outcome"}


def test_load_dataset_geojson_preserves_geometry(tmp_path):
    geopandas = pytest.importorskip("geopandas")
    from shapely.geometry import Point

    geojson_path = tmp_path / "fixture.geojson"
    gdf = geopandas.GeoDataFrame(
        {"exposure": [1.0, 2.0], "outcome": [3.0, 5.0]},
        geometry=[Point(0, 0), Point(1, 1)],
        crs="EPSG:4326",
    )
    gdf.to_file(geojson_path, driver="GeoJSON")
    config = _write_config(
        tmp_path,
        f"""
  path: {geojson_path.name}
""",
    )
    loaded = load_dataset(config)
    assert loaded.geometry_available is True
    assert "_gc_unit_id" in loaded.frame.columns
    assert loaded.frame.crs.to_string() == "EPSG:4326"


def test_load_dataset_rejects_missing_input_file(tmp_path):
    config = _write_config(
        tmp_path,
        """
  path: missing.csv
  x: x
  y: y
""",
    )
    with pytest.raises(GeoCausalInputError, match="Input file does not exist"):
        load_dataset(config)
