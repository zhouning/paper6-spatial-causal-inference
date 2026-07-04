from __future__ import annotations

import numpy as np


def _finite(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if np.isfinite(numeric) else None


def compute_residual_spatial_bias_bound(
    *,
    residual_graph_projection_norm: float,
    treatment_residual_norm: float,
    outcome_residual_sd: float,
    latent_smoothness_scale: float = 1.0,
) -> dict[str, object]:
    """Compute a conservative residual spatial bias-bound diagnostic.

    The bound is intentionally diagnostic. It reports how much graph-smooth
    treatment projection remains after adjustment, scaled by residual outcome
    variation and a user-declared latent smoothness scale.
    """

    projection = _finite(residual_graph_projection_norm)
    treatment_norm = _finite(treatment_residual_norm)
    outcome_sd = _finite(outcome_residual_sd)
    smoothness = _finite(latent_smoothness_scale)
    if (
        projection is None
        or treatment_norm is None
        or outcome_sd is None
        or smoothness is None
        or treatment_norm <= 0
        or outcome_sd < 0
        or smoothness < 0
    ):
        return {
            "status": "skipped",
            "bias_bound": np.nan,
            "bias_bound_ratio": np.nan,
            "residual_graph_projection_norm": projection,
            "treatment_residual_norm": treatment_norm,
            "outcome_residual_sd": outcome_sd,
            "latent_smoothness_scale": smoothness,
            "warnings": [
                "Bias bound requires finite positive treatment residual norm and nonnegative scales."
            ],
        }

    ratio = projection / treatment_norm
    bound = ratio * outcome_sd * smoothness
    return {
        "status": "ok",
        "bias_bound": float(bound),
        "bias_bound_ratio": float(ratio),
        "residual_graph_projection_norm": float(projection),
        "treatment_residual_norm": float(treatment_norm),
        "outcome_residual_sd": float(outcome_sd),
        "latent_smoothness_scale": float(smoothness),
        "warnings": [],
    }
