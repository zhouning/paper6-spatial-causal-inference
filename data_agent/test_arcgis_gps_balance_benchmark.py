from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_arcgis_gps_balance_benchmark_writes_gbm_balance_win(tmp_path):
    from data_agent.experiments.arcgis_gps_balance_benchmark import (
        write_arcgis_gps_balance_benchmark,
    )

    manifest = write_arcgis_gps_balance_benchmark(output_dir=tmp_path)

    csv_path = Path(manifest["benchmark_csv"])
    json_path = Path(manifest["manifest_json"])
    assert csv_path.exists()
    assert json_path.exists()
    assert manifest["selected_gps_method"] == "gbm"
    assert manifest["gbm_beats_ols"] is True
    assert manifest["candidate_count"] == 2

    rows = pd.read_csv(csv_path)
    assert set(rows["gps_method"]) == {"ols", "gbm"}
    ols = rows.loc[rows["gps_method"] == "ols"].iloc[0]
    gbm = rows.loc[rows["gps_method"] == "gbm"].iloc[0]
    assert gbm["mean_abs_weighted_correlation"] < ols["mean_abs_weighted_correlation"]
    assert gbm["max_abs_weighted_correlation"] <= ols["max_abs_weighted_correlation"]
