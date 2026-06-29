from __future__ import annotations

import pandas as pd
import pytest


def test_expand_nonattainment_periods_to_county_year():
    from data_agent.experiments.epa_airdata_benchmark import expand_nonattainment_periods

    periods = pd.DataFrame(
        {
            "county_fips": ["01001", "01003"],
            "start_year": [2020, 2021],
            "end_year": [2021, pd.NA],
        }
    )

    result = expand_nonattainment_periods(periods, years=[2020, 2021, 2022])

    status = {
        (row.county_fips, row.year): row.nonattainment
        for row in result.itertuples(index=False)
    }
    assert status[("01001", 2020)] == 1
    assert status[("01001", 2022)] == 0
    assert status[("01003", 2022)] == 1


def test_add_neighbor_exposure_uses_county_adjacency():
    from data_agent.experiments.epa_airdata_benchmark import add_neighbor_exposure

    panel = pd.DataFrame(
        {
            "county_fips": ["01001", "01003", "01005", "01001", "01003", "01005"],
            "year": [2020, 2020, 2020, 2021, 2021, 2021],
            "nonattainment_lag1": [1, 0, 1, 0, 1, 0],
        }
    )
    adjacency = {"01001": ["01003", "01005"], "01003": ["01001"], "01005": ["01001"]}

    result = add_neighbor_exposure(panel, adjacency, exposure_col="nonattainment_lag1")

    row = result[(result["county_fips"] == "01001") & (result["year"] == 2020)].iloc[0]
    assert row["neighbor_nonattainment_lag1"] == pytest.approx(0.5)


def test_prepare_epa_panel_adds_lagged_outcome_and_exposure():
    from data_agent.experiments.epa_airdata_benchmark import prepare_epa_panel

    air = pd.DataFrame(
        {
            "county_fips": ["01001", "01001", "01003", "01003"],
            "year": [2020, 2021, 2020, 2021],
            "pollutant_code": [88101, 88101, 88101, 88101],
            "annual_mean": [9.0, 8.0, 7.0, 7.5],
            "monitor_count": [1, 1, 1, 1],
            "observation_count": [100, 100, 100, 100],
        }
    )
    nonattainment = pd.DataFrame(
        {
            "county_fips": ["01001", "01001", "01003", "01003"],
            "year": [2020, 2021, 2020, 2021],
            "nonattainment": [1, 1, 0, 1],
        }
    )
    centroids = pd.DataFrame(
        {"county_fips": ["01001", "01003"], "x": [-86.6, -86.7], "y": [32.5, 31.9]}
    )

    result = prepare_epa_panel(
        air,
        nonattainment,
        centroids,
        adjacency={"01001": ["01003"], "01003": ["01001"]},
    )

    row = result[(result["county_fips"] == "01001") & (result["year"] == 2021)].iloc[0]
    assert row["county_year_id"] == "01001_2021"
    assert row["baseline_annual_mean"] == pytest.approx(9.0)
    assert row["nonattainment_lag1"] == 1
    assert row["neighbor_nonattainment_lag1"] == 0


def test_make_semisynthetic_scenarios_records_true_effects():
    from data_agent.experiments.epa_airdata_benchmark import make_semisynthetic_scenarios

    panel = pd.DataFrame(
        {
            "county_year_id": ["a_2021", "b_2021", "c_2021", "d_2021"],
            "county_fips": ["a", "b", "c", "d"],
            "year": [2021, 2021, 2021, 2021],
            "annual_mean": [8.0, 7.0, 9.0, 6.0],
            "baseline_annual_mean": [8.5, 7.2, 8.8, 6.1],
            "nonattainment_lag1": [1, 0, 1, 0],
            "neighbor_nonattainment_lag1": [0.0, 0.5, 0.0, 0.5],
            "x": [0.0, 1.0, 0.0, 1.0],
            "y": [0.0, 0.0, 1.0, 1.0],
            "monitor_count": [1, 1, 1, 1],
            "year_index": [0, 0, 0, 0],
        }
    )

    scenarios = make_semisynthetic_scenarios(panel, true_effect=-1.25)

    assert {"stable_known_effect", "spatial_confounding", "spillover"} <= set(scenarios)
    stable = scenarios["stable_known_effect"]
    assert stable.metadata["true_effect"] == pytest.approx(-1.25)
    assert "synthetic_outcome" in stable.frame.columns

def test_summarize_semisynthetic_metrics_uses_each_scenario_error():
    from data_agent.experiments.epa_airdata_benchmark.__main__ import (
        summarize_semisynthetic_metrics,
    )

    records = [
        {"scenario": "stable_known_effect", "effect_estimate": -0.98, "true_effect": -1.0},
        {"scenario": "spatial_confounding", "effect_estimate": -0.60, "true_effect": -1.0},
        {"scenario": "spillover", "effect_estimate": -0.80, "true_effect": -1.0},
    ]

    summary = summarize_semisynthetic_metrics(records)

    assert summary["scenario_count"] == 3
    assert summary["median_absolute_error"] == pytest.approx(0.20)
    assert summary["max_absolute_error"] == pytest.approx(0.40)
    assert summary["scenario_metrics"][0]["absolute_error"] == pytest.approx(0.02)


def test_write_geocausal_config_uses_absolute_paths(tmp_path):
    from data_agent.experiments.epa_airdata_benchmark import write_geocausal_config

    panel_path = tmp_path / "semi_synthetic" / "stable_known_effect.csv"
    output_dir = tmp_path / "scca_run"
    config_path = tmp_path / "epa_policy_structure_semisynthetic.yaml"
    panel_path.parent.mkdir()
    panel_path.write_text("county_year_id,annual_mean\n01001_2020,8.0\n", encoding="utf-8")

    write_geocausal_config(
        panel_path=panel_path,
        output_dir=output_dir,
        config_path=config_path,
    )

    text = config_path.read_text(encoding="utf-8")
    assert f"  path: {panel_path.resolve().as_posix()}" in text
    assert f"  directory: {output_dir.resolve().as_posix()}" in text


def test_make_semisynthetic_scenarios_scales_projected_coordinates():
    from data_agent.experiments.epa_airdata_benchmark import make_semisynthetic_scenarios

    panel = pd.DataFrame(
        {
            "county_year_id": ["a_2021", "b_2021", "c_2021", "d_2021"],
            "county_fips": ["a", "b", "c", "d"],
            "year": [2021, 2021, 2021, 2021],
            "annual_mean": [8.0, 7.0, 9.0, 6.0],
            "baseline_annual_mean": [8.5, 7.2, 8.8, 6.1],
            "nonattainment_lag1": [1, 0, 1, 0],
            "neighbor_nonattainment_lag1": [0.0, 0.5, 0.0, 0.5],
            "x": [1_000_000.0, 2_000_000.0, 1_000_000.0, 2_000_000.0],
            "y": [500_000.0, 500_000.0, 1_500_000.0, 1_500_000.0],
            "monitor_count": [1, 1, 1, 1],
            "year_index": [0, 0, 0, 0],
        }
    )

    scenarios = make_semisynthetic_scenarios(panel, true_effect=-1.0)
    stable = scenarios["stable_known_effect"].frame

    assert stable["synthetic_outcome"].abs().max() < 20
