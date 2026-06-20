import json
from pathlib import Path

import pandas as pd


def test_build_offline_fixture_panel_has_expected_contract():
    from data_agent.experiments.world_model_holdout_validation import (
        build_offline_fixture_panel,
    )

    panel = build_offline_fixture_panel(
        random_state=0,
        n_pixels_per_area=8,
        years=(2019, 2020, 2021, 2022),
    )

    required = {"area", "split", "pixel_id", "year", "lulc_label"}
    required.update({f"A{i:02d}" for i in range(64)})
    assert required.issubset(panel.columns)
    assert set(panel["split"]) >= {"Train", "Val", "Test", "OOD"}
    assert panel["pixel_id"].nunique() > 0
    assert panel["year"].nunique() == 4


def test_build_transition_pairs_separates_train_and_holdout_rows():
    from data_agent.experiments.world_model_holdout_validation import (
        build_offline_fixture_panel,
        build_transition_pairs,
    )

    panel = build_offline_fixture_panel(
        random_state=1,
        n_pixels_per_area=6,
        years=(2018, 2019, 2020, 2021),
    )
    train_pairs, holdout_pairs = build_transition_pairs(
        panel,
        holdout_splits=("Test", "OOD"),
        holdout_years=(2021,),
    )

    assert not train_pairs.empty
    assert not holdout_pairs.empty
    assert set(train_pairs["split"]).issubset({"Train", "Val"})
    assert set(holdout_pairs["split"]).issubset({"Test", "OOD"})
    assert (holdout_pairs["year_tp1"] == 2021).all()
    assert {"z_t", "z_tp1", "lulc_t", "lulc_tp1"}.issubset(train_pairs.columns)


def test_run_world_model_holdout_validation_writes_required_outputs(tmp_path):
    from data_agent.experiments.world_model_holdout_validation import (
        run_world_model_holdout_validation,
    )

    manifest = run_world_model_holdout_validation(
        output_dir=tmp_path,
        random_state=2,
        n_pixels_per_area=10,
        use_real_panel=False,
    )

    expected = {
        "holdout_metrics_csv": tmp_path / "world_model_holdout_metrics.csv",
        "scenario_calibration_csv": tmp_path / "world_model_scenario_calibration.csv",
        "manifest_json": tmp_path / "world_model_holdout_validation_manifest.json",
        "report_md": tmp_path / "world_model_holdout_validation_report.md",
    }
    for key, path in expected.items():
        assert manifest[key] == str(path)
        assert path.exists()

    metrics = pd.read_csv(expected["holdout_metrics_csv"])
    assert {
        "baseline",
        "evaluation_mode",
        "horizon",
        "mean_cosine_similarity",
        "rmse",
        "mae",
        "n_rows",
        "status",
    }.issubset(metrics.columns)
    assert {"persistence", "mean_delta", "ridge_transition", "markov_transition"}.issubset(
        set(metrics["baseline"])
    )

    calibration = pd.read_csv(expected["scenario_calibration_csv"])
    assert {
        "scenario",
        "scale_factor",
        "predicted_delta_l2",
        "observed_holdout_delta_l2",
        "plausible_vs_holdout",
        "evaluation_mode",
        "status",
    }.issubset(calibration.columns)
    assert calibration["scale_factor"].nunique() >= 5

    manifest_json = json.loads(expected["manifest_json"].read_text(encoding="utf-8"))
    assert manifest_json["evaluation_mode"] in {"offline_fixture_proxy", "real_alphaearth_panel"}
    assert manifest_json["claim_guidance"] in {
        "scenario_simulation_only",
        "predictive_validation_available",
    }
    assert Path(manifest_json["report_md"]).exists()


def test_world_model_predictor_can_be_skipped_without_breaking_baselines(tmp_path):
    from data_agent.experiments.world_model_holdout_validation import (
        run_world_model_holdout_validation,
    )

    manifest = run_world_model_holdout_validation(
        output_dir=tmp_path,
        random_state=3,
        n_pixels_per_area=8,
        use_real_panel=False,
        include_world_model_baseline=True,
        world_model_predictor=lambda train_pairs, holdout_pairs, horizon, scenario: None,
    )

    metrics = pd.read_csv(manifest["holdout_metrics_csv"])
    world_model_rows = metrics[metrics["baseline"] == "world_model_baseline"]
    assert not world_model_rows.empty
    assert set(world_model_rows["status"]) == {"skipped"}
    assert {"persistence", "mean_delta", "ridge_transition", "markov_transition"}.issubset(
        set(metrics["baseline"])
    )


def test_default_world_model_predictor_runs_local_checkpoint_on_fixture_rows():
    from data_agent.experiments.world_model_holdout_validation import (
        build_offline_fixture_panel,
        build_transition_pairs,
        default_world_model_predictor,
    )

    panel = build_offline_fixture_panel(random_state=4, n_pixels_per_area=2)
    train_pairs, holdout_pairs = build_transition_pairs(panel)
    holdout_subset = holdout_pairs[holdout_pairs["horizon"] == 1].head(2)

    predicted = default_world_model_predictor(
        train_pairs=train_pairs,
        holdout_pairs=holdout_subset,
        horizon=1,
        scenario="baseline",
    )

    assert predicted is not None
    assert predicted.shape == (2, 64)
