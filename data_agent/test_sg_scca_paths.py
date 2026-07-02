from pathlib import Path

from data_agent.scca.specs import SCCAPaths, StudySpec


def test_study_spec_accepts_scale_support_metadata():
    spec = StudySpec(
        name="scale_fixture",
        unit_id="building_id",
        exposure="high_rise",
        outcome="lst",
        treatment_support="building",
        outcome_support="modis_pixel",
        aggregation_group="pixel_id",
    )

    assert spec.treatment_support == "building"
    assert spec.outcome_support == "modis_pixel"
    assert spec.aggregation_group == "pixel_id"


def test_scca_paths_include_sg_scca_outputs(tmp_path):
    paths = SCCAPaths(output_dir=Path(tmp_path))

    assert paths.scale_summary.name == "scale_summary.json"
    assert paths.sg_scca_diagnostics.name == "sg_scca_diagnostics.json"
    assert paths.sg_scca_effect_estimates.name == "sg_scca_effect_estimates.csv"
    assert paths.sg_scca_bias_bound.name == "sg_scca_bias_bound.json"
