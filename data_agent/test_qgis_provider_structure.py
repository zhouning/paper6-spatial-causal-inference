from __future__ import annotations

import importlib
from pathlib import Path
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[1]
PROVIDER_PATH = REPO_ROOT / "qgis_provider" / "geocausal_scca_algorithm.py"
PROVIDER_MODULE_PATH = REPO_ROOT / "qgis_provider" / "provider.py"
PLUGIN_MODULE_PATH = REPO_ROOT / "qgis_provider" / "plugin.py"


def test_qgis_provider_skeleton_exists_and_avoids_case_specific_fields():
    text = PROVIDER_PATH.read_text(encoding="utf-8")
    assert "AnalysisRequest" in text
    assert "build_analysis_joined_table" in text
    assert "run_scca_analysis" in text
    assert "prepare_county_analysis_table_from_shapefile" not in text
    assert "SocialAssoc" not in text
    assert "AveAgeDeath" not in text
    assert "STATE_NAME" not in text
    assert "CountyData" not in text


def test_qgis_provider_skeleton_imports_without_qgis_runtime():
    module = importlib.import_module("qgis_provider.geocausal_scca_algorithm")

    assert hasattr(module, "GeoCausalSCCAAlgorithm")
    assert module.GeoCausalSCCAAlgorithm.PARAM_EXPOSURE == "EXPOSURE_FIELD"
    assert module.GeoCausalSCCAAlgorithm.PARAM_OUTCOME == "OUTCOME_FIELD"
    assert module.GeoCausalSCCAAlgorithm.PARAM_OUTPUT_JOINED == "OUTPUT_ANALYSIS_TABLE"


def test_qgis_provider_facade_exists_and_avoids_case_specific_fields():
    text = PROVIDER_MODULE_PATH.read_text(encoding="utf-8")
    assert "GeoCausalProviderSkeleton" in text
    assert "SocialAssoc" not in text
    assert "AveAgeDeath" not in text
    assert "STATE_NAME" not in text


def test_qgis_plugin_entrypoint_imports_without_qgis_runtime():
    module = importlib.import_module("qgis_provider.plugin")
    assert hasattr(module, "GeoCausalPlugin")
    assert hasattr(module, "classFactory")


def test_qgis_provider_factory_returns_runtime_light_provider_without_qgis():
    module = importlib.import_module("qgis_provider.provider")
    provider = module.create_qgis_provider()
    assert provider.id() == "geocausal"
    assert provider.name() == "GeoCausal"


def test_qgis_algorithm_runs_from_parameter_dict(tmp_path):
    module = importlib.import_module("qgis_provider.geocausal_scca_algorithm")
    algorithm = module.GeoCausalSCCAAlgorithm()
    output_root = tmp_path / "results"
    parameters = {
        algorithm.PARAM_INPUT: str(REPO_ROOT / "examples" / "data" / "county_social_capital.csv"),
        algorithm.PARAM_CASE_NAME: "county_social_capital_qgis_test",
        algorithm.PARAM_UNIT_ID: "FIPS",
        algorithm.PARAM_EXPOSURE: "SocialAssoc",
        algorithm.PARAM_OUTCOME: "AveAgeDeath",
        algorithm.PARAM_CONFOUNDERS: "UnemployRate,pHHinPoverty,pNoHealthInsur",
        algorithm.PARAM_CONTEXT: "Shape_Length,Shape_Area",
        algorithm.PARAM_BOOTSTRAP_GROUP: "STATE_NAME",
        algorithm.PARAM_PLACEBO: "Shape_Length,Shape_Area",
        algorithm.PARAM_LOWER_Q: 0.01,
        algorithm.PARAM_UPPER_Q: 0.99,
        algorithm.PARAM_TARGET_OUTCOMES: "70",
        algorithm.PARAM_BOOTSTRAP_REPS: 10,
        algorithm.PARAM_OUTPUT_FOLDER: str(output_root),
    }

    manifest = algorithm.run_from_parameters(parameters)

    case_dir = output_root / "county_social_capital_qgis_test"
    assert manifest["case_name"] == "county_social_capital_qgis_test"
    assert (case_dir / "manifest.json").exists()
    assert (case_dir / "analysis_joined.csv").exists()
    assert manifest["files"]["result_summary_markdown"] == "result_summary.md"
    assert (case_dir / "result_summary.md").exists()


def test_qgis_open_gis_output_mapping_uses_manifest_package_files(tmp_path):
    module = importlib.import_module("qgis_provider.geocausal_scca_algorithm")
    algorithm = module.GeoCausalSCCAAlgorithm()
    case_dir = tmp_path / "case"
    manifest = {
        "open_gis_package": {
            "package_dir": "open_gis_analysis_package",
            "generated_files": {
                "analysis_joined": "analysis_joined.csv",
                "gis_balance_summary": "gis_balance_summary.csv",
                "gis_erf_curve_200": "gis_erf_curve_200.csv",
                "arcgis_style_matching_grid": "arcgis_style_matching_grid.csv",
                "arcgis_style_balance_summary": "arcgis_style_balance_summary.csv",
                "arcgis_style_calibrated_balance_summary": "arcgis_style_calibrated_balance_summary.csv",
                "gis_run_summary_json": "gis_run_summary.json",
                "gis_run_summary_markdown": "gis_run_summary.md",
            },
        }
    }

    outputs = algorithm.open_gis_package_outputs(case_dir, manifest)

    package_dir = case_dir / "open_gis_analysis_package"
    assert outputs[algorithm.OUTPUT_OPEN_GIS_PACKAGE] == str(package_dir)
    assert outputs[algorithm.OUTPUT_OPEN_GIS_JOINED] == str(package_dir / "analysis_joined.csv")
    assert outputs[algorithm.OUTPUT_OPEN_GIS_BALANCE] == str(package_dir / "gis_balance_summary.csv")
    assert outputs[algorithm.OUTPUT_OPEN_GIS_ERF_200] == str(package_dir / "gis_erf_curve_200.csv")
    assert outputs[algorithm.OUTPUT_OPEN_GIS_ARCGIS_STYLE_GRID] == str(package_dir / "arcgis_style_matching_grid.csv")
    assert outputs[algorithm.OUTPUT_OPEN_GIS_ARCGIS_STYLE_BALANCE] == str(package_dir / "arcgis_style_balance_summary.csv")
    assert outputs[algorithm.OUTPUT_OPEN_GIS_ARCGIS_STYLE_CALIBRATED_BALANCE] == str(package_dir / "arcgis_style_calibrated_balance_summary.csv")
    assert outputs[algorithm.OUTPUT_OPEN_GIS_SUMMARY_JSON] == str(package_dir / "gis_run_summary.json")
    assert outputs[algorithm.OUTPUT_OPEN_GIS_SUMMARY_MD] == str(package_dir / "gis_run_summary.md")

def test_qgis_required_fields_preserve_order_and_uniqueness():
    module = importlib.import_module("qgis_provider.geocausal_scca_algorithm")
    request = module.QGISRunRequest(
        case_name="test",
        input_csv=Path("input.csv"),
        output_dir=Path("out"),
        unit_id_field="FIPS",
        exposure_field="SocialAssoc",
        outcome_field="AveAgeDeath",
        confounder_fields=("FIPS", "UnemployRate"),
        context_fields=("Shape_Length",),
        coordinate_fields=("Shape_Length", "Shape_Area"),
        bootstrap_group_field="STATE_NAME",
    )

    assert module.GeoCausalSCCAAlgorithm.required_fields_for_request(request) == (
        "FIPS",
        "SocialAssoc",
        "AveAgeDeath",
        "STATE_NAME",
        "UnemployRate",
        "Shape_Length",
        "Shape_Area",
    )


class _FakeField:
    def __init__(self, name):
        self._name = name

    def name(self):
        return self._name


class _FakeFeature:
    def __init__(self, values):
        self._values = values

    def attribute(self, field):
        return self._values[field]

    def hasGeometry(self):
        return False


class _FakeSource:
    def __init__(self, rows):
        self._rows = rows

    def fields(self):
        return [_FakeField(name) for name in self._rows[0]]

    def getFeatures(self):
        return [_FakeFeature(row) for row in self._rows]


def test_qgis_source_export_writes_selected_fields_without_qgis_runtime(tmp_path):
    module = importlib.import_module("qgis_provider.geocausal_scca_algorithm")
    output_csv = tmp_path / "input.csv"

    module.GeoCausalSCCAAlgorithm.export_qgis_source_to_csv(
        _FakeSource(
            [
                {"FIPS": "01001", "SocialAssoc": 12.3, "AveAgeDeath": 71.0},
                {"FIPS": "01003", "SocialAssoc": 10.0, "AveAgeDeath": 70.5},
            ]
        ),
        output_csv,
        selected_fields=("FIPS", "SocialAssoc", "AveAgeDeath"),
        derive_coordinates=False,
    )

    text = output_csv.read_text(encoding="utf-8-sig")
    assert text.splitlines()[0] == "FIPS,SocialAssoc,AveAgeDeath"
    assert "01001,12.3,71.0" in text
