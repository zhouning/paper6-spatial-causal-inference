import json

import pandas as pd


def test_synthetic_multiseed_benchmark_writes_summary_and_details(tmp_path):
    from data_agent.experiments.synthetic_multiseed import run_synthetic_multiseed_benchmark

    manifest = run_synthetic_multiseed_benchmark(
        output_dir=tmp_path,
        seeds=[0, 1],
        scenario_names=["PSM", "DiD"],
    )

    summary_path = tmp_path / "synthetic_multiseed_summary.csv"
    details_path = tmp_path / "synthetic_multiseed_details.json"

    assert manifest["summary_csv"] == str(summary_path)
    assert manifest["details_json"] == str(details_path)
    assert summary_path.exists()
    assert details_path.exists()

    summary = pd.read_csv(summary_path)
    assert set(summary["scenario"]) == {"PSM", "DiD"}
    assert set(summary["variant"]) == {"standard"}
    for column in [
        "n_seeds",
        "n_success",
        "failure_count",
        "estimate_mean",
        "bias",
        "rmse",
        "mae",
        "coverage_rate",
    ]:
        assert column in summary.columns

    assert summary["n_seeds"].tolist() == [2, 2]
    assert summary["failure_count"].sum() == 0
    assert summary["rmse"].notna().all()

    details = json.loads(details_path.read_text(encoding="utf-8"))
    assert len(details) == 4
    assert {row["status"] for row in details} == {"ok"}


def test_synthetic_multiseed_summary_counts_failures(tmp_path):
    from data_agent.experiments.synthetic_multiseed import write_benchmark_outputs

    details = [
        {
            "scenario": "PSM",
            "variant": "standard",
            "method": "PSM",
            "seed": 0,
            "status": "ok",
            "metric_name": "att",
            "true_value": 10.0,
            "estimate": 12.0,
            "ci_lower": 8.0,
            "ci_upper": 14.0,
        },
        {
            "scenario": "PSM",
            "variant": "standard",
            "method": "PSM",
            "seed": 1,
            "status": "error",
            "metric_name": "att",
            "true_value": 10.0,
            "estimate": None,
            "ci_lower": None,
            "ci_upper": None,
            "error": "synthetic failure",
        },
    ]

    manifest = write_benchmark_outputs(details, tmp_path)

    summary = pd.read_csv(manifest["summary_csv"])
    assert len(summary) == 1
    assert int(summary.loc[0, "n_seeds"]) == 2
    assert int(summary.loc[0, "n_success"]) == 1
    assert int(summary.loc[0, "failure_count"]) == 1
    assert float(summary.loc[0, "coverage_rate"]) == 1.0


def test_synthetic_multiseed_summary_uses_seed_specific_true_values(tmp_path):
    from data_agent.experiments.synthetic_multiseed import write_benchmark_outputs

    details = [
        {
            "scenario": "CausalForest",
            "variant": "standard",
            "method": "causal_forest_analysis",
            "seed": 0,
            "status": "ok",
            "metric_name": "ate",
            "true_value": 100.0,
            "estimate": 101.0,
            "ci_lower": 99.0,
            "ci_upper": 103.0,
        },
        {
            "scenario": "CausalForest",
            "variant": "standard",
            "method": "causal_forest_analysis",
            "seed": 1,
            "status": "ok",
            "metric_name": "ate",
            "true_value": 110.0,
            "estimate": 109.0,
            "ci_lower": 107.0,
            "ci_upper": 111.0,
        },
    ]

    manifest = write_benchmark_outputs(details, tmp_path)
    summary = pd.read_csv(manifest["summary_csv"])

    assert len(summary) == 1
    assert float(summary.loc[0, "bias"]) == 0.0
    assert float(summary.loc[0, "rmse"]) == 1.0
    assert float(summary.loc[0, "mae"]) == 1.0
    assert float(summary.loc[0, "coverage_rate"]) == 1.0


def test_synthetic_multiseed_extended_variants_add_sensitivity_rows(tmp_path):
    from data_agent.experiments.synthetic_multiseed import run_synthetic_multiseed_benchmark

    manifest = run_synthetic_multiseed_benchmark(
        output_dir=tmp_path,
        seeds=[0],
        scenario_names=["PSM", "GCCM"],
        include_extended_variants=True,
    )

    summary = pd.read_csv(manifest["summary_csv"])

    psm_variants = set(summary.loc[summary["scenario"] == "PSM", "variant"])
    gccm_variants = set(summary.loc[summary["scenario"] == "GCCM", "variant"])

    assert psm_variants == {
        "standard",
        "caliper",
        "kernel",
        "naive_difference",
        "ols_adjusted",
    }
    assert gccm_variants == {"standard", "knn_k2", "queen"}


def test_gccm_direction_accuracy_uses_rho_dominance_when_both_converge():
    from data_agent.experiments.synthetic_multiseed import _gccm_direction_accuracy

    result = {
        "x_causes_y_converges": True,
        "y_causes_x_converges": True,
        "x_causes_y_rho": 0.801,
        "y_causes_x_rho": 0.798,
    }

    assert _gccm_direction_accuracy(result) == 1.0


def test_gccm_direction_accuracy_rejects_reverse_rho_dominance():
    from data_agent.experiments.synthetic_multiseed import _gccm_direction_accuracy

    result = {
        "x_causes_y_converges": True,
        "y_causes_x_converges": True,
        "x_causes_y_rho": 0.790,
        "y_causes_x_rho": 0.810,
    }

    assert _gccm_direction_accuracy(result) == 0.0


def test_gccm_direction_accuracy_supports_saved_details_without_convergence_flags():
    from data_agent.experiments.synthetic_multiseed import _gccm_direction_accuracy

    saved_detail = {
        "x_causes_y_rho": 0.801,
        "y_causes_x_rho": 0.798,
    }

    assert _gccm_direction_accuracy(saved_detail) == 1.0
