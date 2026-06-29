from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.optimize import minimize
from sklearn.ensemble import GradientBoostingRegressor


BALANCE_THRESHOLD = 0.1
DEFAULT_SCALES = tuple(round(value, 1) for value in np.linspace(0.0, 1.0, 6))


@dataclass(frozen=True)
class ArcGISStyleMatchingResult:
    weights: pd.Series
    calibrated_weights: pd.Series
    propensity_scores: pd.Series
    balance_summary: pd.DataFrame
    calibrated_balance_summary: pd.DataFrame
    grid: pd.DataFrame
    selected_num_bins: int | None
    selected_scale: float | None
    selected_gps_method: str | None
    selected_mean_abs_weighted_correlation: float | None
    calibrated_mean_abs_weighted_correlation: float | None
    calibration_summary: dict[str, object]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _GPSFit:
    method: str
    exposure_scaled: pd.Series
    covariates_scaled: pd.DataFrame
    observed_gps: pd.Series
    density_at: Callable[[np.ndarray, pd.DataFrame], np.ndarray]


def candidate_num_bins(n: int) -> tuple[int, ...]:
    """ArcGIS-like candidate exposure bin counts for automatic search."""
    if n <= 0:
        return ()
    lower = max(2, int(np.floor(n ** 0.25)))
    upper = max(lower, int(np.ceil(2.0 * (n ** (1.0 / 3.0)))))
    upper = min(upper, max(2, n))
    step = max(3, int(np.ceil((upper - lower) / 9.0))) if upper > lower else 3
    values = list(range(lower, upper + 1, step))
    if upper not in values and len(values) < 10:
        values.append(upper)
    values = sorted({int(value) for value in values if 2 <= value <= n})
    return tuple(values[:10])


def _available_numeric_columns(frame: pd.DataFrame, columns: Sequence[str]) -> list[str]:
    return [column for column in columns if column in frame.columns]


def _numeric_complete_frame(frame: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    numeric = frame[list(columns)].apply(pd.to_numeric, errors="coerce")
    return numeric.replace([np.inf, -np.inf], np.nan).dropna()


def _minmax_scale(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").astype(float)
    minimum = float(numeric.min())
    maximum = float(numeric.max())
    span = maximum - minimum
    if not np.isfinite(span) or span <= 0:
        return pd.Series(0.0, index=series.index, dtype=float)
    return ((numeric - minimum) / span).astype(float)


def _normal_density(z: np.ndarray) -> np.ndarray:
    return np.exp(-0.5 * z**2) / np.sqrt(2.0 * np.pi)


def _fit_regression_gps(frame: pd.DataFrame, exposure: str, covariates: Sequence[str]) -> _GPSFit | None:
    exposure_scaled = _minmax_scale(frame[exposure])
    if exposure_scaled.nunique() < 2:
        return None
    covariates_scaled = pd.DataFrame(
        {column: _minmax_scale(frame[column]) for column in covariates},
        index=frame.index,
    )
    x = pd.DataFrame({"const": 1.0}, index=frame.index)
    for column in covariates_scaled.columns:
        x[column] = covariates_scaled[column].astype(float)
    try:
        model = sm.OLS(exposure_scaled.astype(float), x.astype(float), missing="drop").fit()
    except Exception:
        return None

    predicted = pd.Series(model.predict(x.astype(float)), index=frame.index, dtype=float)
    residuals = exposure_scaled - predicted
    residual_sd = float(np.std(residuals.to_numpy(dtype=float), ddof=1))
    if not np.isfinite(residual_sd) or residual_sd <= 0:
        return None
    x_columns = list(x.columns)

    def density_at(exposure_values_scaled: np.ndarray, covariate_values_scaled: pd.DataFrame) -> np.ndarray:
        design = pd.DataFrame({"const": 1.0}, index=covariate_values_scaled.index)
        for column in x_columns:
            if column == "const":
                continue
            design[column] = pd.to_numeric(covariate_values_scaled[column], errors="coerce").astype(float)
        design = design[x_columns]
        predicted_values = np.asarray(model.predict(design.astype(float)), dtype=float)
        z = (np.asarray(exposure_values_scaled, dtype=float) - predicted_values) / residual_sd
        density = _normal_density(z) / residual_sd
        return np.maximum(np.asarray(density, dtype=float), np.finfo(float).eps)

    observed = pd.Series(
        density_at(exposure_scaled.to_numpy(dtype=float), covariates_scaled),
        index=frame.index,
        dtype=float,
    )
    return _GPSFit(
        method="ols",
        exposure_scaled=exposure_scaled,
        covariates_scaled=covariates_scaled,
        observed_gps=observed,
        density_at=density_at,
    )


def _fit_gradient_boosting_gps(frame: pd.DataFrame, exposure: str, covariates: Sequence[str]) -> _GPSFit | None:
    exposure_scaled = _minmax_scale(frame[exposure])
    if exposure_scaled.nunique() < 2:
        return None
    covariates_scaled = pd.DataFrame(
        {column: _minmax_scale(frame[column]) for column in covariates},
        index=frame.index,
    )
    if covariates_scaled.empty:
        return None
    try:
        model = GradientBoostingRegressor(
            random_state=0,
            n_estimators=120,
            learning_rate=0.05,
            max_depth=2,
            subsample=0.9,
        )
        x = covariates_scaled.astype(float)
        y = exposure_scaled.astype(float)
        model.fit(x, y)
    except Exception:
        return None

    predicted = pd.Series(model.predict(covariates_scaled.astype(float)), index=frame.index, dtype=float)
    residuals = exposure_scaled - predicted
    residual_sd = float(np.std(residuals.to_numpy(dtype=float), ddof=1))
    if not np.isfinite(residual_sd) or residual_sd <= 0:
        return None
    x_columns = list(covariates_scaled.columns)

    def density_at(exposure_values_scaled: np.ndarray, covariate_values_scaled: pd.DataFrame) -> np.ndarray:
        design = pd.DataFrame(index=covariate_values_scaled.index)
        for column in x_columns:
            design[column] = pd.to_numeric(covariate_values_scaled[column], errors="coerce").astype(float)
        design = design[x_columns]
        predicted_values = np.asarray(model.predict(design.astype(float)), dtype=float)
        z = (np.asarray(exposure_values_scaled, dtype=float) - predicted_values) / residual_sd
        density = _normal_density(z) / residual_sd
        return np.maximum(np.asarray(density, dtype=float), np.finfo(float).eps)

    observed = pd.Series(
        density_at(exposure_scaled.to_numpy(dtype=float), covariates_scaled),
        index=frame.index,
        dtype=float,
    )
    return _GPSFit(
        method="gbm",
        exposure_scaled=exposure_scaled,
        covariates_scaled=covariates_scaled,
        observed_gps=observed,
        density_at=density_at,
    )


def _fit_gps_method(frame: pd.DataFrame, exposure: str, covariates: Sequence[str], method: str) -> _GPSFit | None:
    normalized = str(method).strip().lower()
    if normalized == "ols":
        return _fit_regression_gps(frame, exposure, covariates)
    if normalized == "gbm":
        return _fit_gradient_boosting_gps(frame, exposure, covariates)
    return None


def _weighted_midrank(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    sorted_weights = weights[order]
    ranks_sorted = np.zeros(len(values), dtype=float)
    total_weight = float(sorted_weights.sum())
    if total_weight <= 0:
        return ranks_sorted

    start = 0
    cumulative_before = 0.0
    while start < len(sorted_values):
        stop = start + 1
        while stop < len(sorted_values) and sorted_values[stop] == sorted_values[start]:
            stop += 1
        group_weight = float(sorted_weights[start:stop].sum())
        ranks_sorted[start:stop] = cumulative_before + group_weight / 2.0
        cumulative_before += group_weight
        start = stop
    ranks = np.empty(len(values), dtype=float)
    ranks[order] = ranks_sorted / total_weight
    return ranks


def _weighted_pearson(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float:
    weight_sum = float(weights.sum())
    if weight_sum <= 0:
        return np.nan
    x_mean = float(np.average(x, weights=weights))
    y_mean = float(np.average(y, weights=weights))
    x_centered = x - x_mean
    y_centered = y - y_mean
    cov = float(np.average(x_centered * y_centered, weights=weights))
    x_var = float(np.average(x_centered * x_centered, weights=weights))
    y_var = float(np.average(y_centered * y_centered, weights=weights))
    denom = float(np.sqrt(x_var * y_var))
    return cov / denom if denom > 0 else np.nan


def _weighted_spearman(x: pd.Series, y: pd.Series, weights: pd.Series | None = None) -> float:
    frame = pd.DataFrame({"x": x, "y": y})
    if weights is None:
        frame["w"] = 1.0
    else:
        frame["w"] = weights
    frame = frame.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    frame = frame.loc[frame["w"] > 0]
    if len(frame) < 3 or frame["x"].nunique() < 2 or frame["y"].nunique() < 2:
        return np.nan
    weight_values = frame["w"].to_numpy(dtype=float)
    x_rank = _weighted_midrank(frame["x"].to_numpy(dtype=float), weight_values)
    y_rank = _weighted_midrank(frame["y"].to_numpy(dtype=float), weight_values)
    return _weighted_pearson(x_rank, y_rank, weight_values)


def _balance_summary(
    frame: pd.DataFrame,
    *,
    exposure: str,
    confounders: Sequence[str],
    weights: pd.Series,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    exposure_values = pd.to_numeric(frame[exposure], errors="coerce")
    aligned_weights = weights.reindex(frame.index).astype(float)
    for variable in confounders:
        if variable not in frame.columns:
            continue
        values = pd.to_numeric(frame[variable], errors="coerce")
        raw = _weighted_spearman(exposure_values, values)
        weighted = _weighted_spearman(exposure_values, values, aligned_weights)
        abs_weighted = abs(weighted) if np.isfinite(weighted) else np.nan
        rows.append(
            {
                "variable": variable,
                "role": "confounder",
                "raw_correlation": raw,
                "weighted_correlation": weighted,
                "absolute_weighted_correlation": abs_weighted,
                "balanced_at_0_1": bool(np.isfinite(abs_weighted) and abs_weighted <= BALANCE_THRESHOLD),
                "n_complete": int(pd.DataFrame({"x": exposure_values, "v": values}).dropna().shape[0]),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "variable",
            "role",
            "raw_correlation",
            "weighted_correlation",
            "absolute_weighted_correlation",
            "balanced_at_0_1",
            "n_complete",
        ],
    )


def _mean_abs_balance(balance: pd.DataFrame) -> float:
    if balance.empty or "absolute_weighted_correlation" not in balance.columns:
        return np.inf
    values = pd.to_numeric(balance["absolute_weighted_correlation"], errors="coerce").dropna()
    if values.empty:
        return np.inf
    return float(values.mean())


def _effective_sample_size(weights: pd.Series | np.ndarray) -> float:
    values = np.asarray(weights, dtype=float)
    values = values[np.isfinite(values) & (values > 0)]
    if values.size == 0:
        return np.nan
    denom = float(np.sum(values * values))
    return float(values.sum() ** 2 / denom) if denom > 0 else np.nan


def _weighted_standardize(values: np.ndarray, weights: np.ndarray) -> np.ndarray | None:
    if float(weights.sum()) <= 0:
        return None
    mean = float(np.average(values, weights=weights))
    variance = float(np.average((values - mean) ** 2, weights=weights))
    if not np.isfinite(variance) or variance <= 0:
        return None
    return (values - mean) / np.sqrt(variance)


def _calibrate_balance_weights(
    frame: pd.DataFrame,
    *,
    exposure: str,
    confounders: Sequence[str],
    base_weights: pd.Series,
) -> tuple[pd.Series, pd.DataFrame, float | None, dict[str, object]]:
    base = pd.to_numeric(base_weights.reindex(frame.index), errors="coerce").fillna(0.0).astype(float)
    base_balance = _balance_summary(frame, exposure=exposure, confounders=confounders, weights=base)
    base_mean = _mean_abs_balance(base_balance)
    summary: dict[str, object] = {
        "status": "skipped",
        "base_mean_abs_weighted_correlation": base_mean if np.isfinite(base_mean) else None,
        "base_effective_sample_size": _effective_sample_size(base),
        "calibrated_effective_sample_size": _effective_sample_size(base),
        "nonzero_weight_n": int((base > 0).sum()),
        "ridge": 0.01,
        "clip": 6.0,
    }
    available = [column for column in confounders if column in frame.columns]
    if exposure not in frame.columns or not available:
        summary["status"] = "skipped_no_variables"
        return base, base_balance, base_mean if np.isfinite(base_mean) else None, summary

    numeric = frame[[exposure, *available]].apply(pd.to_numeric, errors="coerce")
    numeric["__weight__"] = base
    complete = numeric.replace([np.inf, -np.inf], np.nan).dropna()
    complete = complete.loc[complete["__weight__"] > 0]
    if len(complete) < max(10, len(available) + 2):
        summary["status"] = "skipped_sparse_positive_weights"
        return base, base_balance, base_mean if np.isfinite(base_mean) else None, summary

    weights = complete["__weight__"].to_numpy(dtype=float)
    exposure_rank = complete[exposure].rank(method="average").to_numpy(dtype=float)
    exposure_z = _weighted_standardize(exposure_rank, weights)
    if exposure_z is None:
        summary["status"] = "skipped_no_exposure_rank_variation"
        return base, base_balance, base_mean if np.isfinite(base_mean) else None, summary

    moment_columns: list[np.ndarray] = []
    used_variables: list[str] = []
    for variable in available:
        variable_rank = complete[variable].rank(method="average").to_numpy(dtype=float)
        variable_z = _weighted_standardize(variable_rank, weights)
        if variable_z is not None:
            moment_columns.append(exposure_z * variable_z)
            used_variables.append(variable)
    if not moment_columns:
        summary["status"] = "skipped_no_confounder_rank_variation"
        return base, base_balance, base_mean if np.isfinite(base_mean) else None, summary

    moments_matrix = np.column_stack(moment_columns)
    ridge = float(summary["ridge"])
    clip = float(summary["clip"])

    def objective(lam: np.ndarray) -> float:
        adjustment = np.clip(-moments_matrix.dot(lam), -clip, clip)
        calibrated = weights * np.exp(adjustment)
        weight_sum = float(calibrated.sum())
        if weight_sum <= 0:
            return np.inf
        moments = (calibrated[:, np.newaxis] * moments_matrix).sum(axis=0) / weight_sum
        return float(np.sum(moments * moments) + ridge * np.sum(lam * lam))

    try:
        result = minimize(
            objective,
            np.zeros(moments_matrix.shape[1], dtype=float),
            method="BFGS",
            options={"maxiter": 300, "gtol": 1e-6},
        )
        adjustment = np.clip(-moments_matrix.dot(result.x), -clip, clip)
        calibrated_values = weights * np.exp(adjustment)
    except Exception as exc:
        summary["status"] = "optimizer_failed"
        summary["warning"] = str(exc)
        return base, base_balance, base_mean if np.isfinite(base_mean) else None, summary

    calibrated = base.copy()
    calibrated.loc[complete.index] = calibrated_values
    calibrated_balance = _balance_summary(frame, exposure=exposure, confounders=confounders, weights=calibrated)
    calibrated_mean = _mean_abs_balance(calibrated_balance)
    if not np.isfinite(calibrated_mean) or (np.isfinite(base_mean) and calibrated_mean > base_mean):
        summary["status"] = "not_improved"
        summary["optimizer_success"] = bool(getattr(result, "success", False))
        summary["used_variables"] = used_variables
        return base, base_balance, base_mean if np.isfinite(base_mean) else None, summary

    summary.update(
        {
            "status": "ok",
            "optimizer_success": bool(getattr(result, "success", False)),
            "objective": float(getattr(result, "fun", np.nan)),
            "used_variables": used_variables,
            "calibrated_effective_sample_size": _effective_sample_size(calibrated),
            "calibrated_weight_sum": float(calibrated.sum()),
            "calibrated_weight_max": float(calibrated.max()),
            "calibrated_mean_abs_weighted_correlation": float(calibrated_mean),
        }
    )
    return calibrated, calibrated_balance, float(calibrated_mean), summary

def _matching_count_weights(gps: _GPSFit, *, num_bins: int, scale: float) -> pd.Series:
    n = len(gps.exposure_scaled)
    if n == 0:
        return pd.Series(dtype=float)
    exposure_values = gps.exposure_scaled.to_numpy(dtype=float)
    observed_gps = gps.observed_gps.to_numpy(dtype=float)
    query_positions = np.arange(n, dtype=int)
    counts = np.zeros(n, dtype=float)
    edges = np.linspace(0.0, 1.0, int(num_bins) + 1)
    for bin_index in range(int(num_bins)):
        left = edges[bin_index]
        right = edges[bin_index + 1]
        if bin_index == int(num_bins) - 1:
            in_bin = (exposure_values >= left) & (exposure_values <= right)
        else:
            in_bin = (exposure_values >= left) & (exposure_values < right)
        candidate_positions = np.flatnonzero(in_bin)
        if len(candidate_positions) == 0:
            continue
        center = (left + right) / 2.0
        counterfactual_gps = gps.density_at(
            np.repeat(center, n),
            gps.covariates_scaled,
        )
        gps_distance = np.abs(
            observed_gps[candidate_positions][np.newaxis, :]
            - counterfactual_gps[:, np.newaxis]
        )
        exposure_distance = np.abs(exposure_values[candidate_positions][np.newaxis, :] - center)
        score = float(scale) * gps_distance + (1.0 - float(scale)) * exposure_distance
        if len(candidate_positions) > 1:
            local_lookup = {int(position): offset for offset, position in enumerate(candidate_positions)}
            for position in np.intersect1d(query_positions, candidate_positions):
                score[int(position), local_lookup[int(position)]] = np.inf
        chosen_offsets = np.argmin(score, axis=1)
        chosen_positions = candidate_positions[chosen_offsets]
        np.add.at(counts, chosen_positions, 1.0)
    if float(counts.sum()) <= 0:
        counts = np.ones(n, dtype=float)
    return pd.Series(counts, index=gps.exposure_scaled.index, dtype=float)


def _empty_result(frame: pd.DataFrame, warnings: list[str]) -> ArcGISStyleMatchingResult:
    weights = pd.Series(1.0, index=frame.index, dtype=float)
    propensity = pd.Series(np.nan, index=frame.index, dtype=float)
    return ArcGISStyleMatchingResult(
        weights=weights,
        calibrated_weights=weights,
        propensity_scores=propensity,
        balance_summary=pd.DataFrame(
            columns=[
                "variable",
                "role",
                "raw_correlation",
                "weighted_correlation",
                "absolute_weighted_correlation",
                "balanced_at_0_1",
                "n_complete",
            ]
        ),
        calibrated_balance_summary=pd.DataFrame(
            columns=[
                "variable",
                "role",
                "raw_correlation",
                "weighted_correlation",
                "absolute_weighted_correlation",
                "balanced_at_0_1",
                "n_complete",
            ]
        ),
        grid=pd.DataFrame(
            columns=[
                "gps_method",
                "num_bins",
                "scale",
                "mean_abs_weighted_correlation",
                "max_abs_weighted_correlation",
                "nonzero_weight_n",
                "selected",
            ]
        ),
        selected_num_bins=None,
        selected_scale=None,
        selected_gps_method=None,
        selected_mean_abs_weighted_correlation=None,
        calibrated_mean_abs_weighted_correlation=None,
        calibration_summary={"status": "skipped"},
        warnings=tuple(warnings),
    )


def arcgis_style_matching_search(
    frame: pd.DataFrame,
    *,
    exposure: str,
    confounders: Sequence[str],
    num_bins: Sequence[int] | None = None,
    scales: Sequence[float] | None = None,
    gps_methods: Sequence[str] | None = None,
) -> ArcGISStyleMatchingResult:
    available_confounders = _available_numeric_columns(frame, confounders)
    warnings: list[str] = []
    if exposure not in frame.columns:
        return _empty_result(frame, [f"Exposure column '{exposure}' is missing."])
    if not available_confounders:
        return _empty_result(frame, ["No confounders are available for ArcGIS-style matching."])

    complete = _numeric_complete_frame(frame, [exposure, *available_confounders])
    if len(complete) < 3:
        return _empty_result(frame, ["Fewer than 3 complete rows are available for ArcGIS-style matching."])
    if complete[exposure].nunique() < 2:
        return _empty_result(frame, ["Exposure has no variation for ArcGIS-style matching."])

    requested_methods = tuple(dict.fromkeys(str(value).strip().lower() for value in (gps_methods or ("ols", "gbm"))))
    gps_by_method: dict[str, _GPSFit] = {}
    for method in requested_methods:
        if method not in {"ols", "gbm"}:
            warnings.append(f"GPS method '{method}' is not supported for ArcGIS-style matching.")
            continue
        fit = _fit_gps_method(complete, exposure, available_confounders, method)
        if fit is None:
            warnings.append(f"{method.upper()} GPS fit failed for ArcGIS-style matching.")
            continue
        gps_by_method[method] = fit
    if not gps_by_method:
        return _empty_result(frame, warnings or ["No GPS method fit succeeded for ArcGIS-style matching."])

    bin_candidates = tuple(int(value) for value in (num_bins or candidate_num_bins(len(complete))))
    bin_candidates = tuple(sorted({value for value in bin_candidates if 2 <= value <= len(complete)}))
    scale_candidates = tuple(float(value) for value in (scales or DEFAULT_SCALES))
    if not bin_candidates:
        return _empty_result(frame, ["No valid exposure bin candidates are available for ArcGIS-style matching."])
    if not scale_candidates:
        return _empty_result(frame, ["No valid scale candidates are available for ArcGIS-style matching."])

    rows: list[dict[str, object]] = []
    weights_by_candidate: dict[tuple[str, int, float], pd.Series] = {}
    for method, gps in gps_by_method.items():
        for bins in bin_candidates:
            for scale in scale_candidates:
                candidate_weights = _matching_count_weights(gps, num_bins=bins, scale=scale)
                weights_by_candidate[(method, bins, scale)] = candidate_weights
                balance = _balance_summary(
                    complete,
                    exposure=exposure,
                    confounders=available_confounders,
                    weights=candidate_weights,
                )
                abs_values = pd.to_numeric(balance["absolute_weighted_correlation"], errors="coerce").dropna()
                rows.append(
                    {
                        "gps_method": method,
                        "num_bins": int(bins),
                        "scale": float(scale),
                        "mean_abs_weighted_correlation": _mean_abs_balance(balance),
                        "max_abs_weighted_correlation": float(abs_values.max()) if not abs_values.empty else np.inf,
                        "nonzero_weight_n": int((candidate_weights > 0).sum()),
                        "selected": False,
                    }
                )

    grid = pd.DataFrame(rows)
    finite_objective = pd.to_numeric(grid["mean_abs_weighted_correlation"], errors="coerce")
    if finite_objective.replace([np.inf, -np.inf], np.nan).dropna().empty:
        return _empty_result(frame, ["ArcGIS-style matching grid produced no finite balance scores."])

    selected_index = int(finite_objective.idxmin())
    grid.loc[selected_index, "selected"] = True
    selected_row = grid.loc[selected_index]
    selected_method = str(selected_row["gps_method"])
    selected_key = (selected_method, int(selected_row["num_bins"]), float(selected_row["scale"]))
    selected_complete_weights = weights_by_candidate[selected_key]
    selected_gps = gps_by_method[selected_method]
    full_weights = pd.Series(0.0, index=frame.index, dtype=float)
    full_weights.loc[selected_complete_weights.index] = selected_complete_weights.astype(float)
    full_propensity = pd.Series(np.nan, index=frame.index, dtype=float)
    full_propensity.loc[selected_gps.observed_gps.index] = selected_gps.observed_gps.astype(float)
    selected_balance = _balance_summary(
        frame,
        exposure=exposure,
        confounders=available_confounders,
        weights=full_weights,
    )
    selected_objective = float(selected_row["mean_abs_weighted_correlation"])
    (
        calibrated_weights,
        calibrated_balance,
        calibrated_objective,
        calibration_summary,
    ) = _calibrate_balance_weights(
        frame,
        exposure=exposure,
        confounders=available_confounders,
        base_weights=full_weights,
    )

    return ArcGISStyleMatchingResult(
        weights=full_weights,
        calibrated_weights=calibrated_weights,
        propensity_scores=full_propensity,
        balance_summary=selected_balance,
        calibrated_balance_summary=calibrated_balance,
        grid=grid,
        selected_num_bins=int(selected_row["num_bins"]),
        selected_scale=float(selected_row["scale"]),
        selected_gps_method=selected_method,
        selected_mean_abs_weighted_correlation=selected_objective,
        calibrated_mean_abs_weighted_correlation=calibrated_objective,
        calibration_summary=calibration_summary,
        warnings=tuple(warnings),
    )
