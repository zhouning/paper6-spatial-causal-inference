from pathlib import Path

import pandas as pd


def test_chongqing_uhi_notebook_demo_contract(tmp_path):
    from notebooks.run_chongqing_uhi_demo import INPUT_CSV, run_demo

    summary = run_demo(
        output_dir=tmp_path / "chongqing_uhi_notebook_demo",
        input_csv=INPUT_CSV,
        n_bootstrap=12,
        n_spatial_bootstrap=8,
        random_state=0,
    )

    assert summary["case_name"] == "chongqing_uhi_notebook_demo"
    assert Path(summary["narrative_summary_markdown"]).exists()

    result = summary["result_summary"]
    assert result["row_count"] == 5000
    assert result["treatment_count"] == 2500
    assert result["control_count"] == 2500
    assert result["ablation_rows"] >= 8
    assert result["balance_rows"] > 0
    assert result["bootstrap_rows"] == 16
    assert result["placebo_rows"] == 6
    assert result["residual_rows"] == 2
    assert result["balance_interpretation"] in {"credible_balance", "bounded_balance", "failed_balance"}
    assert result["full_rs_context_att"] is not None
    assert result["full_rs_context_max_post_smd"] is not None

    manifest = summary["analysis_manifest"]
    for key in (
        "ablation_csv",
        "balance_csv",
        "matched_counts_csv",
        "bootstrap_csv",
        "placebo_csv",
        "residual_csv",
        "manifest_json",
        "report_md",
    ):
        assert Path(manifest[key]).exists()

    ablation = pd.read_csv(manifest["ablation_csv"])
    assert "full_rs_context" in set(ablation["variant"])

    spatial = summary["spatial_manifest"]
    assert Path(spatial["points_csv"]).exists()
    assert spatial["point_count"] == 5000
    assert Path(spatial["geojson"]).exists()
    assert Path(spatial["gpkg"]).exists()

    visualizations = summary["visualization_manifest"]
    for key in ("att_variants_png", "balance_png", "lst_points_png", "lst_points_html"):
        assert Path(visualizations[key]).exists()
