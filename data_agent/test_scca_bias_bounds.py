import numpy as np

from data_agent.scca.bias_bounds import compute_residual_spatial_bias_bound


def test_bias_bound_increases_with_remaining_graph_projection():
    low = compute_residual_spatial_bias_bound(
        residual_graph_projection_norm=0.1,
        treatment_residual_norm=2.0,
        outcome_residual_sd=1.5,
        latent_smoothness_scale=1.0,
    )
    high = compute_residual_spatial_bias_bound(
        residual_graph_projection_norm=0.6,
        treatment_residual_norm=2.0,
        outcome_residual_sd=1.5,
        latent_smoothness_scale=1.0,
    )

    assert low["status"] == "ok"
    assert high["status"] == "ok"
    assert high["bias_bound"] > low["bias_bound"]
    assert high["bias_bound_ratio"] > low["bias_bound_ratio"]


def test_bias_bound_skips_invalid_treatment_residual_norm():
    result = compute_residual_spatial_bias_bound(
        residual_graph_projection_norm=0.1,
        treatment_residual_norm=0.0,
        outcome_residual_sd=1.5,
    )

    assert result["status"] == "skipped"
    assert np.isnan(result["bias_bound"])
    assert np.isnan(result["bias_bound_ratio"])
    assert any("positive treatment residual norm" in warning for warning in result["warnings"])
