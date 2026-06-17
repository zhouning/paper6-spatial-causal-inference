from __future__ import annotations

import json

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import gaussian_kde
from sklearn.ensemble import GradientBoostingRegressor

from .specs import SCCAPaths, StudySpec


def _available_columns(features: pd.DataFrame, columns: tuple[str, ...]) -> list[str]:
    return [col for col in columns if col in features.columns]


def _model_covariates(features: pd.DataFrame, spec: StudySpec) -> tuple[list[str], list[str]]:
    covariates = _available_columns(features, spec.confounders)
    context_columns = _available_columns(features, spec.context_columns)
    ordered = list(dict.fromkeys(covariates + context_columns))
    return ordered, context_columns


def _complete_numeric_frame(frame: pd.DataFrame) -> pd.DataFrame:
    numeric = frame.apply(pd.to_numeric, errors="coerce")
    return numeric.replace([np.inf, -np.inf], np.nan).dropna()


def _ols_effect(y: pd.Series, x: pd.DataFrame, exposure_name: str) -> dict[str, float]:
    frame = _complete_numeric_frame(pd.concat([y.rename("__y__"), x], axis=1))
    if len(frame) < 2:
        raise ValueError("Not enough complete rows for OLS effect estimation.")
    x_const = sm.add_constant(frame.drop(columns=["__y__"]), has_constant="add")
    model = sm.OLS(frame["__y__"].astype(float), x_const.astype(float), missing="drop").fit()
    conf_int = model.conf_int()
    return {
        "coef": float(model.params.get(exposure_name, np.nan)),
        "se": float(model.bse.get(exposure_name, np.nan)),
        "p_value": float(model.pvalues.get(exposure_name, np.nan)),
        "ci_lower": float(conf_int.loc[exposure_name, 0]) if exposure_name in conf_int.index else np.nan,
        "ci_upper": float(conf_int.loc[exposure_name, 1]) if exposure_name in conf_int.index else np.nan,
        "r_squared": float(model.rsquared),
        "n": int(model.nobs),
    }


def _gps_weights(features: pd.DataFrame, spec: StudySpec, covariates: list[str]) -> np.ndarray:
    weights = np.ones(len(features), dtype=float)
    if len(features) < 3 or not covariates:
        return weights

    frame = _complete_numeric_frame(features[[spec.exposure, *covariates]])
    if len(frame) < 3 or frame[spec.exposure].nunique() < 2:
        return weights

    try:
        model = GradientBoostingRegressor(random_state=0)
        x = frame[covariates].astype(float)
        exposure = frame[spec.exposure].astype(float)
        model.fit(x, exposure)
        residuals = exposure - model.predict(x)
        residual_sd = float(np.std(residuals, ddof=1))
        if not np.isfinite(residual_sd) or residual_sd <= 0:
            return weights

        density = gaussian_kde(residuals)(residuals)
        conditional = np.maximum(density, np.finfo(float).eps)
        raw = 1.0 / conditional
        raw = np.where(np.isfinite(raw), raw, np.nan)
        mean = np.nanmean(raw)
        if not np.isfinite(mean) or mean <= 0:
            return weights

        weights[frame.index.to_numpy()] = raw / mean
        weights = np.where(np.isfinite(weights), weights, 1.0)
        overall_mean = weights.mean()
        if np.isfinite(overall_mean) and overall_mean > 0:
            weights = weights / overall_mean
    except Exception:
        return np.ones(len(features), dtype=float)
    return weights


def _erf_curve(features: pd.DataFrame, spec: StudySpec, weights: np.ndarray) -> pd.DataFrame:
    frame = _complete_numeric_frame(features[[spec.exposure, spec.outcome]])
    if frame.empty:
        return pd.DataFrame({"exposure": [np.nan], "response": [np.nan]})

    exposure = frame[spec.exposure].astype(float)
    grid = np.linspace(float(exposure.min()), float(exposure.max()), 50)
    if len(frame) < 2 or exposure.nunique() < 2:
        response = np.repeat(float(frame[spec.outcome].mean()), len(grid))
        return pd.DataFrame({"exposure": grid, "response": response})

    try:
        aligned_weights = pd.Series(weights, index=features.index).loc[frame.index].astype(float)
        aligned_weights = aligned_weights.replace([np.inf, -np.inf], np.nan).fillna(1.0)
        x_const = sm.add_constant(exposure.rename(spec.exposure), has_constant="add")
        model = sm.WLS(frame[spec.outcome].astype(float), x_const.astype(float), weights=aligned_weights).fit()
        response = model.predict(sm.add_constant(pd.Series(grid, name=spec.exposure), has_constant="add"))
    except Exception:
        response = np.repeat(np.nan, len(grid))
    return pd.DataFrame({"exposure": grid, "response": np.asarray(response, dtype=float)})


def estimate_effects(
    features: pd.DataFrame,
    spec: StudySpec,
    paths: SCCAPaths,
) -> dict[str, object]:
    paths.ensure()
    covariates, context_columns = _model_covariates(features, spec)
    results: dict[str, object] = {}
    estimates: list[dict[str, object]] = []

    baseline_x = features[[spec.exposure, *covariates]]
    baseline = _ols_effect(features[spec.outcome], baseline_x, spec.exposure)
    results["baseline_adjusted_ols"] = baseline
    estimates.append({"estimator": "baseline_adjusted_ols", **baseline})

    if "outcome_change" in features.columns:
        difference_x = features[[spec.exposure, *covariates]]
        difference = _ols_effect(features["outcome_change"], difference_x, spec.exposure)
        results["difference_outcome_ols"] = difference
        estimates.append({"estimator": "difference_outcome_ols", **difference})

    weights = _gps_weights(features, spec, covariates)
    erf = _erf_curve(features, spec, weights)
    gps_result = {
        "weight_min": float(np.min(weights)),
        "weight_max": float(np.max(weights)),
        "weight_mean": float(np.mean(weights)),
        "n": int(np.isfinite(weights).sum()),
    }
    results["generalized_propensity_erf"] = gps_result
    estimates.append(
        {
            "estimator": "generalized_propensity_erf",
            "coef": np.nan,
            "se": np.nan,
            "p_value": np.nan,
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "r_squared": np.nan,
            "n": gps_result["n"],
        }
    )

    pd.DataFrame(estimates).to_csv(paths.effect_estimates, index=False)
    erf.to_csv(paths.erf_curve, index=False)
    diagnostics = {
        "covariates": covariates,
        "context_columns": context_columns,
        "gps_weight_min": gps_result["weight_min"],
        "gps_weight_max": gps_result["weight_max"],
        "gps_weight_mean": gps_result["weight_mean"],
        "estimators": {
            name: {"n": int(value["n"])}
            for name, value in results.items()
            if isinstance(value, dict) and "n" in value
        },
    }
    paths.model_diagnostics.write_text(
        json.dumps(diagnostics, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return results
