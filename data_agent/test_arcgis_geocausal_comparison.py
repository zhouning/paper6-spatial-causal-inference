from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _write_arcgis_fixture(tmp_path: Path) -> Path:
    arcgis_dir = tmp_path / "arcgis"
    arcgis_dir.mkdir()
    features_csv = arcgis_dir / "arcgis_features.csv"
    erf_csv = arcgis_dir / "arcgis_erf.csv"
    pd.DataFrame({"RECRD_USED": [1, 0, 1]}).to_csv(features_csv, index=False)
    pd.DataFrame(
        {"EXPOSURE": [1.0, 2.0, 3.0], "RESPONSE": [10.0, 12.0, 14.0]}
    ).to_csv(erf_csv, index=False)
    manifest = {
        "tool": "arcpy.stats.CausalInferenceAnalysis",
        "summary": {
            "original_n": 3,
            "exposure_trimmed_n": 1,
            "final_n": 2,
            "mean_weighted_correlation": 0.0559,
        },
        "output_csvs": {
            "out_features_csv": str(features_csv),
            "out_erf_table_csv": str(erf_csv),
        },
    }
    manifest_path = arcgis_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def _write_open_gis_fixture(tmp_path: Path) -> Path:
    open_dir = tmp_path / "open_gis_analysis_package"
    open_dir.mkdir()
    pd.DataFrame({"gc_unit_id": ["a", "c"]}).to_csv(open_dir / "analysis_joined.csv", index=False)
    pd.DataFrame(
        {"exposure": [1.0, 2.0, 3.0], "response": [11.0, 12.0, 13.0]}
    ).to_csv(open_dir / "gis_erf_curve_200.csv", index=False)
    pd.DataFrame(
        {"exposure": [1.0, 2.0, 3.0], "response": [10.2, 12.1, 13.8]}
    ).to_csv(open_dir / "gis_arcgis_style_erf_curve_200.csv", index=False)
    pd.DataFrame(
        [
            {"variable": "x1", "role": "confounder", "absolute_weighted_correlation": 0.04},
            {"variable": "x2", "role": "confounder", "absolute_weighted_correlation": 0.06},
            {"variable": "ctx", "role": "context", "absolute_weighted_correlation": 0.20},
        ]
    ).to_csv(open_dir / "gis_balance_summary.csv", index=False)
    pd.DataFrame(
        [
            {"num_bins": 7, "scale": 0.6, "mean_abs_weighted_correlation": 0.03, "selected": False},
            {"num_bins": 7, "scale": 0.8, "mean_abs_weighted_correlation": 0.02, "selected": True},
        ]
    ).to_csv(open_dir / "arcgis_style_matching_grid.csv", index=False)
    pd.DataFrame(
        [
            {"variable": "x1", "role": "confounder", "absolute_weighted_correlation": 0.01},
            {"variable": "x2", "role": "confounder", "absolute_weighted_correlation": 0.03},
        ]
    ).to_csv(open_dir / "arcgis_style_balance_summary.csv", index=False)
    pd.DataFrame(
        [
            {"variable": "x1", "role": "confounder", "absolute_weighted_correlation": 0.005},
            {"variable": "x2", "role": "confounder", "absolute_weighted_correlation": 0.015},
        ]
    ).to_csv(open_dir / "arcgis_style_calibrated_balance_summary.csv", index=False)
    (open_dir / "gis_run_summary.json").write_text(
        json.dumps({"evidence_grade": "core_support"}), encoding="utf-8"
    )
    return open_dir


def test_build_arcgis_geocausal_comparison_writes_metrics_and_report(tmp_path):
    from geocausal.arcgis_comparison import build_arcgis_geocausal_comparison

    manifest = build_arcgis_geocausal_comparison(
        arcgis_manifest_path=_write_arcgis_fixture(tmp_path),
        open_gis_dir=_write_open_gis_fixture(tmp_path),
        output_dir=tmp_path / "comparison",
    )

    assert Path(manifest["comparison_csv"]).exists()
    assert Path(manifest["report_md"]).exists()
    assert Path(manifest["manifest_json"]).exists()
    assert manifest["metrics"]["arcgis_final_n"] == 2
    assert manifest["metrics"]["geocausal_joined_rows"] == 2
    assert manifest["metrics"]["arcgis_erf_rows"] == 3
    assert manifest["metrics"]["geocausal_erf_rows"] == 3
    assert round(manifest["metrics"]["erf_response_mae"], 4) == 0.6667
    assert round(manifest["metrics"]["erf_response_rmse"], 4) == 0.8165
    assert manifest["metrics"]["geocausal_arcgis_style_erf_rows"] == 3
    assert round(manifest["metrics"]["arcgis_style_erf_response_mae"], 4) == 0.1667
    assert round(manifest["metrics"]["arcgis_style_erf_response_rmse"], 4) == 0.1732
    assert manifest["metrics"]["geocausal_confounder_mean_abs_weighted_correlation"] == 0.05
    assert manifest["metrics"]["geocausal_arcgis_style_confounder_mean_abs_weighted_correlation"] == 0.02
    assert manifest["metrics"]["geocausal_arcgis_style_selected_num_bins"] == 7
    assert manifest["metrics"]["geocausal_arcgis_style_selected_scale"] == 0.8
    assert manifest["metrics"]["geocausal_arcgis_style_calibrated_confounder_mean_abs_weighted_correlation"] == 0.01

    table = pd.read_csv(manifest["comparison_csv"])
    rows = dict(zip(table["metric"], table["status"]))
    assert rows["analysis_rows"] == "match"
    assert rows["erf_rows"] == "match"
    assert rows["arcgis_style_erf_response_mae"] == "computed"
    assert rows["mean_weighted_balance"] == "geocausal_lower"
    assert rows["arcgis_style_mean_weighted_balance"] == "geocausal_lower"
    assert rows["arcgis_style_calibrated_mean_weighted_balance"] == "geocausal_lower"

    report = Path(manifest["report_md"]).read_text(encoding="utf-8")
    assert "ArcGIS vs GeoCausal Benchmark" in report
    assert "ERF response MAE" in report
    assert "ArcGIS-style ERF response MAE" in report
    assert "GeoCausal ArcGIS-style confounder mean absolute weighted balance" in report
    assert "GeoCausal ArcGIS-style calibrated confounder mean absolute weighted balance" in report


def test_cli_arcgis_compare_prints_manifest(tmp_path, monkeypatch, capsys):
    from geocausal import cli

    captured = {}

    def fake_compare(*, arcgis_manifest_path, open_gis_dir, output_dir):
        captured["arcgis_manifest_path"] = arcgis_manifest_path
        captured["open_gis_dir"] = open_gis_dir
        captured["output_dir"] = output_dir
        return {"comparison_csv": "comparison.csv", "metrics": {"arcgis_final_n": 2}}

    monkeypatch.setattr(cli, "build_arcgis_geocausal_comparison", fake_compare)

    status = cli.main(
        [
            "arcgis-compare",
            "--arcgis-manifest",
            str(tmp_path / "arcgis.json"),
            "--open-gis-dir",
            str(tmp_path / "open_gis"),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert status == 0
    assert captured == {
        "arcgis_manifest_path": tmp_path / "arcgis.json",
        "open_gis_dir": tmp_path / "open_gis",
        "output_dir": tmp_path / "out",
    }
    assert "comparison.csv" in capsys.readouterr().out
