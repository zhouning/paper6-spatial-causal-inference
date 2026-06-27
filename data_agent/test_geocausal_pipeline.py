from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from geocausal.config import load_config
from geocausal.errors import GeoCausalConfigError
from geocausal.open_gis import write_open_gis_package
from geocausal.pipeline import diagnose_config, rebuild_report, run_analysis
from data_agent.scca.specs import SCCAPaths


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
        "spatial_diagnostics.json",
        "spatial_bootstrap_robustness.csv",
        "spatial_bootstrap_summary.json",
        "spatial_graph_sensitivity.csv",
        "spatial_graph_sensitivity_summary.json",
        "spatial_slx_estimates.csv",
        "spatial_slx_summary.json",
        "spatial_spillover_decomposition.csv",
        "spatial_spillover_summary.json",
        "spatial_exposure_mapping.csv",
        "spatial_exposure_mapping_summary.json",
        "result_summary.md",
        "robustness_report.md",
        "manifest.json",
    }
    assert expected_files.issubset({path.name for path in output_dir.iterdir()})
    assert manifest["case_name"] == "geocausal_fixture"
    assert manifest["exposure"] == "exposure"
    assert manifest["outcome"] == "outcome"
    assert manifest["row_count"] == 8
    assert manifest["evidence_grade"] in {"core_support", "bounded_support"}
    assert manifest["rule_version"]
    assert isinstance(manifest["evidence_grade_reasons"], list)
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
    assert "spatial_diagnostics" in manifest["files"]
    assert "spatial_bootstrap_robustness" in manifest["files"]
    assert "spatial_bootstrap_summary" in manifest["files"]
    assert "spatial_graph_sensitivity" in manifest["files"]
    assert "spatial_graph_sensitivity_summary" in manifest["files"]
    assert "spatial_slx_estimates" in manifest["files"]
    assert "spatial_slx_summary" in manifest["files"]
    assert "spatial_spillover_decomposition" in manifest["files"]
    assert "spatial_spillover_summary" in manifest["files"]
    assert "spatial_exposure_mapping" in manifest["files"]
    assert "spatial_exposure_mapping_summary" in manifest["files"]
    assert "result_summary_markdown" in manifest["files"]
    assert "result_summary" in manifest
    assert (output_dir / manifest["files"]["result_summary_markdown"]).exists()
    estimates = pd.read_csv(output_dir / "effect_estimates.csv")
    assert "spatial_neighbor_adjusted_ols" in set(estimates["estimator"])
    spatial_bootstrap = json.loads((output_dir / "spatial_bootstrap_summary.json").read_text(encoding="utf-8"))
    assert spatial_bootstrap["n_replicates_requested"] >= 5
    assert spatial_bootstrap["n_replicates_valid"] > 0
    assert manifest["result_summary"]["spatial_block_bootstrap"]["status"] == "ok"
    assert manifest["result_summary"]["spatial_graph_sensitivity"]["status"] == "ok"
    assert manifest["result_summary"]["spatial_slx_model"]["status"] in {"ok", "skipped", "unstable"}
    assert manifest["result_summary"]["spatial_spillover_decomposition"]["status"] == "ok"
    assert manifest["result_summary"]["spatial_exposure_mapping"]["status"] == "ok"
    spatial_lag_summary = manifest["result_summary"].get("spatial_lag_adjusted_ols", {})
    if "spatial_lag_adjusted_ols" in set(estimates["estimator"]):
        assert spatial_lag_summary.get("status") == "ok"
    report_text = (output_dir / "analysis_report.md").read_text(encoding="utf-8")
    assert "## Result Summary" in report_text
    assert "Spatial block bootstrap" in report_text
    assert "Spatial graph sensitivity" in report_text
    assert "Formal SLX output" in report_text
    assert "Spatial spillover decomposition" in report_text
    assert "Exposure mapping" in report_text
    result_summary_text = (output_dir / "result_summary.md").read_text(encoding="utf-8")
    assert "## Numeric Summary" in result_summary_text
    assert "Formal SLX output" in result_summary_text
    assert "Evidence grade" in result_summary_text


def test_run_analysis_supports_arcgis_style_trimming_and_targets(tmp_path):
    _fixture_frame().to_csv(tmp_path / "fixture.csv", index=False)
    config_path = tmp_path / "analysis.yaml"
    config_path.write_text(
        """
case_name: arcgis_compatible_fixture
input:
  path: fixture.csv
  x: x
  y: y
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
    group_column: group
    n_replicates: 5
preprocessing:
  exposure_trim:
    lower_quantile: 0.01
    upper_quantile: 0.99
targets:
  outcome_values:
    - name: outcome_target_7
      value: 7.0
output:
  directory: results/arcgis_compatible_fixture
""",
        encoding="utf-8",
    )
    config = load_config(config_path)

    manifest = run_analysis(config)

    output_dir = config.resolve_output_dir()
    assert (output_dir / "target_exposures.csv").exists()
    assert manifest["case_name"] == "arcgis_compatible_fixture"
    assert manifest["row_count"] == 6
    assert manifest["preprocessing"]["exposure_trim"]["removed_n"] == 2
    assert manifest["files"]["target_exposures"] == "target_exposures.csv"

    targets = pd.read_csv(output_dir / "target_exposures.csv")
    assert set(targets.columns) >= {
        "unit_id",
        "method",
        "target_name",
        "target_outcome",
        "current_exposure",
        "required_exposure",
        "exposure_change",
    }
    assert set(targets["target_name"]) == {"outcome_target_7"}
    assert set(targets["method"]) == {"adjusted_ols_prediction", "erf_delta_anchor"}


def test_run_analysis_writes_open_gis_parity_package(tmp_path):
    _fixture_frame().to_csv(tmp_path / "fixture.csv", index=False)
    config = load_config(_write_fixture_config(tmp_path))

    manifest = run_analysis(config)

    output_dir = config.resolve_output_dir()
    package_dir = output_dir / "open_gis_analysis_package"
    expected_files = {
        "analysis_joined.csv",
        "gis_balance_summary.csv",
        "gis_erf_curve_200.csv",
        "gis_run_summary.json",
        "gis_run_summary.md",
    }
    assert expected_files.issubset({path.name for path in package_dir.iterdir()})
    assert manifest["files"]["open_gis_analysis_package"] == "open_gis_analysis_package"
    assert manifest["open_gis_package"]["package_dir"] == "open_gis_analysis_package"

    joined = pd.read_csv(package_dir / "analysis_joined.csv")
    assert {
        "gc_unit_id",
        "gc_exposure",
        "gc_outcome",
        "gc_propensity_score",
        "gc_balancing_weight",
        "gc_included",
        "gc_trim_status",
    }.issubset(joined.columns)
    assert len(joined) == manifest["row_count"]
    assert joined["gc_included"].all()
    assert joined["gc_balancing_weight"].notna().all()

    balance = pd.read_csv(package_dir / "gis_balance_summary.csv")
    assert {"baseline", "confounder", "context"}.issubset(set(balance["variable"]))
    assert {
        "raw_correlation",
        "weighted_correlation",
        "absolute_weighted_correlation",
        "balanced_at_0_1",
    }.issubset(balance.columns)

    erf_200 = pd.read_csv(package_dir / "gis_erf_curve_200.csv")
    assert len(erf_200) == 200
    assert {"exposure", "response", "source"}.issubset(erf_200.columns)
    assert set(erf_200["source"]) == {"interpolated_from_erf_curve"}

    summary = json.loads((package_dir / "gis_run_summary.json").read_text(encoding="utf-8"))
    assert summary["case_name"] == "geocausal_fixture"
    assert summary["generated_files"]["analysis_joined"] == "analysis_joined.csv"
    assert summary["evidence_grade"] in {"core_support", "bounded_support", "fragile_support"}
    assert "Open GIS" in (package_dir / "gis_run_summary.md").read_text(encoding="utf-8")


def test_open_gis_balance_summary_aligns_weights_by_row_position(tmp_path):
    features = pd.DataFrame(
        {
            "unit_id": ["u10", "u20", "u30", "u40"],
            "exposure": [1.0, 2.0, 3.0, 4.0],
            "outcome": [2.0, 2.5, 3.2, 4.3],
            "confounder": [1.0, 2.1, 2.7, 4.4],
            "context": [10.0, 9.5, 7.2, 6.0],
        },
        index=[10, 20, 30, 40],
    )
    config_path = tmp_path / "analysis.yaml"
    config_path.write_text(
        """
case_name: open_gis_index_alignment
input:
  path: fixture.csv
variables:
  unit_id: unit_id
  exposure: exposure
  outcome: outcome
  confounders:
    - confounder
context:
  columns:
    - context
robustness:
  bootstrap:
    group_column: unit_id
    n_replicates: 3
output:
  directory: results/open_gis_index_alignment
""",
        encoding="utf-8",
    )
    config = load_config(config_path)
    spec = config.to_study_spec()
    paths = SCCAPaths(output_dir=config.resolve_output_dir())
    paths.ensure()
    pd.DataFrame(
        {
            "unit_id": ["u10", "u20", "u30", "u40"],
            "gc_propensity_score": [0.2, 0.4, 0.8, 1.2],
            "gc_balancing_weight": [1.0, 2.0, 3.0, 4.0],
        }
    ).to_csv(paths.generalized_propensity_scores, index=False)
    pd.DataFrame(
        {
            "exposure": [1.0, 4.0],
            "response": [2.0, 4.3],
        }
    ).to_csv(paths.erf_curve, index=False)

    write_open_gis_package(
        config=config,
        features=features,
        spec=spec,
        paths=paths,
        manifest={
            "row_count": 4,
            "evidence_grade": "core_support",
            "evidence_grade_reasons": [],
            "result_summary": {},
        },
    )

    balance = pd.read_csv(paths.output_dir / "open_gis_analysis_package" / "gis_balance_summary.csv")
    assert set(balance["variable"]) == {"confounder", "context"}
    assert balance["weighted_correlation"].notna().all()
    assert balance["n_complete"].tolist() == [4, 4]


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


def test_run_analysis_writes_spatial_diagnostics_for_county_shapefile(tmp_path):
    pytest.importorskip("geopandas")

    county_path = REPO_ROOT / "data" / "CountyData.shp"
    if not county_path.exists():
        pytest.skip("County shapefile fixture is unavailable.")

    config_path = tmp_path / "analysis.yaml"
    config_path.write_text(
        f"""
case_name: county_shapefile_spatial_smoke
input:
  path: {county_path}
variables:
  unit_id: FIPS
  exposure: SocialAsso
  outcome: AveAgeDeat
  confounders:
    - UnemployRa
    - pHHinPover
    - pNoHealthI
context:
  columns:
    - Shape_Leng
    - Shape_Area
robustness:
  bootstrap:
    group_column: STATE_NAME
    n_replicates: 3
output:
  directory: results/county_shapefile_spatial_smoke
""",
        encoding="utf-8",
    )
    config = load_config(config_path)

    manifest = run_analysis(config)

    output_dir = config.resolve_output_dir()
    diagnostics = json.loads((output_dir / "spatial_diagnostics.json").read_text(encoding="utf-8"))
    assert manifest["files"]["spatial_diagnostics"] == "spatial_diagnostics.json"
    assert diagnostics["graph"]["method"] in {"geometry_touches", "coordinate_knn", "unavailable"}
    assert "graph" in diagnostics
    assert "residual_moran" in diagnostics


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
