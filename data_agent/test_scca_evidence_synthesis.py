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
        run_scca_evidence_synthesis,
    )

    manifest = run_scca_evidence_synthesis(output_dir=tmp_path)

    expected = {
        "synthesis_csv": tmp_path / "scca_evidence_synthesis.csv",
        "report_md": tmp_path / "scca_evidence_synthesis_report.md",
        "manifest_json": tmp_path / "scca_evidence_synthesis_manifest.json",
        "grade_rules_json": tmp_path / "scca_evidence_grade_rules.json",
        "grade_rules_md": tmp_path / "scca_evidence_grade_rules.md",
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
        "epa_nonattainment_airdata",
        "county_social_capital_spatial_notebook",
    }
    assert set(synthesis["case"]) == expected_cases
    assert "county_social_capital" not in set(synthesis["case"])
    assert set(synthesis["evidence_grade"]) == {"core_support", "bounded_support"}
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
