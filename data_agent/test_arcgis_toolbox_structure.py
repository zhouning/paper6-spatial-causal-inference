from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from arcgis_toolbox.geocausal_arcgis_support import (
    build_analysis_joined_table,
    split_arcgis_output_table_path,
    summarize_manifest_messages,
    validate_requested_fields,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLBOX_PATH = REPO_ROOT / "arcgis_toolbox" / "GeoCausalSCCA.pyt"


def _load_toolbox_module():
    loader = importlib.machinery.SourceFileLoader("geocausal_arcgis_toolbox", str(TOOLBOX_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_toolbox_file_exists_and_avoids_case_specific_field_names():
    text = TOOLBOX_PATH.read_text(encoding="utf-8")
    assert "GeoCausal SCCA Analysis" in text
    assert "AnalysisRequest" in text
    assert "output_analysis_table" in text
    assert "DEFAULT_OUTPUT_FOLDER" in text
    assert "SocialAssoc" not in text
    assert "AveAgeDeath" not in text
    assert "STATE_NAME" not in text
    assert "CountyData" not in text


def test_toolbox_module_exposes_expected_classes():
    module = _load_toolbox_module()
    assert hasattr(module, "Toolbox")
    assert hasattr(module, "GeoCausalSCCATool")
    toolbox = module.Toolbox()
    assert toolbox.alias == "geocausal_scca"
    assert toolbox.tools == [module.GeoCausalSCCATool]


def test_build_analysis_joined_table_pivots_generic_target_results(tmp_path):
    input_csv = tmp_path / "input.csv"
    target_csv = tmp_path / "target_exposures.csv"
    output_csv = tmp_path / "analysis_joined.csv"
    pd.DataFrame(
        {
            "sample_key": ["a", "b", "c"],
            "dose": [1.0, 2.0, 3.0],
            "response": [10.0, 12.0, 14.0],
        }
    ).to_csv(input_csv, index=False)
    pd.DataFrame(
        {
            "unit_id": ["a", "b", "a", "b"],
            "method": [
                "erf_delta_anchor",
                "erf_delta_anchor",
                "adjusted_ols_prediction",
                "adjusted_ols_prediction",
            ],
            "target_name": ["target_20", "target_20", "target_20", "target_20"],
            "target_outcome": [20.0, 20.0, 20.0, 20.0],
            "required_exposure": [5.5, 6.5, 5.0, 6.0],
            "exposure_change": [4.5, 4.5, 4.0, 4.0],
            "status": ["ok", "outside_erf_support", "ok", "ok"],
            "warning": ["", "outside support", "", ""],
        }
    ).to_csv(target_csv, index=False)

    result = build_analysis_joined_table(
        input_csv=input_csv,
        target_exposures_csv=target_csv,
        output_csv=output_csv,
        unit_id_field="sample_key",
        method="erf_delta_anchor",
    )

    assert result == output_csv
    joined = pd.read_csv(output_csv)
    assert list(joined["sample_key"]) == ["a", "b", "c"]
    assert "dose" in joined.columns
    assert "gc_target_20_required_exposure" in joined.columns
    assert "gc_target_20_exposure_change" in joined.columns
    assert "gc_target_20_status" in joined.columns
    assert joined.loc[joined["sample_key"] == "a", "gc_target_20_required_exposure"].iloc[0] == 5.5
    assert joined.loc[joined["sample_key"] == "b", "gc_target_20_status"].iloc[0] == "outside_erf_support"
    assert pd.isna(joined.loc[joined["sample_key"] == "c", "gc_target_20_required_exposure"].iloc[0])


def test_split_arcgis_output_table_path_supports_file_geodatabase_targets():
    out_path, out_name = split_arcgis_output_table_path(
        r"C:\analysis\outputs.gdb\joined_results"
    )
    assert out_path == r"C:\analysis\outputs.gdb"
    assert out_name == "joined_results"


def test_validate_requested_fields_reports_missing_fields_clearly():
    available_fields = ("unit_id", "exposure", "outcome", "shape_x", "shape_y")

    try:
        validate_requested_fields(
            requested_fields=("unit_id", "baseline", "outcome"),
            available_fields=available_fields,
            x_field="shape_x",
            y_field="missing_y",
        )
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected validate_requested_fields() to raise ValueError.")

    assert "baseline" in message
    assert "missing_y" in message
    assert "Available fields" in message


def test_summarize_manifest_messages_includes_spatial_diagnostics_and_result_summary():
    manifest = {
        "case_name": "county_demo",
        "row_count": 3044,
        "exposure": "SocialAssoc",
        "outcome": "AveAgeDeath",
        "credibility_decision": "moderate_support",
        "robustness_interpretation": "bounded_support",
        "preprocessing": {"exposure_trim": {"removed_n": 64}},
        "files": {
            "target_exposures": "target_exposures.csv",
            "spatial_diagnostics": "spatial_diagnostics.json",
            "result_summary_markdown": "result_summary.md",
        },
        "result_summary": {
            "spatial_diagnostics": {
                "graph_method": "coordinate_knn",
                "edge_count": 7019,
                "exposure_moran_i": 0.5173518878,
                "residual_moran_i": 0.3127560212,
            },
            "spatial_slx_model": {
                "status": "ok",
                "total_effect": 0.2145094523,
                "total_p_value": 1.8e-57,
            },
        },
    }

    messages = summarize_manifest_messages(manifest)

    assert any("Spatial diagnostics:" in line for line in messages)
    assert any("coordinate_knn" in line for line in messages)
    assert any("SLX total effect:" in line for line in messages)
    assert any("Result summary:" in line for line in messages)


def test_export_input_dataset_preserves_manual_coordinate_fields(tmp_path, monkeypatch):
    import arcgis_toolbox.geocausal_arcgis_support as support

    class FakeSearchCursor:
        def __init__(self, input_dataset, fields):
            self.fields = list(fields)

        def __enter__(self):
            return iter([("a", 1.0, 10.0, -120.5, 35.2)])

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_arcpy = SimpleNamespace(
        ListFields=lambda input_dataset: [
            SimpleNamespace(name="unit_id"),
            SimpleNamespace(name="exposure"),
            SimpleNamespace(name="outcome"),
            SimpleNamespace(name="x_coord"),
            SimpleNamespace(name="y_coord"),
        ],
        Describe=lambda input_dataset: SimpleNamespace(shapeType="Polygon"),
        da=SimpleNamespace(SearchCursor=FakeSearchCursor),
    )
    monkeypatch.setitem(sys.modules, "arcpy", fake_arcpy)

    output_csv = tmp_path / "input.csv"
    summary = support.export_input_dataset(
        "fake_layer",
        output_csv,
        fields=("unit_id", "exposure", "outcome"),
        x_field="x_coord",
        y_field="y_coord",
    )

    exported = pd.read_csv(output_csv)
    assert list(exported.columns) == ["unit_id", "exposure", "outcome", "x_coord", "y_coord"]
    assert summary["coordinate_columns"] == ("x_coord", "y_coord")
    assert summary["derived_coordinates"] is False
