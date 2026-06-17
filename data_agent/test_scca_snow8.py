from pathlib import Path
import json

import pandas as pd

from data_agent.scca.specs import SCCAPaths, StudySpec
from data_agent.scca.profiling import load_table, profile_table


def test_study_spec_snow8_defaults():
    spec = StudySpec.snow8_default()
    assert spec.unit_id == "sub_ID"
    assert spec.exposure == "perc_sou"
    assert spec.outcome == "rate1854"
    assert spec.baseline_outcome == "rate1849"
    assert "pop_house" in spec.confounders
    assert "d_thames" in spec.context_columns


def test_scca_paths_create_expected_output_dir(tmp_path):
    paths = SCCAPaths(output_dir=tmp_path / "scca_snow8")
    paths.ensure()
    assert paths.output_dir.exists()
    assert paths.data_profile.name == "data_profile.json"
    assert paths.effect_estimates.name == "effect_estimates.csv"


def _snow8_like_frame():
    return pd.DataFrame(
        {
            "sub_ID": ["1", "2", "3"],
            "district": ["A", "A", "B"],
            "perc_sou": [1.0, 0.5, 0.0],
            "rate1854": [180.0, 120.0, 60.0],
            "rate1849": [130.0, 100.0, 70.0],
            "pop_house": [6.5, 7.1, 5.9],
            "pop1851": [10000, 8000, 7000],
            "d_thames": [20.0, 30.0, 10.0],
        }
    )


def test_load_table_reads_csv_with_utf8_sig(tmp_path):
    path = tmp_path / "snow8.csv"
    _snow8_like_frame().to_csv(path, index=False, encoding="utf-8-sig")
    loaded = load_table(path)
    assert loaded.shape == (3, 8)
    assert loaded["perc_sou"].dtype.kind in {"f", "i"}


def test_profile_table_writes_json_and_candidates(tmp_path):
    df = _snow8_like_frame()
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    profile = profile_table(df, StudySpec.snow8_default(), paths)
    assert profile["n_rows"] == 3
    assert profile["columns"]["perc_sou"]["role"] == "exposure"
    assert profile["columns"]["rate1854"]["role"] == "outcome"
    assert paths.data_profile.exists()
    assert paths.variable_candidates.exists()
    saved = json.loads(paths.data_profile.read_text(encoding="utf-8"))
    assert saved["n_columns"] == 8
