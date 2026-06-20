from pathlib import Path

import pandas as pd

from geocausal.adapters import (
    AnalysisRequest,
    build_analysis_joined_table,
    run_scca_analysis,
    write_analysis_config,
)


def test_write_analysis_config_uses_only_user_supplied_generic_fields(tmp_path):
    request = AnalysisRequest(
        case_name="generic_dose_response",
        input_path=tmp_path / "generic.csv",
        output_dir=tmp_path / "results",
        unit_id="id",
        exposure="dose",
        outcome="response",
        confounders=("confounder",),
        context_columns=("context",),
        bootstrap_group="group",
        placebo_exposures=("placebo_dose",),
        lower_exposure_quantile=0.1,
        upper_exposure_quantile=0.9,
        target_outcomes=(5.0,),
        bootstrap_replicates=5,
    )

    config_path = write_analysis_config(request)

    text = config_path.read_text(encoding="utf-8")
    assert "dose" in text
    assert "response" in text
    assert "SocialAssoc" not in text
    assert "AveAgeDeath" not in text
    assert "County" not in text


def test_run_scca_analysis_from_generic_table_without_case_specific_fields(tmp_path):
    input_path = tmp_path / "generic.csv"
    frame = pd.DataFrame(
        {
            "id": [f"u{i:02d}" for i in range(20)],
            "dose": list(range(20)),
            "response": [2.0 + 0.4 * i for i in range(20)],
            "confounder": [float(i % 5) for i in range(20)],
            "context": [float(20 - i) for i in range(20)],
            "group": [f"g{i % 4}" for i in range(20)],
            "placebo_dose": [float((i * 3) % 7) for i in range(20)],
        }
    )
    frame.to_csv(input_path, index=False)

    request = AnalysisRequest(
        case_name="generic_dose_response",
        input_path=input_path,
        output_dir=tmp_path / "results",
        unit_id="id",
        exposure="dose",
        outcome="response",
        confounders=("confounder",),
        context_columns=("context",),
        bootstrap_group="group",
        placebo_exposures=("placebo_dose",),
        lower_exposure_quantile=0.1,
        upper_exposure_quantile=0.9,
        target_outcomes=(5.0,),
        bootstrap_replicates=5,
    )

    manifest = run_scca_analysis(request)

    assert manifest["case_name"] == "generic_dose_response"
    assert manifest["exposure"] == "dose"
    assert manifest["outcome"] == "response"
    assert manifest["row_count"] == 16
    assert manifest["preprocessing"]["exposure_trim"]["removed_n"] == 4
    assert manifest["files"]["target_exposures"] == "target_exposures.csv"

    targets = pd.read_csv(Path(manifest["config_path"]).parent / "target_exposures.csv")
    assert set(targets["method"]) == {"adjusted_ols_prediction", "erf_delta_anchor"}


def test_build_analysis_joined_table_is_available_without_gis_dependencies(tmp_path):
    input_csv = tmp_path / "input.csv"
    target_csv = tmp_path / "target_exposures.csv"
    output_csv = tmp_path / "joined.csv"
    pd.DataFrame(
        {
            "unit_key": ["x1", "x2"],
            "dose": [3.0, 4.0],
            "response": [8.0, 9.0],
        }
    ).to_csv(input_csv, index=False)
    pd.DataFrame(
        {
            "unit_id": ["x1", "x2"],
            "method": ["erf_delta_anchor", "erf_delta_anchor"],
            "target_name": ["goal 10", "goal 10"],
            "required_exposure": [5.0, 6.0],
            "exposure_change": [2.0, 2.0],
            "status": ["ok", "ok"],
        }
    ).to_csv(target_csv, index=False)

    build_analysis_joined_table(
        input_csv=input_csv,
        target_exposures_csv=target_csv,
        output_csv=output_csv,
        unit_id_field="unit_key",
    )

    joined = pd.read_csv(output_csv)
    assert "gc_goal_10_required_exposure" in joined.columns
    assert joined.loc[0, "gc_goal_10_exposure_change"] == 2.0


def test_example_county_social_capital_data_runs_through_notebook_adapter(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    sample_csv = repo_root / "examples" / "data" / "county_social_capital.csv"
    assert sample_csv.exists()

    request = AnalysisRequest(
        case_name="county_social_capital_example",
        input_path=sample_csv,
        output_dir=tmp_path / "county_social_capital_example",
        unit_id="FIPS",
        exposure="SocialAssoc",
        outcome="AveAgeDeath",
        confounders=(
            "UnemployRate",
            "pHHinPoverty",
            "pNoHealthInsur",
            "MentalHealth",
            "pAdultSmoking",
            "pAdultObesity",
        ),
        context_columns=("AirPollution", "Shape_Area"),
        bootstrap_group="STATE_NAME",
        lower_exposure_quantile=0.01,
        upper_exposure_quantile=0.99,
        target_outcomes=(70.0,),
        bootstrap_replicates=30,
    )

    manifest = run_scca_analysis(request)

    assert manifest["case_name"] == "county_social_capital_example"
    assert manifest["row_count"] > 3000
    assert manifest["files"]["target_exposures"] == "target_exposures.csv"
    target_csv = request.output_dir / "target_exposures.csv"
    assert target_csv.exists()

    joined_csv = request.output_dir / "analysis_joined.csv"
    build_analysis_joined_table(
        input_csv=sample_csv,
        target_exposures_csv=target_csv,
        output_csv=joined_csv,
        unit_id_field="FIPS",
    )
    joined = pd.read_csv(joined_csv, dtype={"FIPS": str})
    assert len(joined) > 3000
    assert "gc_target_70_required_exposure" in joined.columns
