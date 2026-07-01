from pathlib import Path

import numpy as np
import pandas as pd


LOCAL_CHONGQING_SAMPLE = (
    Path(__file__).resolve().parent.parent
    / "paper"
    / "ijgis_submission_20260605"
    / "07_results"
    / "chongqing_uhi_analysis_sample.csv"
)


def _notebook_fixture(row_count: int = 256) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    rows = []
    for idx in range(row_count):
        treated = 1 if idx < row_count // 2 else 0
        block = idx % 32
        local = idx // 32
        centroid_x = 106.30 + 0.004 * block + 0.0002 * local
        centroid_y = 29.30 + 0.003 * block + 0.00015 * local
        elevation = 220.0 + 1.5 * block + 0.2 * local
        ndbi = 0.08 + 0.001 * block + 0.01 * treated
        ndvi = 0.42 - 0.0015 * block - 0.015 * treated
        lst = 30.5 + 0.22 * treated + 0.5 * ndbi - 0.15 * ndvi - 0.002 * elevation
        rows.append(
            {
                "Id": idx + 1,
                "floor": 12 if treated else 6,
                "treatment": treated,
                "centroid_x": centroid_x,
                "centroid_y": centroid_y,
                "area_m2": 90.0 + 2.0 * block + float(rng.normal(0, 0.2)),
                "LST": lst,
                "rs_B2": 0.12 + 0.0005 * block,
                "rs_B3": 0.14 + 0.0005 * block,
                "rs_B4": 0.16 + 0.0005 * block,
                "rs_B8": 0.20 + 0.0003 * block,
                "rs_B11": 0.24 + 0.0003 * block,
                "rs_B12": 0.28 + 0.0003 * block,
                "rs_NDVI": ndvi,
                "rs_NDBI": ndbi,
                "rs_MNDWI": -0.04 + 0.0007 * block,
                "rs_BSI": 0.06 + 0.0008 * block,
                "rs_elevation": elevation,
                "rs_slope": 4.0 + 0.05 * block,
            }
        )
    return pd.DataFrame(rows)


def _input_csv_for_notebook_contract(tmp_path: Path) -> tuple[Path, int, int, int]:
    if LOCAL_CHONGQING_SAMPLE.exists():
        frame = pd.read_csv(LOCAL_CHONGQING_SAMPLE, usecols=["treatment"])
        treatment = pd.to_numeric(frame["treatment"], errors="coerce")
        return (
            LOCAL_CHONGQING_SAMPLE,
            int(len(frame)),
            int(treatment.sum()),
            int((treatment == 0).sum()),
        )

    input_csv = tmp_path / "chongqing_uhi_fixture.csv"
    frame = _notebook_fixture()
    frame.to_csv(input_csv, index=False)
    return input_csv, int(len(frame)), 128, 128


def test_chongqing_uhi_notebook_demo_contract(tmp_path):
    from notebooks.run_chongqing_uhi_demo import run_demo

    input_csv, expected_rows, expected_treated, expected_control = _input_csv_for_notebook_contract(tmp_path)

    summary = run_demo(
        output_dir=tmp_path / "chongqing_uhi_notebook_demo",
        input_csv=input_csv,
        n_bootstrap=12,
        n_spatial_bootstrap=8,
        random_state=0,
    )

    assert summary["case_name"] == "chongqing_uhi_notebook_demo"
    assert Path(summary["narrative_summary_markdown"]).exists()

    result = summary["result_summary"]
    assert result["row_count"] == expected_rows
    assert result["treatment_count"] == expected_treated
    assert result["control_count"] == expected_control
    assert result["ablation_rows"] >= 8
    assert result["balance_rows"] > 0
    assert result["bootstrap_rows"] == 16
    assert result["placebo_rows"] == 6
    assert result["residual_rows"] == 3
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
    assert spatial["point_count"] == expected_rows
    assert Path(spatial["geojson"]).exists()
    assert Path(spatial["gpkg"]).exists()

    visualizations = summary["visualization_manifest"]
    for key in ("att_variants_png", "balance_png", "lst_points_png", "lst_points_html"):
        assert Path(visualizations[key]).exists()
