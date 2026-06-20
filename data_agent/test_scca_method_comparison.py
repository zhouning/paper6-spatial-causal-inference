import json

import pandas as pd


def test_scca_method_comparison_tracks_county_spatial_downgrade_and_chongqing_balance_gain(tmp_path):
    from data_agent.experiments.scca_method_comparison import build_scca_method_comparison

    arcgis_dir = tmp_path / "arcgis_toolbox_demo" / "county_social_capital_arcgis_demo"
    arcgis_dir.mkdir(parents=True)
    (arcgis_dir / "manifest.json").write_text(
        json.dumps(
            {
                "credibility_decision": "strong_support",
                "robustness_interpretation": "robust_support",
                "preprocessing": {"exposure_trim": {"kept_n": 3044, "removed_n": 64}},
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        [{"estimator": "baseline_adjusted_ols", "coef": 0.1812445027}]
    ).to_csv(arcgis_dir / "effect_estimates.csv", index=False)

    (tmp_path / "county_social_capital_spatial_notebook_summary.json").write_text(
        json.dumps(
            {
                "result_summary": {
                    "spatial_lag_adjusted_ols": {
                        "coef": 0.1445547494,
                        "relative_change": 0.2024323647,
                    },
                    "spatial_diagnostics": {
                        "residual_moran_i": 0.3127560212,
                        "residual_moran_p_value": 0.01,
                    },
                    "spatial_graph_sensitivity": {
                        "neighbor_adjusted_relative_change_max": 0.2054307562,
                        "neighbor_adjusted_sign_stability": True,
                    },
                },
                "spatial_manifest": {"matched_count": 3044, "row_count": 3108},
            }
        ),
        encoding="utf-8",
    )

    pd.DataFrame(
        [
            {
                "variant": "raw",
                "att": 0.2377372286,
                "max_post_smd": None,
                "balance_pass_0_1": False,
                "matched_treated_n": 2500,
                "matched_control_n": 2500,
            },
            {
                "variant": "full_rs_context",
                "att": 0.2441250110,
                "max_post_smd": 0.0613070923,
                "balance_pass_0_1": True,
                "matched_treated_n": 1621,
                "matched_control_n": 1621,
            },
        ]
    ).to_csv(tmp_path / "chongqing_uhi_ablation.csv", index=False)
    pd.DataFrame(
        [
            {
                "variant": "full_rs_context",
                "moran_i": 0.1017969541,
                "permutation_p_value": 0.01,
                "status": "ok",
            }
        ]
    ).to_csv(tmp_path / "chongqing_residual_spatial_diagnostics.csv", index=False)

    comparison = build_scca_method_comparison(tmp_path)

    assert {
        "county_nonspatial_vs_spatial",
        "chongqing_raw_vs_full_scca",
    }.issubset(set(comparison["comparison_id"]))

    county = comparison.loc[
        comparison["comparison_id"] == "county_nonspatial_vs_spatial"
    ].iloc[0]
    assert county["baseline_grade"] == "core_support"
    assert county["enhanced_grade"] == "bounded_support"
    assert county["effect_delta_rel"] < 0
    assert county["enhanced_residual_moran_i"] > 0.3

    chongqing = comparison.loc[
        comparison["comparison_id"] == "chongqing_raw_vs_full_scca"
    ].iloc[0]
    assert chongqing["baseline_balance_pass"] is False
    assert chongqing["enhanced_balance_pass"] is True
    assert chongqing["enhanced_grade"] == "core_support"


def test_scca_method_comparison_writes_contract_files(tmp_path):
    from data_agent.experiments.scca_method_comparison import run_scca_method_comparison

    # Reuse the build-contract expectations with minimal empty input support.
    manifest = run_scca_method_comparison(output_dir=tmp_path, results_dir=tmp_path)

    expected = {
        "comparison_csv": tmp_path / "scca_method_comparison.csv",
        "report_md": tmp_path / "scca_method_comparison_report.md",
        "manifest_json": tmp_path / "scca_method_comparison_manifest.json",
    }
    for key, path in expected.items():
        assert manifest[key] == str(path)
        assert path.exists()
