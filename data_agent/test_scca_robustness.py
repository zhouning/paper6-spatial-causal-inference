import json

import pandas as pd

from data_agent.scca.robustness import (
    classify_robustness,
    run_context_ablation,
    run_placebo_tests,
    summarize_bootstrap,
    summarize_erf_stability,
    write_robustness_outputs,
)
from data_agent.scca.specs import StudySpec


def _robustness_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "unit_id": [f"u{i}" for i in range(1, 9)],
            "group": ["A", "A", "B", "B", "C", "C", "D", "D"],
            "x": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            "y": [0.0, 1.0, 0.5, 1.5, 2.0, 2.5, 3.0, 3.5],
            "baseline": [2.0, 2.1, 2.3, 2.4, 2.7, 2.8, 3.1, 3.3],
            "confounder": [1.0, 1.2, 1.8, 2.0, 2.5, 2.8, 3.2, 3.6],
            "context": [5.0, 4.8, 4.0, 3.9, 3.2, 3.0, 2.4, 2.2],
            "placebo": [7.0, 6.9, 6.8, 6.7, 6.6, 6.5, 6.4, 6.3],
            "outcome": [2.0, 2.5, 3.7, 4.4, 5.8, 6.6, 7.9, 8.7],
        }
    )


def _robustness_spec() -> StudySpec:
    return StudySpec(
        name="fixture_scca",
        unit_id="unit_id",
        exposure="x",
        outcome="outcome",
        baseline_outcome="baseline",
        confounders=("baseline", "confounder"),
        context_columns=("context",),
        coordinate_columns=("x", "y"),
        subgroup_column="group",
    )


def test_run_context_ablation_writes_expected_specifications():
    result = run_context_ablation(_robustness_fixture(), _robustness_spec(), "fixture")
    assert set(result["specification"]) == {
        "exposure_only",
        "confounders_only",
        "context_only",
        "confounders_plus_context",
    }
    assert set(result["estimator"]) == {"baseline_adjusted_ols"}
    main = result.loc[result["specification"] == "confounders_plus_context"].iloc[0]
    assert main["status"] == "ok"
    assert main["n"] == 8
    assert "baseline" in main["included_columns"]


def test_run_placebo_tests_uses_alternate_exposure_without_mutating_input():
    frame = _robustness_fixture()
    before = frame.copy(deep=True)
    tests = [
        {
            "test_name": "fixture_placebo",
            "exposure": "placebo",
            "role": "negative_control",
            "expected_relation": "weaker_than_main",
        }
    ]
    result = run_placebo_tests(frame, _robustness_spec(), "fixture", tests)
    pd.testing.assert_frame_equal(frame, before)
    assert result.loc[0, "exposure"] == "placebo"
    assert result.loc[0, "role"] == "negative_control"
    assert result.loc[0, "status"] in {"ok", "unstable", "skipped"}


def test_summarize_bootstrap_reports_counts_and_sign_stability():
    rows = pd.DataFrame(
        {
            "case": ["fixture"] * 4,
            "bootstrap_type": ["group"] * 4,
            "replicate": [0, 1, 2, 3],
            "coef": [1.0, 1.2, 0.8, float("nan")],
            "n": [8, 8, 8, 0],
            "status": ["ok", "ok", "ok", "skipped"],
        }
    )
    summary = summarize_bootstrap(rows, "fixture", "group", 4)
    assert summary["n_replicates_requested"] == 4
    assert summary["n_replicates_valid"] == 3
    assert summary["failure_count"] == 1
    assert summary["sign_stability"] == 1.0
    assert summary["ci_lower_2_5"] < summary["ci_upper_97_5"]


def test_summarize_erf_stability_detects_increasing_curve():
    erf = pd.DataFrame(
        {
            "exposure": [0.0, 1.0, 2.0, 3.0],
            "response": [2.0, 3.0, 5.0, 8.0],
        }
    )
    summary = summarize_erf_stability(erf, "fixture")
    assert summary["monotonic_direction"] == "increasing"
    assert summary["monotonic_fraction"] == 1.0
    assert summary["range_effect"] == 6.0
    assert summary["median_split_effect"] > 0


def test_write_robustness_outputs_creates_contract_files(tmp_path):
    ablation = run_context_ablation(_robustness_fixture(), _robustness_spec(), "fixture")
    placebo = run_placebo_tests(
        _robustness_fixture(),
        _robustness_spec(),
        "fixture",
        [
            {
                "test_name": "fixture_placebo",
                "exposure": "placebo",
                "role": "negative_control",
                "expected_relation": "weaker_than_main",
            }
        ],
    )
    bootstrap_rows = pd.DataFrame(
        {
            "case": ["fixture"] * 3,
            "bootstrap_type": ["group"] * 3,
            "replicate": [0, 1, 2],
            "coef": [1.0, 1.1, 0.9],
            "n": [8, 8, 8],
            "status": ["ok", "ok", "ok"],
        }
    )
    bootstrap_summary = summarize_bootstrap(bootstrap_rows, "fixture", "group", 3)
    erf_summary = summarize_erf_stability(
        pd.DataFrame({"exposure": [0.0, 1.0], "response": [2.0, 3.0]}),
        "fixture",
    )
    manifest = write_robustness_outputs(
        output_dir=tmp_path,
        case_name="fixture",
        original_decision="moderate_support",
        main_coef=1.0,
        main_limitation="fixture limitation",
        ablation=ablation,
        placebo=placebo,
        bootstrap_rows=bootstrap_rows,
        bootstrap_summary=bootstrap_summary,
        erf_summary=erf_summary,
    )
    for file_name in [
        "context_ablation.csv",
        "placebo_tests.csv",
        "bootstrap_robustness.csv",
        "bootstrap_summary.json",
        "erf_stability.json",
        "robustness_report.md",
        "robustness_manifest.json",
    ]:
        assert (tmp_path / file_name).exists()
    saved_manifest = json.loads((tmp_path / "robustness_manifest.json").read_text(encoding="utf-8"))
    assert manifest["case"] == "fixture"
    assert saved_manifest["robustness_interpretation"] in {
        "robust_support",
        "bounded_support",
        "fragile_support",
    }


def test_classify_robustness_marks_placebo_stronger_as_fragile():
    ablation = pd.DataFrame(
        {
            "specification": ["confounders_plus_context"],
            "coef": [1.0],
            "status": ["ok"],
        }
    )
    placebo = pd.DataFrame(
        {
            "coef": [2.0],
            "status": ["ok"],
        }
    )
    classification = classify_robustness(
        "moderate_support",
        ablation,
        placebo,
        {"sign_stability": 1.0},
        {"monotonic_direction": "increasing", "monotonic_fraction": 1.0},
        "main limitation",
    )
    assert classification["robustness_interpretation"] == "fragile_support"
