import json

import pandas as pd

from data_agent.experiments.run_scca_county_social_capital_robustness import (
    run_county_social_capital_robustness,
)
from data_agent.experiments.run_scca_snow8_robustness import run_snow8_robustness
from data_agent.experiments.run_scca_soho_robustness import run_soho_robustness
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


def test_run_snow8_robustness_writes_manifest_on_fixture(tmp_path):
    frame = pd.DataFrame(
        {
            "sub_ID": [f"s{i}" for i in range(1, 9)],
            "district": ["A", "A", "B", "B", "C", "C", "D", "D"],
            "perc_sou": [0.1, 0.2, 0.4, 0.5, 0.7, 0.8, 0.9, 1.0],
            "perc_lam": [0.9, 0.8, 0.6, 0.5, 0.3, 0.2, 0.1, 0.0],
            "rate1854": [80, 85, 100, 110, 130, 140, 155, 165],
            "rate1849": [60, 62, 70, 72, 80, 82, 90, 92],
            "pop_house": [5.1, 5.3, 5.8, 6.0, 6.4, 6.6, 7.0, 7.1],
            "pop1851": [1000, 1050, 1100, 1150, 1200, 1250, 1300, 1350],
            "pop1854": [1010, 1060, 1110, 1160, 1210, 1260, 1310, 1360],
            "d_sou": [1, 2, 3, 4, 5, 6, 7, 8],
            "d_lam": [8, 7, 6, 5, 4, 3, 2, 1],
            "d_pump": [2, 2, 3, 3, 4, 4, 5, 5],
            "d_thames": [10, 9, 8, 7, 6, 5, 4, 3],
            "d_unasc": [0.1, 0.2, 0.1, 0.2, 0.3, 0.2, 0.3, 0.4],
        }
    )
    csv_path = tmp_path / "snow8.csv"
    frame.to_csv(csv_path, index=False)
    manifest = run_snow8_robustness(csv_path=csv_path, output_dir=tmp_path / "out", n_replicates=5)
    assert manifest["case"] == "snow8"
    assert (tmp_path / "out" / "robustness_manifest.json").exists()


def test_run_soho_robustness_writes_manifest_on_fixture(tmp_path):
    frame = pd.DataFrame(
        {
            "ID": [str(i) for i in range(1, 9)],
            "deaths": [0, 1, 1, 2, 2, 3, 3, 4],
            "death_dum": [0, 1, 1, 1, 1, 1, 1, 1],
            "dis_bspump": [200, 160, 120, 90, 70, 50, 30, 10],
            "dis_pestf": [20, 30, 35, 45, 60, 80, 90, 110],
            "dis_sewers": [25, 35, 40, 55, 70, 85, 100, 115],
            "pestfield": [1, 1, 1, 0, 0, 0, 0, 0],
            "COORD_X": [529200, 529220, 529240, 529260, 529280, 529300, 529320, 529340],
            "COORD_Y": [181000, 181020, 181040, 181060, 181080, 181100, 181120, 181140],
        }
    )
    csv_path = tmp_path / "soho.csv"
    frame.to_csv(csv_path, index=False)
    manifest = run_soho_robustness(csv_path=csv_path, output_dir=tmp_path / "out", n_replicates=5)
    assert manifest["case"] == "soho"
    assert (tmp_path / "out" / "robustness_manifest.json").exists()


def test_run_county_social_capital_robustness_writes_manifest_on_fixture(tmp_path):
    frame = pd.DataFrame(
        {
            "OBJECTID": list(range(1, 9)),
            "STATE_NAME": ["A", "A", "B", "B", "C", "C", "D", "D"],
            "CountyCode": [1001, 1003, 2001, 2003, 3001, 3003, 4001, 4003],
            "County": [f"County {i}" for i in range(1, 9)],
            "FIPS": [1001, 1003, 2001, 2003, 3001, 3003, 4001, 4003],
            "AveAgeDeath": [70, 71, 72, 73, 74, 75, 76, 77],
            "SocialAssoc": [5, 6, 7, 8, 9, 10, 11, 12],
            "UnemployRate": [6, 5, 5, 4, 4, 3, 3, 2],
            "pHHinPoverty": [20, 18, 16, 14, 12, 10, 8, 6],
            "pNoHealthInsur": [12, 11, 10, 9, 8, 7, 6, 5],
            "MentalHealth": [5, 5, 4, 4, 3, 3, 2, 2],
            "pAdultSmoking": [25, 23, 21, 19, 17, 15, 13, 11],
            "pAdultObesity": [35, 34, 33, 32, 31, 30, 29, 28],
            "FastFood": [2, 2, 3, 3, 4, 4, 5, 5],
            "pInsufficientSleep": [40, 38, 36, 34, 32, 30, 28, 26],
            "pAlcohol": [4, 5, 6, 7, 8, 9, 10, 11],
            "pSuicideDeaths": [20, 19, 18, 17, 16, 15, 14, 13],
            "AirPollution": [12, 11, 10, 9, 8, 7, 6, 5],
            "Shape_Length": [100, 120, 130, 140, 150, 160, 170, 180],
            "Shape_Area": [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700],
        }
    )
    workbook = tmp_path / "county.xlsx"
    frame.to_excel(workbook, sheet_name="CountyData", index=False)
    manifest = run_county_social_capital_robustness(
        workbook_path=workbook,
        output_dir=tmp_path / "out",
        n_replicates=5,
    )
    assert manifest["case"] == "county_social_capital"
    assert (tmp_path / "out" / "robustness_manifest.json").exists()
