from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from geocausal.config import load_config
from geocausal.errors import GeoCausalConfigError
from geocausal.pipeline import diagnose_config, rebuild_report, run_analysis


REPO_ROOT = Path(__file__).resolve().parents[1]


def _fixture_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "unit_id": [f"u{i}" for i in range(1, 9)],
            "group": ["A", "A", "B", "B", "C", "C", "D", "D"],
            "x": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            "y": [0.0, 1.0, 0.5, 1.5, 2.0, 2.5, 3.0, 3.5],
            "exposure": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            "outcome": [2.0, 2.6, 3.5, 4.1, 5.2, 5.9, 6.8, 7.5],
            "baseline": [1.5, 1.7, 2.0, 2.2, 2.4, 2.5, 2.8, 3.0],
            "confounder": [1.0, 1.1, 1.6, 1.8, 2.3, 2.6, 3.0, 3.3],
            "context": [8.0, 7.5, 7.0, 6.4, 5.9, 5.3, 4.8, 4.2],
            "placebo": [7.0, 6.9, 6.7, 6.6, 6.5, 6.4, 6.2, 6.1],
        }
    )


def _write_fixture_config(
    tmp_path: Path,
    csv_name: str = "fixture.csv",
    *,
    include_bootstrap_group: bool = True,
    include_coordinates: bool = True,
) -> Path:
    config_path = tmp_path / "analysis.yaml"
    bootstrap_group = "    group_column: group\n" if include_bootstrap_group else ""
    coordinate_lines = "  x: x\n  y: y\n" if include_coordinates else ""
    config_path.write_text(
        f"""
case_name: geocausal_fixture
input:
  path: {csv_name}
{coordinate_lines.rstrip()}
variables:
  unit_id: unit_id
  exposure: exposure
  outcome: outcome
  baseline_outcome: baseline
  confounders:
    - baseline
    - confounder
context:
  columns:
    - context
robustness:
  placebo_exposures:
    - name: placebo_check
      column: placebo
      role: negative_control
      expected_relation: weaker_than_main
  bootstrap:
{bootstrap_group}    n_replicates: 5
output:
  directory: results/geocausal_fixture
""",
        encoding="utf-8",
    )
    return config_path


def test_diagnose_config_returns_rows_columns_and_warnings(tmp_path):
    _fixture_frame().to_csv(tmp_path / "fixture.csv", index=False)
    config = load_config(_write_fixture_config(tmp_path))
    diagnosis = diagnose_config(config)
    assert diagnosis["case_name"] == "geocausal_fixture"
    assert diagnosis["input_rows"] == 8
    assert diagnosis["input_columns"] >= 9
    assert diagnosis["output_writable"] is True
    assert diagnosis["errors"] == []


def test_diagnose_config_raises_for_missing_columns(tmp_path):
    _fixture_frame().drop(columns=["placebo"]).to_csv(tmp_path / "fixture.csv", index=False)
    config = load_config(_write_fixture_config(tmp_path))
    with pytest.raises(GeoCausalConfigError, match="placebo"):
        diagnose_config(config)


def test_run_analysis_writes_complete_output_package(tmp_path):
    _fixture_frame().to_csv(tmp_path / "fixture.csv", index=False)
    config = load_config(_write_fixture_config(tmp_path))
    manifest = run_analysis(config)
    output_dir = config.resolve_output_dir()
    expected_files = {
        "effect_estimates.csv",
        "erf_curve.csv",
        "context_ablation.csv",
        "placebo_tests.csv",
        "bootstrap_robustness.csv",
        "bootstrap_summary.json",
        "erf_stability.json",
        "robustness_report.md",
        "manifest.json",
    }
    assert expected_files.issubset({path.name for path in output_dir.iterdir()})
    assert manifest["case_name"] == "geocausal_fixture"
    assert manifest["exposure"] == "exposure"
    assert manifest["outcome"] == "outcome"
    assert manifest["row_count"] == 8
    assert manifest["files"]["manifest"] == "manifest.json"
    saved_manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest == saved_manifest
    assert len(manifest["warnings"]) == len(set(manifest["warnings"]))
    for relative_path in manifest["files"].values():
        assert (output_dir / relative_path).exists(), relative_path
    assert saved_manifest["robustness_interpretation"] in {
        "robust_support",
        "bounded_support",
        "fragile_support",
    }


def test_run_analysis_bootstrap_falls_back_to_input_coordinates(tmp_path):
    _fixture_frame().to_csv(tmp_path / "fixture.csv", index=False)
    config = load_config(_write_fixture_config(tmp_path, include_bootstrap_group=False))

    manifest = run_analysis(config)

    output_dir = config.resolve_output_dir()
    saved_manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest == saved_manifest
    for relative_path in manifest["files"].values():
        assert (output_dir / relative_path).exists(), relative_path
    bootstrap_rows = pd.read_csv(output_dir / "bootstrap_robustness.csv")
    assert not bootstrap_rows.empty


def test_run_analysis_bootstrap_falls_back_to_geojson_geometry(tmp_path):
    geopandas = pytest.importorskip("geopandas")
    shapely_geometry = pytest.importorskip("shapely.geometry")

    frame = _fixture_frame().drop(columns=["x", "y"])
    geo_frame = geopandas.GeoDataFrame(
        frame,
        geometry=[
            shapely_geometry.Point(-120.0 + offset, 35.0 + offset * 0.25)
            for offset in range(len(frame))
        ],
        crs="EPSG:4326",
    )
    geo_frame.to_file(tmp_path / "fixture.geojson", driver="GeoJSON")
    config = load_config(
        _write_fixture_config(
            tmp_path,
            csv_name="fixture.geojson",
            include_bootstrap_group=False,
            include_coordinates=False,
        )
    )

    manifest = run_analysis(config)

    output_dir = config.resolve_output_dir()
    saved_manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest == saved_manifest
    bootstrap_rows = pd.read_csv(output_dir / "bootstrap_robustness.csv")
    assert not bootstrap_rows.empty


def test_rebuild_report_uses_existing_manifest(tmp_path):
    output_dir = tmp_path / "results"
    output_dir.mkdir()
    (output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "case_name": "reported_case",
                "robustness_interpretation": "bounded_support",
                "files": {"manifest": "manifest.json"},
            }
        ),
        encoding="utf-8",
    )
    report = rebuild_report(output_dir)
    assert report["case_name"] == "reported_case"
    assert (output_dir / "geocausal_report.md").exists()
    assert "reported_case" in (output_dir / "geocausal_report.md").read_text(encoding="utf-8")


def test_cli_init_writes_template(tmp_path):
    output = tmp_path / "analysis.yaml"

    result = subprocess.run(
        [sys.executable, "-m", "geocausal.cli", "init", "--template", "scca", "--output", str(output)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert output.exists()
    assert "case_name:" in output.read_text(encoding="utf-8")
    assert json.loads(result.stdout)["path"] == str(output)


def test_cli_diagnose_and_run(tmp_path):
    _fixture_frame().to_csv(tmp_path / "fixture.csv", index=False)
    config_path = _write_fixture_config(tmp_path)

    diagnose_result = subprocess.run(
        [sys.executable, "-m", "geocausal.cli", "diagnose", str(config_path)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    run_result = subprocess.run(
        [sys.executable, "-m", "geocausal.cli", "run", str(config_path)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "geocausal_fixture" in diagnose_result.stdout
    assert any(
        support in run_result.stdout
        for support in ("bounded_support", "robust_support", "fragile_support")
    )
    assert (tmp_path / "results" / "geocausal_fixture" / "manifest.json").exists()


def test_cli_report_rebuilds_markdown(tmp_path):
    output_dir = tmp_path / "results"
    output_dir.mkdir()
    (output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "case_name": "reported_case",
                "robustness_interpretation": "bounded_support",
                "files": {"manifest": "manifest.json"},
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "geocausal.cli", "report", str(output_dir)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "reported_case" in result.stdout
    assert (output_dir / "geocausal_report.md").exists()
