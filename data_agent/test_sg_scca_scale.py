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
