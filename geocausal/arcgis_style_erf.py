from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ArcGISStyleERFResult:
    curve: pd.DataFrame
    summary: dict[str, Any]
    warnings: tuple[str, ...] = ()


def _json_float(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if np.isfinite(numeric) else None


def _aligned_weights(features: pd.DataFrame, weights: pd.Series | np.ndarray | list[float]) -> pd.Series:
    if isinstance(weights, pd.Series):
        aligned = weights.reindex(features.index)
    else:
        aligned = pd.Series(weights, index=features.index)
    return pd.to_numeric(aligned, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(lower=0.0)


def plugin_bandwidth(exposure: pd.Series) -> float:
    values = pd.to_numeric(exposure, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(values) < 2 or values.nunique() < 2:
        return float("nan")
    bandwidth = 2.0 * float(values.std(ddof=1)) * (len(values) ** (-1.0 / 5.0))
    return bandwidth if np.isfinite(bandwidth) and bandwidth > 0 else float("nan")


def arcgis_style_erf_curve(
    features: pd.DataFrame,
    *,
    exposure: str,
    outcome: str,
    weights: pd.Series | np.ndarray | list[float],
    n_grid: int = 200,
    bandwidth: float | None = None,
) -> ArcGISStyleERFResult:
    columns = ["exposure", "response", "source"]
    if exposure not in features.columns or outcome not in features.columns:
        return ArcGISStyleERFResult(
            curve=pd.DataFrame(columns=columns),
            summary={
                "status": "skipped",
                "n": 0,
                "n_grid": 0,
                "bandwidth": None,
                "weight_sum": None,
                "effective_sample_size": None,
            },
            warnings=("Exposure or outcome column is missing for ArcGIS-style ERF estimation.",),
        )

    frame = pd.DataFrame(
        {
            "exposure": pd.to_numeric(features[exposure], errors="coerce"),
            "outcome": pd.to_numeric(features[outcome], errors="coerce"),
            "weight": _aligned_weights(features, weights),
        },
        index=features.index,
    ).replace([np.inf, -np.inf], np.nan)
    frame = frame.dropna(subset=["exposure", "outcome"])
    frame["weight"] = frame["weight"].fillna(0.0).clip(lower=0.0)
    positive = frame["weight"] > 0
    warnings: list[str] = []
    if len(frame) < 2 or frame["exposure"].nunique() < 2:
        return ArcGISStyleERFResult(
            curve=pd.DataFrame(columns=columns),
            summary={
                "status": "skipped",
                "n": int(len(frame)),
                "n_grid": 0,
                "bandwidth": None,
                "weight_sum": _json_float(frame["weight"].sum()) if not frame.empty else None,
                "effective_sample_size": None,
            },
            warnings=("ArcGIS-style ERF requires at least two exposure values.",),
        )
    if int(positive.sum()) < 2:
        warnings.append("ArcGIS-style ERF has fewer than two positive-weight rows; using unit weights.")
        frame["weight"] = 1.0

    bw = float(bandwidth) if bandwidth is not None else plugin_bandwidth(frame["exposure"])
    if not np.isfinite(bw) or bw <= 0:
        return ArcGISStyleERFResult(
            curve=pd.DataFrame(columns=columns),
            summary={
                "status": "skipped",
                "n": int(len(frame)),
                "n_grid": 0,
                "bandwidth": None,
                "weight_sum": _json_float(frame["weight"].sum()),
                "effective_sample_size": None,
            },
            warnings=tuple([*warnings, "ArcGIS-style ERF bandwidth is non-positive or non-finite."]),
        )

    x = frame["exposure"].to_numpy(dtype=float)
    y = frame["outcome"].to_numpy(dtype=float)
    w = frame["weight"].to_numpy(dtype=float)
    grid = np.linspace(float(np.min(x)), float(np.max(x)), int(n_grid))
    response = np.empty(len(grid), dtype=float)
    local_ess = np.empty(len(grid), dtype=float)
    for index, point in enumerate(grid):
        kernel = np.exp(-0.5 * ((x - point) / bw) ** 2) * w
        total = float(kernel.sum())
        if total <= 0 or not np.isfinite(total):
            response[index] = np.nan
            local_ess[index] = np.nan
            continue
        response[index] = float(np.average(y, weights=kernel))
        square_sum = float(np.sum(kernel * kernel))
        local_ess[index] = (total * total / square_sum) if square_sum > 0 else np.nan

    weight_sum = float(np.sum(w))
    ess = (weight_sum * weight_sum / float(np.sum(w * w))) if float(np.sum(w * w)) > 0 else np.nan
    curve = pd.DataFrame(
        {
            "exposure": grid,
            "response": response,
            "source": "arcgis_style_kernel_weighted_mean",
            "bandwidth": bw,
            "local_effective_sample_size": local_ess,
        }
    )
    return ArcGISStyleERFResult(
        curve=curve,
        summary={
            "status": "ok",
            "n": int(len(frame)),
            "n_grid": int(len(curve)),
            "bandwidth": bw,
            "weight_sum": _json_float(weight_sum),
            "effective_sample_size": _json_float(ess),
            "response_min": _json_float(np.nanmin(response)) if np.isfinite(response).any() else None,
            "response_max": _json_float(np.nanmax(response)) if np.isfinite(response).any() else None,
        },
        warnings=tuple(warnings),
    )