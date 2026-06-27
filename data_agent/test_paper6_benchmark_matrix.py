from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _write_fixture_inputs(tmp_path: Path) -> dict[str, Path]:
    arcgis_manifest = tmp_path / "arcgis_comparison_manifest.json"
    arcgis_manifest.write_text(
        json.dumps(
            {
                "metrics": {
                    "arcgis_final_n": 3044,
                    "geocausal_joined_rows": 3044,
                    "arcgis_mean_weighted_correlation": 0.0559,
                    "geocausal_confounder_mean_abs_weighted_correlation": 0.1114,
                    "geocausal_arcgis_style_calibrated_confounder_mean_abs_weighted_correlation": 0.0453,
                    "erf_response_mae": 1.2736,
                    "preferred_erf_response_mae": 0.0429,
                    "arcgis_style_erf_response_mae": 0.0429,
                    "arcgis_style_calibrated_erf_response_mae": 0.0300,
                }
            }
        ),
        encoding="utf-8",
    )
    soho_arcgis_run_manifest = tmp_path / "soho_arcgis_causal_manifest_relaxed.json"
    soho_arcgis_run_manifest.write_text(
        json.dumps(
            {
                "parameters": {
                    "output_stem": "soho_arcgis_builtin_relaxed",
                    "balance_threshold": 0.2,
                }
            }
        ),
        encoding="utf-8",
    )
    soho_arcgis_manifest = tmp_path / "soho_arcgis_comparison_manifest.json"
    soho_arcgis_manifest.write_text(
        json.dumps(
            {
                "arcgis_manifest_path": str(soho_arcgis_run_manifest),
                "metrics": {
                    "arcgis_final_n": 1814,
                    "geocausal_joined_rows": 1814,
                    "arcgis_mean_weighted_correlation": 0.1778,
                    "geocausal_confounder_mean_abs_weighted_correlation": 0.3354,
                    "geocausal_arcgis_style_calibrated_confounder_mean_abs_weighted_correlation": 0.1109,
                    "erf_response_mae": 0.4119,
                    "preferred_erf_response_mae": 0.1481,
                    "arcgis_style_erf_response_mae": 0.1481,
                    "arcgis_style_calibrated_erf_response_mae": 0.1200,
                },
            }
        ),
        encoding="utf-8",
    )
    method_comparison = tmp_path / "scca_method_comparison.csv"
    pd.DataFrame(
        [
            {
                "comparison_id": "county_nonspatial_vs_spatial",
                "case": "county_social_capital",
                "baseline_method": "adjusted OLS",
                "enhanced_method": "SCCA spatial diagnostics",
                "baseline_effect": 0.18,
                "enhanced_effect": 0.17,
                "baseline_grade": "core_support",
                "enhanced_grade": "bounded_support",
            },
            {
                "comparison_id": "chongqing_raw_vs_full_scca",
                "case": "chongqing_uhi",
                "baseline_method": "raw difference",
                "enhanced_method": "full SCCA matching",
                "baseline_effect": 2.2,
                "enhanced_effect": 0.9,
                "baseline_grade": "bounded_support",
                "enhanced_grade": "core_support",
            },
        ]
    ).to_csv(method_comparison, index=False)
    synthetic_summary = tmp_path / "scenario_fragility_summary.csv"
    pd.DataFrame(
        [
            {
                "scenario": "ERF",
                "n_summary_rows": 4,
                "n_robust": 2,
                "n_bounded": 2,
                "n_fragile": 0,
                "min_score": 0.84,
                "max_score": 0.91,
            },
            {
                "scenario": "GCCM",
                "n_summary_rows": 12,
                "n_robust": 0,
                "n_bounded": 0,
                "n_fragile": 12,
                "min_score": 0.06,
                "max_score": 0.40,
            },
        ]
    ).to_csv(synthetic_summary, index=False)
    epa_summary = tmp_path / "epa_benchmark_summary.json"
    epa_summary.write_text(
        json.dumps(
            {
                "benchmark_role": "policy_structure_semisynthetic_until_airdata_download_recovers",
                "airdata_status": "AQS AirData downloads timed out; Green Book and Census inputs were acquired.",
                "real_data": {
                    "effect_estimate": -0.9999999999561664,
                    "evidence_grade": "bounded_support",
                    "row_count": 4880,
                    "panel_year_min": 2005,
                    "panel_year_max": 2024,
                    "true_effect": -1.0,
                    "absolute_error": 4.3833603413645505e-11,
                },
                "semi_synthetic": {
                    "scenario_count": 3,
                    "median_absolute_error": 4.3586023679154096e-11,
                    "mean_absolute_error": 3.8291888178794885e-11,
                    "max_absolute_error": 4.3833603413645505e-11,
                    "scenario_metrics": [
                        {
                            "scenario": "stable_known_effect",
                            "absolute_error": 4.3833603413645505e-11,
                            "evidence_grade": "bounded_support",
                            "grade_rule_ids": [
                                "weak_credibility",
                                "bounded_robustness",
                                "material_residual_moran",
                            ],
                        },
                        {
                            "scenario": "spatial_confounding",
                            "absolute_error": 2.7456037443585046e-11,
                            "evidence_grade": "bounded_support",
                            "grade_rule_ids": [
                                "weak_credibility",
                                "bounded_robustness",
                                "material_residual_moran",
                            ],
                        },
                        {
                            "scenario": "spillover",
                            "absolute_error": 4.3586023679154096e-11,
                            "evidence_grade": "bounded_support",
                            "grade_rule_ids": [
                                "weak_credibility",
                                "fragile_robustness",
                                "material_residual_moran",
                            ],
                        },
                    ],
                },
                "policy_structure_semisynthetic": {
                    "effect_estimate": -0.9999999999561664,
                    "evidence_grade": "bounded_support",
                    "row_count": 4880,
                    "panel_year_min": 2005,
                    "panel_year_max": 2024,
                    "true_effect": -1.0,
                    "absolute_error": 4.3833603413645505e-11,
                },
            }
        ),
        encoding="utf-8",
    )
    return {
        "arcgis_manifest": arcgis_manifest,
        "soho_arcgis_manifest": soho_arcgis_manifest,
        "method_comparison": method_comparison,
        "synthetic_summary": synthetic_summary,
        "epa_summary": epa_summary,
    }


def test_paper6_benchmark_matrix_combines_arcgis_real_and_synthetic_rows(tmp_path):
    from data_agent.experiments.paper6_benchmark_matrix import build_paper6_benchmark_matrix

    paths = _write_fixture_inputs(tmp_path)

    matrix = build_paper6_benchmark_matrix(
        arcgis_comparison_manifest=paths["arcgis_manifest"],
        method_comparison_csv=paths["method_comparison"],
        synthetic_scenario_summary_csv=paths["synthetic_summary"],
    )

    assert set(matrix["case_id"]) == {
        "county_arcgis_builtin",
        "county_social_capital",
        "chongqing_uhi",
        "synthetic_ERF",
        "synthetic_GCCM",
    }
    county = matrix.loc[matrix["case_id"] == "county_arcgis_builtin"].iloc[0]
    assert county["arcgis_available"] is True
    assert county["preferred_erf_response_mae"] == 0.0429
    assert county["arcgis_style_erf_response_mae"] == 0.0429
    assert county["arcgis_style_calibrated_erf_response_mae"] == 0.03
    assert county["geocausal_calibrated_balance"] == 0.0453
    synthetic = matrix.loc[matrix["case_id"] == "synthetic_GCCM"].iloc[0]
    assert synthetic["data_type"] == "synthetic_known_truth"
    assert synthetic["synthetic_fragile_rows"] == 12
    assert "prioritize" in synthetic["next_action"].lower()


def test_paper6_benchmark_matrix_writes_csv_report_and_manifest(tmp_path):
    from data_agent.experiments.paper6_benchmark_matrix import write_paper6_benchmark_matrix

    paths = _write_fixture_inputs(tmp_path)
    manifest = write_paper6_benchmark_matrix(
        output_dir=tmp_path / "out",
        arcgis_comparison_manifest=paths["arcgis_manifest"],
        method_comparison_csv=paths["method_comparison"],
        synthetic_scenario_summary_csv=paths["synthetic_summary"],
    )

    assert Path(manifest["matrix_csv"]).exists()
    assert Path(manifest["report_md"]).exists()
    assert Path(manifest["manifest_json"]).exists()
    assert manifest["n_rows"] == 5
    assert "county_arcgis_builtin" in manifest["case_ids"]
    report = Path(manifest["report_md"]).read_text(encoding="utf-8")
    assert "Paper 6 Multi-Dataset Benchmark Matrix" in report
    assert "ArcGIS-style ERF MAE" in report
    assert "synthetic_GCCM" in report

def test_paper6_benchmark_matrix_includes_epa_policy_structure_semisynthetic_row(tmp_path):
    from data_agent.experiments.paper6_benchmark_matrix import build_paper6_benchmark_matrix

    paths = _write_fixture_inputs(tmp_path)

    matrix = build_paper6_benchmark_matrix(
        epa_benchmark_summary_json=paths["epa_summary"],
    )

    assert set(matrix["case_id"]) == {"epa_nonattainment_airdata"}
    epa = matrix.iloc[0]
    assert epa["data_type"] == "semi_synthetic_policy_structure"
    assert epa["sample_rows"] == 4880
    assert epa["panel_year_min"] == 2005
    assert epa["panel_year_max"] == 2024
    assert epa["scenario_count"] == 3
    assert epa["synthetic_fragile_rows"] == 1
    assert epa["enhanced_effect"] == -0.9999999999561664
    assert epa["true_effect"] == -1.0
    assert epa["absolute_error"] == 4.3833603413645505e-11
    assert epa["median_absolute_error"] == 4.3586023679154096e-11
    assert epa["enhanced_grade"] == "bounded_support"
    assert "real epa policy geography" in epa["evidence_summary"].lower()

def test_paper6_benchmark_matrix_writer_includes_optional_epa_input(tmp_path):
    from data_agent.experiments.paper6_benchmark_matrix import write_paper6_benchmark_matrix

    paths = _write_fixture_inputs(tmp_path)

    manifest = write_paper6_benchmark_matrix(
        output_dir=tmp_path / "out_with_epa",
        arcgis_comparison_manifest=paths["arcgis_manifest"],
        method_comparison_csv=paths["method_comparison"],
        synthetic_scenario_summary_csv=paths["synthetic_summary"],
        epa_benchmark_summary_json=paths["epa_summary"],
    )

    assert manifest["n_rows"] == 6
    assert "epa_nonattainment_airdata" in manifest["case_ids"]
    assert manifest["inputs"]["epa_benchmark_summary_json"] == str(paths["epa_summary"])
    report = Path(manifest["report_md"]).read_text(encoding="utf-8")
    assert "Policy-structure semi-synthetic rows" in report
    assert "epa_nonattainment_airdata" in report

def test_paper6_surpass_scorecard_marks_wins_gaps_and_next_priorities(tmp_path):
    from data_agent.experiments.paper6_benchmark_matrix import (
        build_arcgis_surpass_scorecard,
        build_paper6_benchmark_matrix,
    )

    paths = _write_fixture_inputs(tmp_path)
    matrix = build_paper6_benchmark_matrix(
        arcgis_comparison_manifest=paths["arcgis_manifest"],
        method_comparison_csv=paths["method_comparison"],
        synthetic_scenario_summary_csv=paths["synthetic_summary"],
        epa_benchmark_summary_json=paths["epa_summary"],
    )

    scorecard = build_arcgis_surpass_scorecard(matrix, required_arcgis_real_rows=2)

    assert {
        "county_calibrated_balance",
        "county_preferred_erf",
        "county_arcgis_style_erf",
        "county_arcgis_style_calibrated_erf",
        "county_default_erf_gap",
        "direct_arcgis_real_dataset_coverage",
        "synthetic_fragility",
        "epa_known_truth_recovery",
        "overall_arcgis_surpass_readiness",
    }.issubset(set(scorecard["criterion_id"]))
    balance = scorecard.loc[scorecard["criterion_id"] == "county_calibrated_balance"].iloc[0]
    assert balance["status"] == "surpasses_arcgis"
    assert balance["metric_value"] == 0.0453
    assert balance["arcgis_reference"] == 0.0559
    default_erf = scorecard.loc[scorecard["criterion_id"] == "county_default_erf_gap"].iloc[0]
    preferred_erf = scorecard.loc[scorecard["criterion_id"] == "county_preferred_erf"].iloc[0]
    calibrated_erf = scorecard.loc[scorecard["criterion_id"] == "county_arcgis_style_calibrated_erf"].iloc[0]
    assert preferred_erf["status"] == "near_parity"
    assert preferred_erf["metric_value"] == 0.0429
    assert calibrated_erf["status"] == "near_parity"
    assert calibrated_erf["metric_value"] == 0.03
    assert default_erf["status"] == "diagnostic_gap"
    coverage = scorecard.loc[scorecard["criterion_id"] == "direct_arcgis_real_dataset_coverage"].iloc[0]
    assert coverage["status"] == "insufficient_evidence"
    synthetic = scorecard.loc[scorecard["criterion_id"] == "synthetic_fragility"].iloc[0]
    assert synthetic["status"] == "open_gap"
    assert synthetic["metric_value"] == 12
    epa = scorecard.loc[scorecard["criterion_id"] == "epa_known_truth_recovery"].iloc[0]
    assert epa["status"] == "passes_known_truth"
    overall = scorecard.loc[scorecard["criterion_id"] == "overall_arcgis_surpass_readiness"].iloc[0]
    assert overall["status"] == "not_yet_claimable"
    assert "additional real ArcGIS comparisons" in overall["next_action"]
    assert "default-ERF" not in overall["next_action"]

def test_paper6_benchmark_matrix_writer_outputs_surpass_scorecard(tmp_path):
    from data_agent.experiments.paper6_benchmark_matrix import write_paper6_benchmark_matrix

    paths = _write_fixture_inputs(tmp_path)

    manifest = write_paper6_benchmark_matrix(
        output_dir=tmp_path / "out_with_scorecard",
        arcgis_comparison_manifest=paths["arcgis_manifest"],
        method_comparison_csv=paths["method_comparison"],
        synthetic_scenario_summary_csv=paths["synthetic_summary"],
        epa_benchmark_summary_json=paths["epa_summary"],
    )

    scorecard_csv = Path(manifest["surpass_scorecard_csv"])
    scorecard_report = Path(manifest["surpass_scorecard_report_md"])
    assert scorecard_csv.exists()
    assert scorecard_report.exists()
    scorecard = pd.read_csv(scorecard_csv)
    overall = scorecard.loc[scorecard["criterion_id"] == "overall_arcgis_surpass_readiness"].iloc[0]
    assert overall["status"] == "not_yet_claimable"
    report = scorecard_report.read_text(encoding="utf-8")
    assert "Paper 6 ArcGIS Surpass Scorecard" in report
    assert "not_yet_claimable" in report
    assert "county_calibrated_balance" in report

def test_paper6_benchmark_matrix_accepts_multiple_arcgis_comparison_manifests(tmp_path):
    from data_agent.experiments.paper6_benchmark_matrix import (
        build_arcgis_surpass_scorecard,
        build_paper6_benchmark_matrix,
    )

    paths = _write_fixture_inputs(tmp_path)

    matrix = build_paper6_benchmark_matrix(
        arcgis_comparison_manifests=[paths["arcgis_manifest"], paths["soho_arcgis_manifest"]],
    )

    assert set(matrix["case_id"]) == {"county_arcgis_builtin", "soho_arcgis_builtin_relaxed"}
    soho = matrix.loc[matrix["case_id"] == "soho_arcgis_builtin_relaxed"].iloc[0]
    assert soho["sample_rows"] == 1814
    assert soho["arcgis_available"] is True
    assert soho["arcgis_balance"] == 0.1778
    assert soho["geocausal_calibrated_balance"] == 0.1109
    assert soho["preferred_erf_response_mae"] == 0.1481
    assert soho["arcgis_style_calibrated_erf_response_mae"] == 0.12
    assert "balance_threshold=0.2" in soho["evidence_summary"]

    scorecard = build_arcgis_surpass_scorecard(matrix, required_arcgis_real_rows=3)
    coverage = scorecard.loc[scorecard["criterion_id"] == "direct_arcgis_real_dataset_coverage"].iloc[0]
    assert coverage["metric_value"] == 2
    wins = scorecard.loc[scorecard["criterion_id"] == "direct_arcgis_calibrated_balance_wins"].iloc[0]
    assert wins["status"] == "surpasses_arcgis"
    assert wins["metric_value"] == 2
    assert wins["arcgis_reference"] == 2
