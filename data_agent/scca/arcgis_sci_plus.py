from __future__ import annotations

import numpy as np
import pandas as pd


def _finite_or_none(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if np.isfinite(numeric) else None


def arcgis_quantile_trim(
    frame: pd.DataFrame,
    exposure: str,
    *,
    lower_q: float = 0.01,
    upper_q: float = 0.99,
) -> tuple[pd.DataFrame, dict[str, object]]:
    values = pd.to_numeric(frame[exposure], errors="coerce")
    lower = float(values.quantile(lower_q))
    upper = float(values.quantile(upper_q))
    mask = values.ge(lower) & values.le(upper)
    trimmed = frame.loc[mask].copy()
    summary = {
        "input_rows": int(len(frame)),
        "trimmed_rows": int(len(trimmed)),
        "removed_rows": int(len(frame) - len(trimmed)),
        "lower_q": float(lower_q),
        "upper_q": float(upper_q),
        "lower_quantile": lower,
        "upper_quantile": upper,
    }
    return trimmed, summary


def solve_target_exposure(
    erf_curve: pd.DataFrame, target_response: float
) -> dict[str, object]:
    target = float(target_response)
    required = {"exposure", "response"}
    missing = sorted(required - set(erf_curve.columns))
    if missing:
        return {
            "status": "skipped",
            "target_response": target,
            "target_exposure": None,
            "target_prediction": None,
            "warnings": [
                f"ERF curve missing column(s): {', '.join(missing)}."
            ],
        }

    frame = erf_curve[["exposure", "response"]].apply(
        pd.to_numeric, errors="coerce"
    )
    frame = frame[np.isfinite(frame["exposure"]) & np.isfinite(frame["response"])]
    if frame.empty:
        return {
            "status": "skipped",
            "target_response": target,
            "target_exposure": None,
            "target_prediction": None,
            "warnings": ["ERF curve has no finite exposure/response rows."],
        }

    idx = (frame["response"] - target).abs().idxmin()
    row = frame.loc[idx]
    prediction = float(row["response"])
    return {
        "status": "ok",
        "target_response": target,
        "target_exposure": float(row["exposure"]),
        "target_prediction": prediction,
        "absolute_response_gap": float(abs(prediction - target)),
        "warnings": [],
    }


def build_arcgis_sci_plus_report(
    *,
    study: str,
    arcgis_trim_summary: dict[str, object],
    erf_summary: dict[str, object],
    target_summary: dict[str, object],
    spatial_risk: dict[str, object],
    role_risk: dict[str, object],
    scale_risk: dict[str, object],
) -> dict[str, object]:
    return {
        "study": study,
        "claim": (
            "ArcGIS SCI Plus reproduces ArcGIS Spatial Causal Inference style "
            "ERF/trim/target outputs and adds open spatial causal-risk auditing."
        ),
        "arcgis_sci_parity": {
            **arcgis_trim_summary,
            "erf": erf_summary,
            "target_analysis": target_summary,
        },
        "geo_causal_extensions": {
            "spatial_risk": spatial_risk,
            "role_risk": role_risk,
            "scale_risk": scale_risk,
        },
    }
