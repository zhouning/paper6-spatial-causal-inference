from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from data_agent.scca.specs import SCCAPaths
from geocausal.config import load_config
from geocausal.open_gis import write_open_gis_package


def _matching_fixture() -> pd.DataFrame:
    exposure = np.linspace(1.0, 24.0, 24)
    return pd.DataFrame(
        {
            "unit_id": [f"u{i:02d}" for i in range(24)],
            "exposure": exposure,
            "outcome": 20.0 + exposure * 0.25 + np.sin(exposure / 3.0),
            "confounder_a": exposure * 0.8 + np.sin(exposure),
            "confounder_b": 30.0 - exposure * 0.35 + np.cos(exposure / 2.0),
        }
    )


def test_arcgis_style_matching_grid_search_selects_best_count_weight_candidate():
    from geocausal.arcgis_style_matching import arcgis_style_matching_search

    frame = _matching_fixture()

    result = arcgis_style_matching_search(
        frame,
        exposure="exposure",
        confounders=("confounder_a", "confounder_b"),
        num_bins=(3, 4, 6),
        scales=(0.0, 0.5, 1.0),
    )

    assert len(result.weights) == len(frame)
    assert len(result.propensity_scores) == len(frame)
    assert result.grid.shape[0] == 9
    assert result.grid["selected"].sum() == 1
    assert result.selected_num_bins in {3, 4, 6}
    assert result.selected_scale in {0.0, 0.5, 1.0}
    assert result.selected_mean_abs_weighted_correlation == result.grid[
        "mean_abs_weighted_correlation"
    ].min()
    assert result.weights.max() > result.weights.min()
    assert result.weights.sum() == len(frame) * result.selected_num_bins
    assert len(result.calibrated_weights) == len(frame)
    assert result.calibrated_weights.sum() > 0
    assert result.calibrated_mean_abs_weighted_correlation <= result.selected_mean_abs_weighted_correlation
    assert {
        "variable",
        "role",
        "raw_correlation",
        "weighted_correlation",
        "absolute_weighted_correlation",
        "balanced_at_0_1",
    }.issubset(result.balance_summary.columns)


def test_arcgis_style_matching_uses_fast_residual_normal_density(monkeypatch):
    import geocausal.arcgis_style_matching as matching

    calls = {"kde": 0}

    def fail_if_called(*args, **kwargs):
        calls["kde"] += 1
        raise AssertionError("KDE must not run inside ArcGIS-style grid search")

    monkeypatch.setattr(matching, "gaussian_kde", fail_if_called, raising=False)

    result = matching.arcgis_style_matching_search(
        _matching_fixture(),
        exposure="exposure",
        confounders=("confounder_a", "confounder_b"),
        num_bins=(3,),
        scales=(0.8,),
    )

    assert calls["kde"] == 0
    assert result.selected_num_bins == 3
    assert result.selected_scale == 0.8
    assert result.selected_mean_abs_weighted_correlation is not None

def test_open_gis_package_writes_arcgis_style_matching_outputs(tmp_path):
    frame = _matching_fixture()
    (tmp_path / "fixture.csv").write_text(frame.to_csv(index=False), encoding="utf-8")
    config_path = tmp_path / "analysis.yaml"
    config_path.write_text(
        """
case_name: arcgis_style_matching_fixture
input:
  path: fixture.csv
variables:
  unit_id: unit_id
  exposure: exposure
  outcome: outcome
  confounders:
    - confounder_a
    - confounder_b
robustness:
  bootstrap:
    group_column: unit_id
    n_replicates: 3
output:
  directory: results/arcgis_style_matching_fixture
""",
        encoding="utf-8",
    )
    config = load_config(config_path)
    spec = config.to_study_spec()
    paths = SCCAPaths(output_dir=config.resolve_output_dir())
    paths.ensure()
    pd.DataFrame(
        {
            "unit_id": frame["unit_id"],
            "gc_propensity_score": np.linspace(0.1, 0.9, len(frame)),
            "gc_balancing_weight": np.ones(len(frame)),
        }
    ).to_csv(paths.generalized_propensity_scores, index=False)
    pd.DataFrame({"exposure": [1.0, 24.0], "response": [20.0, 26.0]}).to_csv(
        paths.erf_curve,
        index=False,
    )

    summary = write_open_gis_package(
        config=config,
        features=frame,
        spec=spec,
        paths=paths,
        manifest={
            "row_count": len(frame),
            "evidence_grade": "core_support",
            "evidence_grade_reasons": [],
            "result_summary": {},
        },
    )

    package_dir = paths.output_dir / "open_gis_analysis_package"
    joined = pd.read_csv(package_dir / "analysis_joined.csv")
    grid = pd.read_csv(package_dir / "arcgis_style_matching_grid.csv")
    balance = pd.read_csv(package_dir / "arcgis_style_balance_summary.csv")
    calibrated_balance = pd.read_csv(package_dir / "arcgis_style_calibrated_balance_summary.csv")
    run_summary = json.loads((package_dir / "gis_run_summary.json").read_text(encoding="utf-8"))

    assert {
        "gc_arcgis_style_propensity_score",
        "gc_arcgis_style_matching_weight",
        "gc_arcgis_style_calibrated_weight",
    }.issubset(joined.columns)
    assert joined["gc_arcgis_style_matching_weight"].sum() > 0
    assert grid["selected"].sum() == 1
    assert {"confounder_a", "confounder_b"} == set(balance["variable"])
    assert {"confounder_a", "confounder_b"} == set(calibrated_balance["variable"])
    assert summary["generated_files"]["arcgis_style_matching_grid"] == "arcgis_style_matching_grid.csv"
    assert summary["generated_files"]["arcgis_style_calibrated_balance_summary"] == "arcgis_style_calibrated_balance_summary.csv"
    assert run_summary["arcgis_style_matching"]["calibrated_mean_abs_weighted_correlation"] <= run_summary["arcgis_style_matching"]["selected_mean_abs_weighted_correlation"]
    assert run_summary["arcgis_style_matching"]["selected_num_bins"] == int(
        grid.loc[grid["selected"] == 1, "num_bins"].iloc[0]
    )
