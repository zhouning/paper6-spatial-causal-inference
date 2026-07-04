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
        "warnings": [warning],
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
    try:
        target = float(target_response)
    except (TypeError, ValueError):
        target = None
    if target is None or not np.isfinite(target):
        return {
            "status": "skipped",
            "target_response": None,
            "target_exposure": None,
            "target_prediction": None,
            "warnings": ["Target analysis requires a finite target_response."],
        }

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

    response_min = float(frame["response"].min())
    response_max = float(frame["response"].max())
    target_within_response_range = response_min <= target <= response_max
    frame = frame.assign(response_gap=(frame["response"] - target).abs())
    nearest_gap = float(frame["response_gap"].min())
    tied = frame[frame["response_gap"].eq(nearest_gap)]
    row = tied.sort_values("exposure", kind="mergesort").iloc[0]
    prediction = float(row["response"])
    tie_count = int(len(tied))
    warnings = []
    if not target_within_response_range:
        warnings.append(
            "Target response is outside the ERF response range; selected nearest ERF point."
        )
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
        "response_min": response_min,
        "response_max": response_max,
        "target_within_response_range": target_within_response_range,
        "tie_count": tie_count,
        "warnings": warnings,
    }



def _normal_density(value: np.ndarray | float, scale: float) -> np.ndarray:
    scale = max(float(scale), np.finfo(float).eps)
    arr = np.asarray(value, dtype=float)
    return np.exp(-0.5 * np.square(arr / scale)) / (scale * np.sqrt(2.0 * np.pi))


def _complete_arcgis_numeric_frame(
    frame: pd.DataFrame,
    columns: list[str],
) -> tuple[pd.DataFrame, list[str]]:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        return pd.DataFrame(), missing
    numeric = frame[columns].apply(pd.to_numeric, errors="coerce")
    numeric = numeric.replace([np.inf, -np.inf], np.nan).dropna()
    return numeric, []


def _regression_propensity_fit(
    frame: pd.DataFrame,
    exposure: str,
    confounders: list[str],
) -> dict[str, object]:
    x = frame[confounders].astype(float)
    treatment = frame[exposure].astype(float).to_numpy(dtype=float)
    means = x.mean(axis=0)
    stds = x.std(axis=0, ddof=0).replace(0, 1.0)
    x_scaled = ((x - means) / stds).to_numpy(dtype=float)
    design = np.column_stack([np.ones(len(frame)), x_scaled])
    beta = np.linalg.lstsq(design, treatment, rcond=None)[0]
    predicted = design @ beta
    residuals = treatment - predicted
    degrees = max(len(frame) - design.shape[1], 1)
    sigma = float(np.sqrt(np.sum(np.square(residuals)) / degrees))
    if not np.isfinite(sigma) or sigma <= 0:
        sigma = float(np.std(treatment, ddof=1)) if len(treatment) > 1 else 1.0
    sigma = max(sigma, np.finfo(float).eps)
    propensity = _normal_density(residuals, sigma)
    return {
        "predicted_exposure": predicted,
        "residual_sigma": sigma,
        "propensity_score": propensity,
        "coef": beta,
    }


def _arcgis_num_bin_candidates(n: int) -> list[int]:
    if n <= 0:
        return []
    lower = max(2, int(np.floor(n ** 0.25)))
    upper = max(lower + 1, int(np.floor(2.0 * (n ** (1.0 / 3.0)))))
    step = max(3, int(np.ceil((upper - lower) / 9.0)))
    values = list(range(lower, upper, step))
    if not values:
        values = [lower]
    return values[:10]


def _weighted_corr(x: np.ndarray, y: np.ndarray, weights: np.ndarray | None = None) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if weights is None:
        weights = np.ones_like(x, dtype=float)
    else:
        weights = np.asarray(weights, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights) & (weights > 0)
    if int(mask.sum()) < 2:
        return np.nan
    x = x[mask]
    y = y[mask]
    weights = weights[mask]
    weight_sum = float(weights.sum())
    if weight_sum <= 0:
        return np.nan
    x_mean = float(np.average(x, weights=weights))
    y_mean = float(np.average(y, weights=weights))
    x_centered = x - x_mean
    y_centered = y - y_mean
    x_var = float(np.average(np.square(x_centered), weights=weights))
    y_var = float(np.average(np.square(y_centered), weights=weights))
    if x_var <= 0 or y_var <= 0:
        return 0.0
    cov = float(np.average(x_centered * y_centered, weights=weights))
    return cov / float(np.sqrt(x_var * y_var))


def _arcgis_balance_table(
    frame: pd.DataFrame,
    exposure: str,
    confounders: list[str],
    weights: np.ndarray,
    *,
    balance_type: str = "MEAN",
) -> tuple[pd.DataFrame, dict[str, object]]:
    exposure_values = frame[exposure].to_numpy(dtype=float)
    rows: list[dict[str, object]] = []
    for variable in confounders:
        values = frame[variable].to_numpy(dtype=float)
        original = _weighted_corr(values, exposure_values)
        weighted = _weighted_corr(values, exposure_values, weights)
        rows.append(
            {
                "variable": variable,
                "original_correlation": original,
                "weighted_correlation": weighted,
                "abs_original_correlation": abs(original) if np.isfinite(original) else np.nan,
                "abs_weighted_correlation": abs(weighted) if np.isfinite(weighted) else np.nan,
            }
        )
    table = pd.DataFrame(rows)
    abs_weighted = pd.to_numeric(table.get("abs_weighted_correlation"), errors="coerce").dropna()
    abs_original = pd.to_numeric(table.get("abs_original_correlation"), errors="coerce").dropna()
    mode = balance_type.upper()
    if abs_weighted.empty:
        aggregate = np.nan
    elif mode == "MEDIAN":
        aggregate = float(abs_weighted.median())
    elif mode == "MAX":
        aggregate = float(abs_weighted.max())
    else:
        aggregate = float(abs_weighted.mean())
    summary = {
        "balance_type": mode,
        "aggregate_original_correlation": float(abs_original.mean()) if not abs_original.empty else np.nan,
        "aggregate_weighted_correlation": aggregate,
        "max_abs_weighted_correlation": float(abs_weighted.max()) if not abs_weighted.empty else np.nan,
    }
    return table, summary


def _arcgis_matching_weights(
    frame: pd.DataFrame,
    exposure: str,
    confounders: list[str],
    propensity_fit: dict[str, object],
    *,
    balance_type: str = "MEAN",
    balance_threshold: float = 0.1,
    num_bins: int | None = None,
    scale: float | None = None,
) -> tuple[np.ndarray, pd.DataFrame, pd.DataFrame, dict[str, object], dict[str, object]]:
    exposure_values = frame[exposure].to_numpy(dtype=float)
    predicted = np.asarray(propensity_fit["predicted_exposure"], dtype=float)
    sigma = float(propensity_fit["residual_sigma"])
    observed_ps = np.asarray(propensity_fit["propensity_score"], dtype=float)
    n = len(frame)
    bin_candidates = [int(num_bins)] if num_bins is not None else _arcgis_num_bin_candidates(n)
    scale_candidates = [float(scale)] if scale is not None else [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    exp_min = float(np.min(exposure_values))
    exp_max = float(np.max(exposure_values))
    exp_range = max(exp_max - exp_min, np.finfo(float).eps)
    ps_range = max(float(np.nanmax(observed_ps) - np.nanmin(observed_ps)), np.finfo(float).eps)
    exposure_scaled = (exposure_values - exp_min) / exp_range
    grid_rows: list[dict[str, object]] = []
    best: dict[str, object] | None = None
    best_weights = np.ones(n, dtype=float)
    best_balance = pd.DataFrame()
    best_balance_summary: dict[str, object] = {}

    for bins in bin_candidates:
        bins = max(2, int(bins))
        edges = np.linspace(exp_min, exp_max, bins + 1)
        centers = 0.5 * (edges[:-1] + edges[1:])
        bin_index = np.digitize(exposure_values, edges[1:-1], right=False)
        for scale_value in scale_candidates:
            scale_value = float(scale_value)
            weights = np.zeros(n, dtype=float)
            for bin_id, center in enumerate(centers):
                candidates = np.where(bin_index == bin_id)[0]
                if len(candidates) == 0:
                    continue
                center_scaled = (float(center) - exp_min) / exp_range
                counterfactual_ps = _normal_density(float(center) - predicted, sigma)
                ps_component = np.abs(observed_ps[candidates][None, :] - counterfactual_ps[:, None]) / ps_range
                exposure_component = np.abs(exposure_scaled[candidates][None, :] - center_scaled)
                score = scale_value * ps_component + (1.0 - scale_value) * exposure_component
                selected = candidates[np.argmin(score, axis=1)]
                weights += np.bincount(selected, minlength=n).astype(float)
            balance_table, balance_summary = _arcgis_balance_table(
                frame,
                exposure,
                confounders,
                weights,
                balance_type=balance_type,
            )
            aggregate = float(balance_summary["aggregate_weighted_correlation"])
            row = {
                "num_bins": bins,
                "scale": scale_value,
                "aggregate_weighted_correlation": aggregate,
                "passes_threshold": bool(np.isfinite(aggregate) and aggregate <= balance_threshold),
                "weight_sum": float(weights.sum()),
                "nonzero_weight_n": int(np.count_nonzero(weights)),
            }
            grid_rows.append(row)
            if best is None or aggregate < float(best["aggregate_weighted_correlation"]):
                best = row
                best_weights = weights
                best_balance = balance_table
                best_balance_summary = balance_summary

    grid = pd.DataFrame(grid_rows)
    if best is None:
        best = {
            "num_bins": None,
            "scale": None,
            "aggregate_weighted_correlation": np.nan,
            "passes_threshold": False,
            "weight_sum": 0.0,
            "nonzero_weight_n": 0,
        }
    summary = {
        "ps_method": "REGRESSION",
        "balancing_method": "MATCHING",
        "balance_type": balance_type.upper(),
        "balance_threshold": float(balance_threshold),
        "selected_num_bins": int(best["num_bins"]) if best["num_bins"] is not None else None,
        "selected_scale": float(best["scale"]) if best["scale"] is not None else None,
        "selected_mean_abs_weighted_correlation": float(best["aggregate_weighted_correlation"]),
        "selected_passes_threshold": bool(best["passes_threshold"]),
        "weight_sum": int(round(float(best["weight_sum"]))),
        "nonzero_weight_n": int(best["nonzero_weight_n"]),
        "candidate_count": int(len(grid_rows)),
    }
    return best_weights, grid, best_balance, best_balance_summary, summary


def _arcgis_plugin_bandwidth(exposure_values: np.ndarray) -> float:
    exposure_values = np.asarray(exposure_values, dtype=float)
    exposure_values = exposure_values[np.isfinite(exposure_values)]
    if len(exposure_values) < 2:
        return 1.0
    sd = float(np.std(exposure_values, ddof=1))
    if not np.isfinite(sd) or sd <= 0:
        return 1.0
    return max(2.0 * sd * (len(exposure_values) ** (-0.2)), np.finfo(float).eps)


def _weighted_effective_n(weights: np.ndarray) -> float:
    weights = np.asarray(weights, dtype=float)
    weights = weights[np.isfinite(weights) & (weights > 0)]
    if len(weights) == 0:
        return 0.0
    denominator = float(np.sum(np.square(weights)))
    if denominator <= 0:
        return 0.0
    return float(np.square(weights.sum()) / denominator)


def _arcgis_weighted_kernel_erf(
    frame: pd.DataFrame,
    exposure: str,
    outcome: str,
    weights: np.ndarray,
    *,
    n_grid: int = 200,
    bandwidth: float | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    exposure_values = frame[exposure].to_numpy(dtype=float)
    outcome_values = frame[outcome].to_numpy(dtype=float)
    weights = np.asarray(weights, dtype=float)
    if bandwidth is None:
        bandwidth = _arcgis_plugin_bandwidth(exposure_values)
    bandwidth = max(float(bandwidth), np.finfo(float).eps)
    grid = np.linspace(float(exposure_values.min()), float(exposure_values.max()), int(n_grid))
    responses: list[float] = []
    for point in grid:
        scaled_distance = (exposure_values - point) / bandwidth
        kernel = np.exp(-0.5 * np.square(scaled_distance))
        kernel[np.abs(scaled_distance) > 3.0] = 0.0
        kernel_weights = kernel * weights
        if float(kernel_weights.sum()) <= 0:
            responses.append(np.nan)
        else:
            responses.append(float(np.average(outcome_values, weights=kernel_weights)))
    curve = pd.DataFrame({"exposure": grid, "response": responses})
    response_values = pd.to_numeric(curve["response"], errors="coerce").dropna()
    summary = {
        "status": "ok" if not response_values.empty else "unstable",
        "n": int(len(frame)),
        "n_grid": int(n_grid),
        "bandwidth": float(bandwidth),
        "weight_sum": float(np.nansum(weights)),
        "effective_sample_size": _weighted_effective_n(weights),
        "response_min": float(response_values.min()) if not response_values.empty else np.nan,
        "response_max": float(response_values.max()) if not response_values.empty else np.nan,
    }
    return curve, summary


def arcgis_documented_causal_analysis(
    frame: pd.DataFrame,
    *,
    exposure: str,
    outcome: str,
    confounders: list[str],
    balance_type: str = "MEAN",
    balance_threshold: float = 0.1,
    num_bins: int | None = None,
    scale: float | None = None,
    bandwidth: float | None = None,
    n_grid: int = 200,
) -> dict[str, object]:
    """Run the documented ArcGIS continuous-exposure causal workflow.

    This implements the public REGRESSION + MATCHING + weighted kernel ERF
    path documented for ArcGIS Causal Inference Analysis. It is not a
    bit-for-bit reimplementation of Esri private internals or untested modes.
    """
    columns = [exposure, outcome, *confounders]
    analysis_frame, missing = _complete_arcgis_numeric_frame(frame, columns)
    if missing:
        return {
            "status": "skipped",
            "warnings": [f"Missing column(s): {', '.join(missing)}."],
            "analysis_frame": pd.DataFrame(),
            "erf_curve": pd.DataFrame(columns=["exposure", "response"]),
            "matching_grid": pd.DataFrame(),
            "balance_table": pd.DataFrame(),
        }
    if len(analysis_frame) < max(5, len(confounders) + 3):
        return {
            "status": "skipped",
            "warnings": ["Too few complete rows for ArcGIS documented causal analysis."],
            "analysis_frame": analysis_frame,
            "erf_curve": pd.DataFrame(columns=["exposure", "response"]),
            "matching_grid": pd.DataFrame(),
            "balance_table": pd.DataFrame(),
        }
    if analysis_frame[exposure].nunique() < 2:
        return {
            "status": "skipped",
            "warnings": ["Exposure has no variation."],
            "analysis_frame": analysis_frame,
            "erf_curve": pd.DataFrame(columns=["exposure", "response"]),
            "matching_grid": pd.DataFrame(),
            "balance_table": pd.DataFrame(),
        }

    propensity_fit = _regression_propensity_fit(analysis_frame, exposure, confounders)
    weights, matching_grid, balance_table, balance_summary, matching_summary = _arcgis_matching_weights(
        analysis_frame,
        exposure,
        confounders,
        propensity_fit,
        balance_type=balance_type,
        balance_threshold=balance_threshold,
        num_bins=num_bins,
        scale=scale,
    )
    erf_curve, erf_summary = _arcgis_weighted_kernel_erf(
        analysis_frame,
        exposure,
        outcome,
        weights,
        n_grid=n_grid,
        bandwidth=bandwidth,
    )
    analysis_with_outputs = analysis_frame.copy()
    analysis_with_outputs["gc_arcgis_documented_propensity_score"] = np.asarray(
        propensity_fit["propensity_score"], dtype=float
    )
    analysis_with_outputs["gc_arcgis_documented_matching_weight"] = weights
    return {
        "status": "ok",
        "arcgis_mode": "continuous_regression_matching_plugin_erf",
        "analysis_frame": analysis_with_outputs,
        "matching_grid": matching_grid,
        "balance_table": balance_table,
        "balance_summary": balance_summary,
        "matching_summary": matching_summary,
        "erf_curve": erf_curve,
        "erf_summary": erf_summary,
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
    bias_bound: dict[str, object] | None = None,
    arcgis_algorithm_summary: dict[str, object] | None = None,
    data_provenance: dict[str, object] | None = None,
) -> dict[str, object]:
    if bias_bound is None:
        bias_bound = {
            "status": "unavailable",
            "warnings": ["Residual spatial bias-bound was not computed for this run."],
        }
    if data_provenance is None:
        data_provenance = {
            "status": "unavailable",
            "warnings": ["Field-level data provenance was not attached for this run."],
        }

    arcgis_sci_parity = {
        **arcgis_trim_summary,
        "erf": erf_summary,
        "target_analysis": target_summary,
    }
    if arcgis_algorithm_summary is not None:
        arcgis_sci_parity["algorithm"] = arcgis_algorithm_summary

    return {
        "study": study,
        "claim": (
            "ArcGIS SCI Plus implements the documented ArcGIS continuous-exposure "
            "REGRESSION + MATCHING + weighted-kernel ERF causal workflow and adds "
            "open spatial causal-risk auditing, scale checks, role audits, and "
            "residual spatial bias-bound reporting when graph inputs are available."
        ),
        "replacement_assessment": {
            "arcgis_platform_replacement": False,
            "causal_inference_task_replacement": "tested_algorithmic_replacement",
            "supported_arcgis_mode": (
                "Continuous exposure/outcome with REGRESSION propensity scores, "
                "MATCHING balance, ArcGIS-style quantile trimming, and weighted "
                "kernel ERF outputs."
            ),
            "supported_replacement_scope": (
                "Tabular or feature-layer causal inference workflows that need "
                "transparent trimming, ERF tables, target-response lookup, "
                "spatial diagnostics, role/scale audits, and reproducible outputs."
            ),
            "not_replaced": (
                "Untested ArcGIS Causal Inference parameter modes such as "
                "GRADIENT_BOOSTING, WEIGHTING, CV/MANUAL bandwidth selection, "
                "bootstrap confidence intervals, and private implementation details "
                "not specified in the public documentation."
            ),
        },
        "arcgis_sci_parity": arcgis_sci_parity,
        "data_provenance": data_provenance,
        "geo_causal_extensions": {
            "spatial_risk": spatial_risk,
            "role_risk": role_risk,
            "scale_risk": scale_risk,
            "bias_bound": bias_bound,
        },
    }
