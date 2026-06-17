from pathlib import Path
import json

import pandas as pd

from data_agent.scca.specs import SCCAPaths, StudySpec
from data_agent.scca.profiling import load_table, profile_table
from data_agent.scca.context import build_context_features


def test_study_spec_snow8_defaults():
    spec = StudySpec.snow8_default()
    assert spec.unit_id == "sub_ID"
    assert spec.exposure == "perc_sou"
    assert spec.outcome == "rate1854"
    assert spec.baseline_outcome == "rate1849"
    assert "pop_house" in spec.confounders
    assert "d_thames" in spec.context_columns


def test_scca_paths_create_expected_output_dir(tmp_path):
    paths = SCCAPaths(output_dir=tmp_path / "scca_snow8")
    paths.ensure()
    assert paths.output_dir.exists()
    assert paths.data_profile.name == "data_profile.json"
    assert paths.effect_estimates.name == "effect_estimates.csv"


def _snow8_like_frame():
    return pd.DataFrame(
        {
            "sub_ID": ["1", "2", "3"],
            "district": ["A", "A", "B"],
            "perc_sou": [1.0, 0.5, 0.0],
            "rate1854": [180.0, 120.0, 60.0],
            "rate1849": [130.0, 100.0, 70.0],
            "pop_house": [6.5, 7.1, 5.9],
            "pop1851": [10000, 8000, 7000],
            "d_thames": [20.0, 30.0, 10.0],
        }
    )


def test_load_table_reads_csv_with_utf8_sig(tmp_path):
    path = tmp_path / "snow8.csv"
    _snow8_like_frame().to_csv(path, index=False, encoding="utf-8-sig")
    loaded = load_table(path)
    assert loaded.shape == (3, 8)
    assert loaded["perc_sou"].dtype.kind in {"f", "i"}


def test_profile_table_writes_json_and_candidates(tmp_path):
    df = _snow8_like_frame()
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    profile = profile_table(df, StudySpec.snow8_default(), paths)
    assert profile["n_rows"] == 3
    assert profile["columns"]["perc_sou"]["role"] == "exposure"
    assert profile["columns"]["rate1854"]["role"] == "outcome"
    assert paths.data_profile.exists()
    assert paths.variable_candidates.exists()
    saved = json.loads(paths.data_profile.read_text(encoding="utf-8"))
    assert saved["n_columns"] == 8


def test_build_context_features_adds_baseline_difference_and_density(tmp_path):
    df = _snow8_like_frame()
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    features, manifest = build_context_features(df, StudySpec.snow8_default(), paths)
    assert "outcome_change" in features.columns
    assert "rate1849_centered" in features.columns
    assert "pop_house_centered" in features.columns
    assert "d_thames_centered" in features.columns
    assert features.loc[0, "outcome_change"] == 50.0
    assert manifest["n_features"] >= 4
    assert paths.context_features.exists()
    assert paths.context_manifest.exists()


def test_build_context_features_skips_missing_baseline_column(tmp_path):
    df = _snow8_like_frame().drop(columns=["rate1849"])
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    features, manifest = build_context_features(df, StudySpec.snow8_default(), paths)
    assert "outcome_change" not in features.columns
    assert "rate1849_centered" not in features.columns
    assert "perc_sou" in features.columns
    assert manifest["n_rows"] == 3
    assert paths.context_features.exists()


def test_build_context_features_preserves_missing_core_values(tmp_path):
    df = _snow8_like_frame()
    df.loc[1, "perc_sou"] = None
    df.loc[2, "rate1854"] = None
    df.loc[0, "rate1849"] = None
    df.loc[1, "pop_house"] = None
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    features, _ = build_context_features(df, StudySpec.snow8_default(), paths)
    assert pd.isna(features.loc[1, "perc_sou"])
    assert pd.isna(features.loc[2, "rate1854"])
    assert pd.isna(features.loc[0, "rate1849"])
    assert pd.isna(features.loc[0, "outcome_change"])
    assert not pd.isna(features.loc[1, "pop_house"])
    assert not pd.isna(features.loc[1, "pop_house_centered"])


from data_agent.scca.design import select_design


def test_select_design_continuous_exposure_with_small_sample_warning(tmp_path):
    df = _snow8_like_frame()
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    plan = select_design(df, StudySpec.snow8_default(), paths)
    assert plan["design"] == "continuous_exposure_baseline_adjusted"
    assert "generalized_propensity_erf" in plan["estimators"]
    assert "baseline_adjusted_ols" in plan["estimators"]
    assert any("small sample" in warning.lower() for warning in plan["warnings"])
    assert paths.design_plan.exists()


def test_select_design_does_not_advertise_unimplemented_binary_or_missing_baseline(tmp_path):
    df = _snow8_like_frame().drop(columns=["rate1849"])
    df["perc_sou"] = [1.0, 1.0, 0.0]
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    plan = select_design(df, StudySpec.snow8_default(), paths)
    assert plan["design"] == "binary_exposure_adjusted_regression"
    assert "propensity_weighted_ols" not in plan["estimators"]
    assert "difference_outcome_ols" not in plan["estimators"]
    assert "baseline_adjusted_ols" in plan["estimators"]
    assert any("baseline outcome column" in warning.lower() for warning in plan["warnings"])
    saved = json.loads(paths.design_plan.read_text(encoding="utf-8"))
    assert saved == plan


from data_agent.scca.context import build_context_features
from data_agent.scca.estimators import estimate_effects


def test_estimate_effects_writes_effect_tables(tmp_path):
    df = _snow8_like_frame()
    spec = StudySpec.snow8_default()
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    features, _ = build_context_features(df, spec, paths)
    results = estimate_effects(features, spec, paths)
    assert "baseline_adjusted_ols" in results
    assert "difference_outcome_ols" in results
    assert "generalized_propensity_erf" in results
    assert paths.effect_estimates.exists()
    assert paths.erf_curve.exists()
    assert paths.model_diagnostics.exists()
    estimates = pd.read_csv(paths.effect_estimates)
    assert set(estimates["estimator"]) >= {"baseline_adjusted_ols", "difference_outcome_ols"}


def test_estimate_effects_records_skipped_models_when_core_rows_sparse(tmp_path):
    df = _snow8_like_frame()
    df.loc[:, "perc_sou"] = [1.0, float("nan"), float("nan")]
    df.loc[:, "rate1854"] = [180.0, float("nan"), float("nan")]
    df.loc[:, "rate1849"] = [130.0, float("nan"), float("nan")]
    spec = StudySpec.snow8_default()
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    features, _ = build_context_features(df, spec, paths)
    results = estimate_effects(features, spec, paths)
    assert paths.effect_estimates.exists()
    assert paths.erf_curve.exists()
    assert paths.model_diagnostics.exists()
    assert results["baseline_adjusted_ols"]["status"] == "skipped"
    diagnostics = json.loads(paths.model_diagnostics.read_text(encoding="utf-8"))
    assert diagnostics["original_n"] == 3
    assert diagnostics["estimators"]["baseline_adjusted_ols"]["dropped_n"] >= 2


def test_estimate_effects_handles_non_default_index_and_reports_erf_effect(tmp_path):
    df = _snow8_like_frame()
    spec = StudySpec.snow8_default()
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    features, _ = build_context_features(df, spec, paths)
    features.index = [10, 20, 30]
    results = estimate_effects(features, spec, paths)
    gps = results["generalized_propensity_erf"]
    assert "range_effect" in gps
    assert "response_min_exposure" in gps
    assert "response_max_exposure" in gps
    erf_curve = pd.read_csv(paths.erf_curve)
    assert gps["n_grid"] == len(erf_curve)
    diagnostics = json.loads(paths.model_diagnostics.read_text(encoding="utf-8"))
    assert diagnostics["gps_weight_mean"] > 0
    assert diagnostics["erf_n"] >= 1
    estimates = pd.read_csv(paths.effect_estimates)
    erf_row = estimates.loc[estimates["estimator"] == "generalized_propensity_erf"].iloc[0]
    assert pd.notna(erf_row["coef"])


from data_agent.scca.diagnostics import audit_effects


def test_audit_effects_writes_balance_overlap_and_credibility(tmp_path):
    df = _snow8_like_frame()
    spec = StudySpec.snow8_default()
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    features, _ = build_context_features(df, spec, paths)
    estimate_effects(features, spec, paths)
    report = audit_effects(features, spec, paths)
    assert report["decision"] in {"strong_support", "moderate_support", "weak_or_failed_support"}
    assert "reasons" in report
    assert paths.balance_summary.exists()
    assert paths.overlap_summary.exists()
    assert paths.spatial_robustness.exists()
    assert paths.credibility_report.exists()


def test_audit_effects_downgrades_when_exposure_not_analyzable(tmp_path):
    df = _snow8_like_frame()
    df["perc_sou"] = [None, None, None]
    spec = StudySpec.snow8_default()
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    features, _ = build_context_features(df, spec, paths)
    report = audit_effects(features, spec, paths)
    assert report["decision"] == "weak_or_failed_support"
    assert any("exposure" in reason.lower() for reason in report["reasons"])


def test_audit_effects_downgrades_when_leave_group_out_unestimable(tmp_path):
    df = _snow8_like_frame()
    spec = StudySpec.snow8_default()
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    features, _ = build_context_features(df, spec, paths)
    features["district"] = ["A", "B", "C"]
    report = audit_effects(features, spec, paths)
    robustness = pd.read_csv(paths.spatial_robustness)
    assert robustness["coef"].isna().all()
    assert report["decision"] == "weak_or_failed_support"
    assert any(
        "leave" in reason.lower() or "spatial" in reason.lower()
        for reason in report["reasons"]
    )


def test_audit_effects_downgrades_when_some_leave_group_out_folds_unestimable(tmp_path):
    spec = StudySpec.snow8_default()
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    features = pd.DataFrame(
        {
            "sub_ID": ["1", "2", "3", "4", "5"],
            "district": ["A", "A", "A", "B", "C"],
            "perc_sou": [0.0, 0.2, 0.4, 0.6, 0.8],
            "rate1854": [10.0, 14.0, 18.0, 22.0, 26.0],
        }
    )

    report = audit_effects(features, spec, paths)

    robustness = pd.read_csv(paths.spatial_robustness)
    assert robustness["coef"].isna().sum() > 0
    assert robustness["coef"].notna().sum() > 0
    assert report["decision"] in {"moderate_support", "weak_or_failed_support"}
    assert report["decision"] != "strong_support"
    assert any(
        "leave" in reason.lower() or "spatial" in reason.lower()
        for reason in report["reasons"]
    )


from data_agent.scca.reporting import write_report


def test_write_report_creates_markdown_and_manifest(tmp_path):
    spec = StudySpec.snow8_default()
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    credibility = {"decision": "moderate_support", "reasons": ["diagnostic warning"]}
    write_report(spec, paths, credibility)
    text = paths.analysis_report.read_text(encoding="utf-8")
    assert "# SCCA Analysis Report" in text
    assert "moderate_support" in text
    assert paths.manifest.exists()
