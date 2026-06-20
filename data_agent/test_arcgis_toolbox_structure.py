from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

import pandas as pd

from arcgis_toolbox.geocausal_arcgis_support import (
    build_analysis_joined_table,
    split_arcgis_output_table_path,
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
