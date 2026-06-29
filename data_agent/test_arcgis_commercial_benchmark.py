from __future__ import annotations

import json

import pytest


def test_arcgis_parity_matrix_contains_required_capabilities():
    from data_agent.experiments.arcgis_commercial_benchmark import (
        build_arcgis_parity_matrix,
    )

    matrix = build_arcgis_parity_matrix()
    capabilities = set(matrix["arcgis_capability"])

    assert "continuous_exposure_outcome_workflow" in capabilities
    assert "ols_or_gradient_boosting_propensity_score" in capabilities
    assert "propensity_score_matching" in capabilities
    assert "inverse_propensity_score_weighting" in capabilities
    assert "one_to_ninetynine_exposure_trimming" in capabilities
    assert "weighted_correlation_balance_threshold" in capabilities
    assert "erf_table" in capabilities
    assert "target_exposure_and_target_outcome_fields" in capabilities
    assert "local_erf_popups" in capabilities
    assert "spatial_residual_diagnostics" in capabilities

    assert set(matrix["scca_status"]) <= {
        "matched",
        "partial",
        "gap",
        "scca_only_differentiator",
    }


def test_inspect_county_outputs_records_arcgis_parity_metrics(tmp_path):
    from data_agent.experiments.arcgis_commercial_benchmark import (
        inspect_county_parity_artifacts,
    )

    results_dir = tmp_path / "07_results"
    results_dir.mkdir()
    (results_dir / "county_social_capital_spatial_notebook_summary.json").write_text(
        json.dumps(
            {
                "result_summary": {
                    "baseline_adjusted_ols": {"coef": 0.181, "n": 3044},
                    "spatial_neighbor_adjusted_ols": {"coef": 0.152},
                    "spatial_lag_adjusted_ols": {"coef": 0.145},
                    "spatial_diagnostics": {
                        "residual_moran_i": 0.313,
                        "residual_moran_p_value": 0.001,
                    },
                },
                "spatial_manifest": {
                    "row_count": 3108,
                    "matched_count": 3044,
                    "spatial_files": ["analysis_joined.gpkg"],
                    "visualization_files": ["interactive_map.html"],
                },
            }
        ),
        encoding="utf-8",
    )

    metrics = inspect_county_parity_artifacts(results_dir)

    assert metrics["input_rows"] == 3108
    assert metrics["included_rows"] == 3044
    assert metrics["baseline_coef"] == pytest.approx(0.181)
    assert metrics["spatial_neighbor_adjusted_coef"] == pytest.approx(0.152)
    assert metrics["spatial_lag_adjusted_coef"] == pytest.approx(0.145)
    assert metrics["residual_moran_i"] == pytest.approx(0.313)
    assert metrics["residual_moran_p_value"] == pytest.approx(0.001)
    assert metrics["spatial_files_available"] is True
    assert metrics["visualization_files_available"] is True


def test_write_arcgis_commercial_benchmark_outputs(tmp_path):
    from data_agent.experiments.arcgis_commercial_benchmark import (
        write_arcgis_commercial_benchmark,
    )

    manifest = write_arcgis_commercial_benchmark(
        output_dir=tmp_path,
        results_dir=tmp_path,
    )

    assert (tmp_path / "arcgis_parity_matrix.csv").exists()
    assert (tmp_path / "arcgis_parity_summary.md").exists()
    assert (tmp_path / "arcgis_commercial_benchmark_manifest.json").exists()
    assert manifest["parity_matrix_csv"].endswith("arcgis_parity_matrix.csv")
    assert manifest["parity_summary_md"].endswith("arcgis_parity_summary.md")
    assert manifest["status_counts"]
