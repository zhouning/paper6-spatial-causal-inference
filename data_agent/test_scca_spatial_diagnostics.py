from __future__ import annotations

import json

import pandas as pd
import pytest

from data_agent.scca.spatial_diagnostics import run_spatial_diagnostics
from data_agent.scca.spatial_diagnostics import append_spatial_adjusted_estimate
from data_agent.scca.spatial_diagnostics import build_spatial_graph, run_spatial_block_bootstrap
from data_agent.scca.specs import SCCAPaths, StudySpec


def _line_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "unit_id": [f"u{i}" for i in range(6)],
            "x": [float(i) for i in range(6)],
            "y": [0.0] * 6,
            "exposure": [float(i) for i in range(6)],
            "outcome": [2.0 + i * 1.5 for i in range(6)],
            "confounder": [0.5 + i * 0.1 for i in range(6)],
            "context": [10.0 - i * 0.2 for i in range(6)],
        }
    )


def _spec() -> StudySpec:
    return StudySpec(
        name="spatial_fixture",
        unit_id="unit_id",
        exposure="exposure",
        outcome="outcome",
        confounders=("confounder",),
        context_columns=("context",),
        coordinate_columns=("x", "y"),
    )


def test_spatial_diagnostics_uses_coordinate_knn_and_writes_json(tmp_path):
    frame = _line_fixture()
    paths = SCCAPaths(output_dir=tmp_path)

    diagnostics = run_spatial_diagnostics(
        frame,
        _spec(),
        paths,
        baseline_exposure_coef=1.5,
        n_permutations=9,
    )

    assert diagnostics["graph"]["method"] == "coordinate_knn"
    assert diagnostics["graph"]["edge_count"] > 0
    assert diagnostics["exposure_moran"]["status"] == "ok"
    assert diagnostics["residual_moran"]["status"] in {"ok", "skipped"}
    assert diagnostics["neighbor_exposure_model"]["status"] in {"ok", "skipped", "unstable"}
    assert diagnostics["spatial_lag_model"]["status"] in {"ok", "skipped", "unstable"}
    assert diagnostics["spatial_slx_model"]["status"] in {"ok", "skipped", "unstable"}
    assert diagnostics["graph_sensitivity_summary"]["status"] in {"ok", "skipped"}
    assert diagnostics["spillover_summary"]["status"] in {"ok", "skipped"}
    assert diagnostics["exposure_mapping_summary"]["status"] in {"ok", "skipped"}
    if diagnostics["neighbor_exposure_model"]["status"] == "ok":
        assert "spatial_adjustment_sensitivity" in diagnostics["neighbor_exposure_model"]
    saved = json.loads(paths.spatial_diagnostics.read_text(encoding="utf-8"))
    assert saved == diagnostics
    assert paths.spatial_graph_sensitivity.exists()
    assert paths.spatial_graph_sensitivity_summary.exists()
    assert paths.spatial_slx_estimates.exists()
    assert paths.spatial_slx_summary.exists()
    assert paths.spatial_spillover_decomposition.exists()
    assert paths.spatial_spillover_summary.exists()
    assert paths.spatial_exposure_mapping.exists()
    assert paths.spatial_exposure_mapping_summary.exists()


def test_spatial_diagnostics_uses_polygon_adjacency_when_available(tmp_path):
    geopandas = pytest.importorskip("geopandas")
    shapely_geometry = pytest.importorskip("shapely.geometry")

    frame = _line_fixture().drop(columns=["x", "y"])
    source = geopandas.GeoDataFrame(
        frame,
        geometry=[
            shapely_geometry.box(i, 0.0, i + 1.0, 1.0)
            for i in range(len(frame))
        ],
        crs="EPSG:3857",
    )
    spec = StudySpec(
        name="polygon_fixture",
        unit_id="unit_id",
        exposure="exposure",
        outcome="outcome",
        confounders=("confounder",),
        context_columns=("context",),
    )
    paths = SCCAPaths(output_dir=tmp_path)

    diagnostics = run_spatial_diagnostics(frame, spec, paths, source_frame=source, n_permutations=9)

    assert diagnostics["graph"]["method"] == "geometry_touches"
    assert diagnostics["graph"]["edge_count"] == len(frame) - 1
    assert diagnostics["exposure_moran"]["status"] == "ok"


def test_spatial_diagnostics_flags_material_main_effect_shift(tmp_path):
    frame = pd.DataFrame(
        {
            "unit_id": [f"u{i}" for i in range(1, 9)],
            "x": [float(i) for i in range(8)],
            "y": [0.0] * 8,
            "exposure": [0.0, 1.0, 0.2, 1.2, 0.4, 1.4, 0.6, 1.6],
            "outcome": [0.8, 0.9, 2.1, 2.3, 3.4, 3.6, 4.8, 5.0],
            "confounder": [0.0] * 8,
            "context": [1.0] * 8,
        }
    )
    paths = SCCAPaths(output_dir=tmp_path)

    diagnostics = run_spatial_diagnostics(
        frame,
        _spec(),
        paths,
        baseline_exposure_coef=0.2,
        n_permutations=9,
    )

    sensitivity = diagnostics["neighbor_exposure_model"]["spatial_adjustment_sensitivity"]
    assert sensitivity["relative_change"] is not None
    assert any("Main exposure coefficient" in flag for flag in diagnostics["flags"])


def test_append_spatial_adjusted_estimate_updates_effects_and_diagnostics(tmp_path):
    paths = SCCAPaths(output_dir=tmp_path)
    pd.DataFrame(
        [
            {
                "estimator": "baseline_adjusted_ols",
                "status": "ok",
                "coef": 1.0,
                "se": 0.1,
                "p_value": 0.01,
                "ci_lower": 0.8,
                "ci_upper": 1.2,
                "r_squared": 0.5,
                "n": 8,
                "complete_n": 8,
                "dropped_n": 0,
                "warnings": "[]",
            }
        ]
    ).to_csv(paths.effect_estimates, index=False)
    paths.model_diagnostics.write_text(
        json.dumps({"estimators": {"baseline_adjusted_ols": {"status": "ok", "n": 8}}}),
        encoding="utf-8",
    )
    diagnostics = {
        "neighbor_exposure_model": {
            "status": "ok",
            "n": 8,
            "exposure_coef": 0.7,
            "coef": 0.3,
            "p_value": 0.02,
            "r_squared": 0.6,
            "spatial_adjustment_sensitivity": {
                "baseline_exposure_coef": 1.0,
                "spatial_adjusted_exposure_coef": 0.7,
                "coef_delta": -0.3,
                "relative_change": 0.3,
                "sign_stable": True,
            },
        }
    }

    row = append_spatial_adjusted_estimate(paths, diagnostics)

    assert row is not None
    estimates = pd.read_csv(paths.effect_estimates)
    assert "spatial_neighbor_adjusted_ols" in set(estimates["estimator"])
    saved = json.loads(paths.model_diagnostics.read_text(encoding="utf-8"))
    assert saved["estimators"]["spatial_neighbor_adjusted_ols"]["status"] == "ok"


def test_run_spatial_block_bootstrap_summarizes_spatial_adjusted_estimator(tmp_path):
    frame = _line_fixture()
    graph = build_spatial_graph(frame, _spec())

    rows, summary = run_spatial_block_bootstrap(
        frame,
        _spec(),
        graph,
        baseline_exposure_coef=1.5,
        n_replicates=6,
        bins=2,
    )

    assert len(rows) == 6
    assert set(rows.columns) >= {"replicate", "coef", "neighbor_exposure_coef", "status"}
    assert summary["n_replicates_requested"] == 6
    assert summary["status"] in {"ok", "skipped"}
    if summary["status"] == "ok":
        assert summary["n_replicates_valid"] > 0
        assert "ci_lower_2_5" in summary


def test_spatial_lag_model_is_estimable_on_larger_spatial_fixture(tmp_path):
    rows = []
    for i in range(60):
        x = i % 10
        y = i // 10
        exposure = 0.6 * x + 0.35 * y + 0.1 * ((x * y) % 5)
        confounder = 1.0 + 0.2 * ((x * x + 3 * y) % 11) + 0.03 * i
        context = 3.0 + 0.4 * ((2 * x + y * y) % 13) - 0.02 * i
        outcome = 5.0 + 0.7 * exposure + 0.3 * confounder - 0.15 * context + 0.05 * ((x + 2 * y) % 7)
        rows.append(
            {
                "unit_id": f"u{i}",
                "x": float(x),
                "y": float(y),
                "exposure": float(exposure),
                "outcome": float(outcome),
                "confounder": float(confounder),
                "context": float(context),
            }
        )
    frame = pd.DataFrame(rows)
    paths = SCCAPaths(output_dir=tmp_path)

    diagnostics = run_spatial_diagnostics(
        frame,
        _spec(),
        paths,
        baseline_exposure_coef=1.0,
        n_permutations=9,
    )

    assert diagnostics["spatial_lag_model"]["status"] == "ok"
    assert diagnostics["spatial_lag_model"]["lag_covariate_count"] == 2
    assert diagnostics["spatial_lag_model"]["spatial_adjustment_sensitivity"]["relative_change"] is not None
    assert diagnostics["spatial_slx_model"]["status"] == "ok"
    assert diagnostics["spatial_slx_model"]["model"] == "SLX"
    assert diagnostics["spatial_slx_model"]["direct_effect"] is not None
    assert diagnostics["spatial_slx_model"]["indirect_effect"] is not None
    assert diagnostics["spatial_slx_model"]["total_effect"] is not None
    assert diagnostics["spatial_slx_model"]["total_se"] is not None
    assert diagnostics["spatial_slx_model"]["total_p_value"] is not None
    assert diagnostics["spatial_slx_model"]["total_ci_lower"] is not None
    assert diagnostics["spatial_slx_model"]["total_ci_upper"] is not None
    assert diagnostics["spatial_slx_model"]["lag_covariate_count"] == 2
    assert diagnostics["spatial_slx_model"]["coefficient_count"] >= 6
    slx_rows = pd.read_csv(paths.spatial_slx_estimates)
    assert {"term", "role", "coef", "p_value"}.issubset(slx_rows.columns)
    assert {"direct_exposure", "indirect_exposure"}.issubset(set(slx_rows["role"]))
    slx_summary = json.loads(paths.spatial_slx_summary.read_text(encoding="utf-8"))
    assert slx_summary["status"] == "ok"
    assert diagnostics["graph_sensitivity_summary"]["status"] == "ok"
    assert diagnostics["graph_sensitivity_summary"]["n_graphs_valid"] >= 2
    assert diagnostics["spillover_summary"]["status"] == "ok"
    assert diagnostics["exposure_mapping_summary"]["status"] == "ok"
