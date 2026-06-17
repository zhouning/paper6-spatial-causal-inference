from pathlib import Path

from data_agent.scca.specs import SCCAPaths, StudySpec


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
