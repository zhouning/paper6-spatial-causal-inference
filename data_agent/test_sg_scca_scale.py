import json

import pandas as pd

from data_agent.scca.scale import build_scale_summary, aggregate_to_outcome_support
from data_agent.scca.specs import SCCAPaths, StudySpec


def test_build_scale_summary_marks_same_support(tmp_path):
    spec = StudySpec(name="same", unit_id="id", exposure="t", outcome="y")
    paths = SCCAPaths(output_dir=tmp_path)

    summary = build_scale_summary(pd.DataFrame({"id": [1, 2], "t": [0, 1], "y": [3, 4]}), spec, paths)

    assert summary["scale_status"] == "same_support"
    assert summary["aggregation_group"] is None
    assert json.loads(paths.scale_summary.read_text(encoding="utf-8")) == summary


def test_aggregate_to_outcome_support_uses_group_means():
    frame = pd.DataFrame(
        {
            "building_id": ["a", "b", "c", "d"],
            "pixel_id": ["p1", "p1", "p2", "p2"],
            "high_rise": [1.0, 0.0, 1.0, 1.0],
            "lst": [30.0, 30.0, 32.0, 32.0],
            "elevation": [100.0, 120.0, 200.0, 220.0],
            "ndvi": [0.20, 0.30, 0.40, 0.50],
        }
    )
    spec = StudySpec(
        name="change_support",
        unit_id="building_id",
        exposure="high_rise",
        outcome="lst",
        context_columns=("ndvi",),
        confounders=("elevation",),
        treatment_support="building",
        outcome_support="modis_pixel",
        aggregation_group="pixel_id",
    )

    aggregated, summary = aggregate_to_outcome_support(frame, spec)

    assert list(aggregated["pixel_id"]) == ["p1", "p2"]
    assert list(aggregated["n_fine_units"]) == [2, 2]
    assert aggregated.loc[aggregated["pixel_id"] == "p1", "high_rise"].iloc[0] == 0.5
    assert aggregated.loc[aggregated["pixel_id"] == "p2", "elevation"].iloc[0] == 210.0
    assert summary["scale_status"] == "change_of_support"
    assert summary["fine_units"] == 4
    assert summary["outcome_units"] == 2


def test_aggregate_to_outcome_support_reports_numeric_coercion_warnings():
    frame = pd.DataFrame(
        {
            "building_id": ["a", "b"],
            "pixel_id": ["p1", "p1"],
            "high_rise": ["yes", 1.0],
            "lst": [30.0, 31.0],
        }
    )
    spec = StudySpec(
        name="coercion_warning",
        unit_id="building_id",
        exposure="high_rise",
        outcome="lst",
        treatment_support="building",
        outcome_support="modis_pixel",
        aggregation_group="pixel_id",
    )

    _, summary = aggregate_to_outcome_support(frame, spec)

    assert "Column high_rise has 1 missing value(s) after numeric coercion." in summary["warnings"]


def test_build_scale_summary_empty_change_support_matches_persisted_json(tmp_path):
    frame = pd.DataFrame(
        {
            "pixel_id": pd.Series(dtype="object"),
            "high_rise": pd.Series(dtype="float64"),
            "lst": pd.Series(dtype="float64"),
        }
    )
    spec = StudySpec(
        name="empty_change_support",
        unit_id="building_id",
        exposure="high_rise",
        outcome="lst",
        treatment_support="building",
        outcome_support="modis_pixel",
        aggregation_group="pixel_id",
    )
    paths = SCCAPaths(output_dir=tmp_path)

    summary = build_scale_summary(frame, spec, paths)

    assert summary == json.loads(paths.scale_summary.read_text(encoding="utf-8"))
    assert summary["outcome_units"] == 0
    assert summary["mean_fine_units_per_outcome"] is None
