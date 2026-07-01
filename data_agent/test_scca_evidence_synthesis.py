import json

import pandas as pd


def test_scca_evidence_synthesis_prefers_tracked_county_spatial_summary(tmp_path):
    from data_agent.experiments.scca_evidence_synthesis import build_scca_evidence_table

    summary_dir = tmp_path / "scca_robustness_summary"
    summary_dir.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "case": "county_social_capital",
                "main_coef": 0.147,
                "ablation_direction_stable": True,
                "placebo_weaker_than_main": True,
                "bootstrap_sign_stability": 1.0,
                "erf_monotonic_direction": "increasing",
                "robustness_interpretation": "robust_support",
                "main_limitation": "No credibility downgrade warnings were triggered.",
            }
        ]
    ).to_csv(summary_dir / "case_robustness_summary.csv", index=False)

    tracked_summary = {
        "result_summary": {
            "baseline_adjusted_ols": {"coef": 0.1812445027},
            "spatial_lag_adjusted_ols": {"coef": 0.1445547494},
            "spatial_slx_model": {"total_effect": 0.2145094523},
            "spatial_diagnostics": {"residual_moran_i": 0.3127560212},
            "spatial_block_bootstrap": {"sign_stability": 1.0},
            "spatial_graph_sensitivity": {"neighbor_adjusted_sign_stability": True},
        },
        "spatial_manifest": {
            "row_count": 3108,
            "matched_count": 3044,
            "enriched_effect_fields": [
                "gc_spatial_direct_effect",
                "gc_spatial_indirect_effect",
            ],
        },
    }
    (tmp_path / "county_social_capital_spatial_notebook_summary.json").write_text(
        json.dumps(tracked_summary),
        encoding="utf-8",
    )

    synthesis = build_scca_evidence_table(tmp_path)

    assert "county_social_capital_spatial_notebook" in set(synthesis["case"])
    assert "county_social_capital" not in set(synthesis["case"])


def test_scca_evidence_synthesis_writes_contract_files(tmp_path):
    from data_agent.experiments.scca_evidence_synthesis import (
        build_residual_moran_threshold_sensitivity,
        build_chongqing_reviewer_audit_package,
        build_chongqing_variable_role_audit,
        run_scca_evidence_synthesis,
    )

    manifest = run_scca_evidence_synthesis(output_dir=tmp_path)

    expected = {
        "synthesis_csv": tmp_path / "scca_evidence_synthesis.csv",
        "report_md": tmp_path / "scca_evidence_synthesis_report.md",
        "manifest_json": tmp_path / "scca_evidence_synthesis_manifest.json",
        "grade_rules_json": tmp_path / "scca_evidence_grade_rules.json",
        "grade_rules_md": tmp_path / "scca_evidence_grade_rules.md",
        "threshold_sensitivity_csv": tmp_path / "scca_grade_threshold_sensitivity.csv",
        "threshold_sensitivity_md": tmp_path / "scca_grade_threshold_sensitivity.md",
        "chongqing_variable_role_audit_csv": tmp_path / "chongqing_variable_role_audit.csv",
        "chongqing_variable_role_audit_md": tmp_path / "chongqing_variable_role_audit.md",
        "chongqing_reviewer_audit_package_csv": tmp_path / "chongqing_reviewer_audit_package.csv",
        "chongqing_reviewer_audit_package_json": tmp_path / "chongqing_reviewer_audit_package.json",
    }
    for key, path in expected.items():
        assert manifest[key] == str(path)
        assert path.exists()

    synthesis = pd.read_csv(expected["synthesis_csv"])
    required_columns = {
        "case",
        "data_type",
        "exposure",
        "outcome",
        "context_source",
        "best_adjustment",
        "effect_estimate",
        "balance_status",
        "robustness_status",
        "evidence_grade",
        "grade_rule_ids",
        "grade_reasons",
        "limitation",
        "manuscript_use",
    }
    assert required_columns.issubset(synthesis.columns)
    expected_cases = {
        "synthetic_benchmark_audit",
        "chongqing_uhi",
        "county_social_capital_spatial_notebook",
    }
    assert set(synthesis["case"]) == expected_cases
    assert "county_social_capital" not in set(synthesis["case"])
    assert set(synthesis["evidence_grade"]) == {"bounded_support"}
    assert synthesis.loc[
        synthesis["case"] == "chongqing_uhi",
        "grade_rule_ids",
    ].str.contains("material_residual_moran").any()
    assert synthesis.loc[
        synthesis["case"] == "county_social_capital_spatial_notebook",
        "evidence_grade",
    ].iloc[0] == "bounded_support"
    assert synthesis.loc[
        synthesis["case"] == "county_social_capital_spatial_notebook",
        "grade_rule_ids",
    ].str.contains("material_residual_moran").any()
    assert synthesis.loc[
        synthesis["case"] == "county_social_capital_spatial_notebook",
        "robustness_status",
    ].str.contains("residual Moran I").any()

    report_text = expected["report_md"].read_text(encoding="utf-8")
    assert "county_social_capital_spatial_notebook" in report_text
    assert "county_social_capital\n" not in report_text
    assert report_text.count("### ") == len(expected_cases)

    payload = json.loads(expected["manifest_json"].read_text(encoding="utf-8"))
    assert payload["n_rows"] == len(synthesis)
    assert payload["rule_version"]
    assert payload["threshold_sensitivity_csv"] == str(expected["threshold_sensitivity_csv"])
    assert payload["chongqing_variable_role_audit_csv"] == str(expected["chongqing_variable_role_audit_csv"])
    assert payload["chongqing_reviewer_audit_package_json"] == str(expected["chongqing_reviewer_audit_package_json"])

    sensitivity = pd.read_csv(expected["threshold_sensitivity_csv"])
    required_sensitivity_columns = {
        "case",
        "residual_moran_i",
        "residual_moran_p_value",
        "residual_moran_abs_threshold",
        "evidence_grade",
        "grade_rule_ids",
        "residual_moran_status",
        "diagnostic_flags",
    }
    assert required_sensitivity_columns.issubset(sensitivity.columns)
    assert {
        "chongqing_full_rs_context",
        "county_social_capital_spatial_notebook",
    }.issubset(set(sensitivity["case"]))
    assert sensitivity.loc[
        (sensitivity["case"] == "chongqing_full_rs_context")
        & (sensitivity["residual_moran_abs_threshold"] == 0.10),
        "evidence_grade",
    ].iloc[0] == "bounded_support"
    assert sensitivity.loc[
        (sensitivity["case"] == "chongqing_full_rs_context")
        & (sensitivity["residual_moran_abs_threshold"] == 0.20),
        "residual_moran_status",
    ].iloc[0] == "significant_below_material_threshold"

    rebuilt = build_residual_moran_threshold_sensitivity(thresholds=(0.10, 0.20))
    assert set(rebuilt["residual_moran_abs_threshold"]) == {0.10, 0.20}

    role_audit = pd.read_csv(expected["chongqing_variable_role_audit_csv"])
    assert {
        "context_group",
        "causal_role",
        "main_model_use",
        "post_treatment_risk",
        "sensitivity_variant",
        "sensitivity_att_c",
        "sensitivity_max_post_smd",
    }.issubset(role_audit.columns)
    assert "ambiguous proxy or mediator" in set(role_audit["causal_role"])
    assert role_audit["post_treatment_risk"].isin(["low", "medium", "high"]).all()

    public_audit = pd.read_csv(expected["chongqing_reviewer_audit_package_csv"])
    assert {
        "item",
        "value",
        "source_file",
        "privacy_status",
    }.issubset(public_audit.columns)
    assert set(public_audit["privacy_status"]) == {"non_sensitive_aggregate"}

    rebuilt_roles = build_chongqing_variable_role_audit()
    assert not rebuilt_roles.empty
    rebuilt_package = build_chongqing_reviewer_audit_package()
    assert not rebuilt_package.empty
