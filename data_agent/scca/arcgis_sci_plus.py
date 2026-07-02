from __future__ import annotations

import numpy as np
import pandas as pd


def _validate_quantile_bounds(lower_q: float, upper_q: float) -> None:
    if not 0 <= lower_q <= 1 or not 0 <= upper_q <= 1:
        raise ValueError("lower_q and upper_q must both be in [0, 1].")
    if lower_q > upper_q:
        raise ValueError("lower_q must be <= upper_q.")


def _skipped_trim_summary(
    frame: pd.DataFrame,
    *,
    lower_q: float,
    upper_q: float,
    warning: str,
) -> tuple[pd.DataFrame, dict[str, object]]:
    input_rows = int(len(frame))
    return frame.iloc[0:0].copy(), {
        "status": "skipped",
        "input_rows": input_rows,
        "trimmed_rows": 0,
        "removed_rows": input_rows,
        "lower_q": float(lower_q),
        "upper_q": float(upper_q),
        "lower_quantile": None,
        "upper_quantile": None,
        "warning": warning,
    }


def arcgis_quantile_trim(
    frame: pd.DataFrame,
    exposure: str,
    *,
    lower_q: float = 0.01,
    upper_q: float = 0.99,
) -> tuple[pd.DataFrame, dict[str, object]]:
    _validate_quantile_bounds(lower_q, upper_q)
    if exposure not in frame.columns:
        return _skipped_trim_summary(
            frame,
            lower_q=lower_q,
            upper_q=upper_q,
            warning=f"Cannot trim: missing exposure column '{exposure}'.",
        )

    values = pd.to_numeric(frame[exposure], errors="coerce")
    finite_values = values[np.isfinite(values)]
    if finite_values.empty:
        return _skipped_trim_summary(
            frame,
            lower_q=lower_q,
            upper_q=upper_q,
            warning=f"Cannot trim: exposure column '{exposure}' has no finite values.",
        )

    lower = float(finite_values.quantile(lower_q))
    upper = float(finite_values.quantile(upper_q))
    mask = values.ge(lower) & values.le(upper)
    trimmed = frame.loc[mask].copy()
    summary = {
        "status": "ok",
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

    frame = frame.assign(response_gap=(frame["response"] - target).abs())
    nearest_gap = float(frame["response_gap"].min())
    tied = frame[frame["response_gap"].eq(nearest_gap)]
    row = tied.sort_values("exposure", kind="mergesort").iloc[0]
    prediction = float(row["response"])
    tie_count = int(len(tied))
    warnings = []
    if tie_count > 1:
        warnings.append(
            "Multiple ERF rows tie for nearest target response; selected smallest exposure."
        )

    return {
        "status": "ok",
        "target_response": target,
        "target_exposure": float(row["exposure"]),
        "target_prediction": prediction,
        "absolute_response_gap": nearest_gap,
        "tie_count": tie_count,
        "warnings": warnings,
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
            "ArcGIS SCI Plus organizes ArcGIS SCI-style ERF/trim/target outputs "
            "and adds open spatial causal-risk auditing."
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
