from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from data_agent.scca.specs import SCCAPaths, StudySpec

from .arcgis_style_erf import arcgis_style_erf_curve
from .arcgis_style_matching import arcgis_style_matching_search
from .config import GeoCausalConfig


PACKAGE_DIR_NAME = "open_gis_analysis_package"
BALANCE_THRESHOLD = 0.1


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        return numeric if np.isfinite(numeric) else None
    return value


def _safe_field_token(value: object) -> str:
    token = "".join(char.lower() if char.isalnum() else "_" for char in str(value).strip())
    token = "_".join(part for part in token.split("_") if part)
    if not token:
        return "target"
    if token[0].isdigit():
        return f"t_{token}"
    return token


def _series_or_nan(frame: pd.DataFrame, column: str) -> pd.Series:
    if column in frame.columns:
        return pd.to_numeric(frame[column], errors="coerce")
    return pd.Series(np.nan, index=frame.index, dtype=float)


def _weighted_correlation(x: pd.Series, y: pd.Series, weights: pd.Series | None = None) -> float:
    frame = pd.DataFrame({"x": x, "y": y})
    if weights is not None:
        frame["w"] = weights
    frame = frame.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 3 or frame["x"].nunique() < 2 or frame["y"].nunique() < 2:
        return np.nan
    if weights is None:
        return float(frame["x"].corr(frame["y"]))
    w = frame["w"].clip(lower=0)
    if float(w.sum()) <= 0:
        return np.nan
    x_centered = frame["x"] - float(np.average(frame["x"], weights=w))
    y_centered = frame["y"] - float(np.average(frame["y"], weights=w))
    cov = float(np.average(x_centered * y_centered, weights=w))
    x_var = float(np.average(x_centered * x_centered, weights=w))
    y_var = float(np.average(y_centered * y_centered, weights=w))
    denom = float(np.sqrt(x_var * y_var))
    return cov / denom if denom > 0 else np.nan


def _merge_target_exposure_fields(joined: pd.DataFrame, paths: SCCAPaths) -> pd.DataFrame:
    target_path = paths.output_dir / "target_exposures.csv"
    if not target_path.exists():
        return joined
    targets = pd.read_csv(target_path, encoding="utf-8-sig", dtype={"unit_id": "string"})
    required = {"unit_id", "method", "target_name"}
    if targets.empty or not required.issubset(targets.columns):
        return joined
    selected = targets.loc[targets["method"].astype(str) == "erf_delta_anchor"].copy()
    if selected.empty:
        return joined
    selected["unit_id"] = selected["unit_id"].astype(str)
    metric_columns = [
        column
        for column in selected.columns
        if column not in {"unit_id", "method", "target_name"}
    ]
    result = joined.copy()
    for target_name in selected["target_name"].dropna().astype(str).drop_duplicates():
        token = _safe_field_token(target_name)
        block = selected.loc[
            selected["target_name"].astype(str) == target_name,
            ["unit_id", *metric_columns],
        ].drop_duplicates(subset=["unit_id"], keep="first")
        block = block.rename(
            columns={column: f"gc_{token}_{_safe_field_token(column)}" for column in metric_columns}
        ).rename(columns={"unit_id": "gc_unit_id"})
        result = result.merge(block, how="left", on="gc_unit_id")
    return result


def _write_joined_table(
    *,
    package_dir: Path,
    features: pd.DataFrame,
    spec: StudySpec,
    paths: SCCAPaths,
) -> tuple[Path, list[str]]:
    warnings: list[str] = []
    joined = features.copy()
    joined["gc_unit_id"] = (
        joined[spec.unit_id].astype(str)
        if spec.unit_id in joined.columns
        else pd.Series([str(index) for index in joined.index], index=joined.index)
    )
    joined["gc_exposure"] = _series_or_nan(joined, spec.exposure)
    joined["gc_outcome"] = _series_or_nan(joined, spec.outcome)
    joined["gc_included"] = True
    joined["gc_trim_status"] = "included"

    gps_path = paths.generalized_propensity_scores
    if gps_path.exists():
        gps = pd.read_csv(gps_path, encoding="utf-8-sig", dtype={"unit_id": "string"})
        if "unit_id" in gps.columns:
            gps = gps.rename(columns={"unit_id": "gc_unit_id"})
            gps["gc_unit_id"] = gps["gc_unit_id"].astype(str)
            joined = joined.merge(gps, how="left", on="gc_unit_id")
        else:
            warnings.append("Generalized propensity score file has no unit_id column; using NaN scores and unit weights.")
    else:
        warnings.append("Generalized propensity score file is missing; using NaN scores and unit weights.")

    if "gc_propensity_score" not in joined.columns:
        joined["gc_propensity_score"] = np.nan
    if "gc_balancing_weight" not in joined.columns:
        joined["gc_balancing_weight"] = 1.0
    joined["gc_balancing_weight"] = pd.to_numeric(
        joined["gc_balancing_weight"], errors="coerce"
    ).fillna(1.0)
    joined = _merge_target_exposure_fields(joined, paths)

    output_path = package_dir / "analysis_joined.csv"
    joined.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path, warnings


def _write_balance_summary(
    *,
    package_dir: Path,
    features: pd.DataFrame,
    spec: StudySpec,
    weights: pd.Series,
) -> Path:
    rows: list[dict[str, Any]] = []
    variables = [
        *[(column, "confounder") for column in spec.confounders],
        *[(column, "context") for column in spec.context_columns],
    ]
    exposure = _series_or_nan(features, spec.exposure).reset_index(drop=True)
    position_weights = pd.Series(weights).reset_index(drop=True)
    for variable, role in variables:
        values = _series_or_nan(features, variable).reset_index(drop=True)
        raw = _weighted_correlation(exposure, values)
        weighted = _weighted_correlation(exposure, values, position_weights)
        abs_weighted = abs(weighted) if np.isfinite(weighted) else np.nan
        rows.append(
            {
                "variable": variable,
                "role": role,
                "raw_correlation": raw,
                "weighted_correlation": weighted,
                "absolute_weighted_correlation": abs_weighted,
                "balanced_at_0_1": bool(np.isfinite(abs_weighted) and abs_weighted <= BALANCE_THRESHOLD),
                "n_complete": int(pd.DataFrame({"x": exposure, "v": values}).dropna().shape[0]),
            }
        )
    output_path = package_dir / "gis_balance_summary.csv"
    pd.DataFrame(rows).to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def _write_erf_200(package_dir: Path, paths: SCCAPaths) -> tuple[Path, list[str]]:
    warnings: list[str] = []
    output_path = package_dir / "gis_erf_curve_200.csv"
    columns = ["exposure", "response", "source"]
    erf = pd.read_csv(paths.erf_curve) if paths.erf_curve.exists() else pd.DataFrame()
    if erf.empty or not {"exposure", "response"}.issubset(erf.columns):
        pd.DataFrame(columns=columns).to_csv(output_path, index=False, encoding="utf-8-sig")
        return output_path, ["ERF curve is missing or empty; Open GIS ERF-200 output is empty."]
    valid = erf.copy()
    valid["exposure"] = pd.to_numeric(valid["exposure"], errors="coerce")
    valid["response"] = pd.to_numeric(valid["response"], errors="coerce")
    valid = valid.replace([np.inf, -np.inf], np.nan).dropna(subset=["exposure", "response"])
    if len(valid) < 2:
        pd.DataFrame(columns=columns).to_csv(output_path, index=False, encoding="utf-8-sig")
        return output_path, ["ERF curve has fewer than two valid points; Open GIS ERF-200 output is empty."]
    valid = valid.sort_values("exposure")
    grid = np.linspace(float(valid["exposure"].min()), float(valid["exposure"].max()), 200)
    output = pd.DataFrame(
        {
            "exposure": grid,
            "response": np.interp(grid, valid["exposure"], valid["response"]),
            "source": "interpolated_from_erf_curve",
        }
    )
    for optional in ("ci_lower", "ci_upper"):
        if optional in valid.columns:
            optional_values = pd.to_numeric(valid[optional], errors="coerce").interpolate().bfill().ffill()
            output[optional] = np.interp(grid, valid["exposure"], optional_values)
    output.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path, warnings


def _write_arcgis_style_matching_outputs(
    *,
    package_dir: Path,
    features: pd.DataFrame,
    spec: StudySpec,
) -> tuple[pd.Series, pd.Series, pd.Series, Path, Path, Path, dict[str, Any], list[str]]:
    result = arcgis_style_matching_search(
        features,
        exposure=spec.exposure,
        confounders=spec.confounders,
    )
    grid_path = package_dir / "arcgis_style_matching_grid.csv"
    balance_path = package_dir / "arcgis_style_balance_summary.csv"
    calibrated_balance_path = package_dir / "arcgis_style_calibrated_balance_summary.csv"
    result.grid.to_csv(grid_path, index=False, encoding="utf-8-sig")
    result.balance_summary.to_csv(balance_path, index=False, encoding="utf-8-sig")
    result.calibrated_balance_summary.to_csv(calibrated_balance_path, index=False, encoding="utf-8-sig")
    selected = {
        "selected_num_bins": result.selected_num_bins,
        "selected_scale": result.selected_scale,
        "selected_mean_abs_weighted_correlation": result.selected_mean_abs_weighted_correlation,
        "calibrated_mean_abs_weighted_correlation": result.calibrated_mean_abs_weighted_correlation,
        "calibration": result.calibration_summary,
        "nonzero_weight_n": int((result.weights > 0).sum()),
        "calibrated_nonzero_weight_n": int((result.calibrated_weights > 0).sum()),
        "candidate_count": int(len(result.grid)),
    }
    return (
        result.propensity_scores,
        result.weights,
        result.calibrated_weights,
        grid_path,
        balance_path,
        calibrated_balance_path,
        selected,
        list(result.warnings),
    )


def _write_arcgis_style_erf_200(
    *,
    package_dir: Path,
    features: pd.DataFrame,
    spec: StudySpec,
    weights: pd.Series,
) -> tuple[Path, dict[str, Any], list[str]]:
    output_path = package_dir / "gis_arcgis_style_erf_curve_200.csv"
    result = arcgis_style_erf_curve(
        features,
        exposure=spec.exposure,
        outcome=spec.outcome,
        weights=weights,
        n_grid=200,
    )
    result.curve.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path, result.summary, list(result.warnings)


def write_open_gis_package(
    *,
    config: GeoCausalConfig,
    features: pd.DataFrame,
    spec: StudySpec,
    paths: SCCAPaths,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    package_dir = paths.output_dir / PACKAGE_DIR_NAME
    package_dir.mkdir(parents=True, exist_ok=True)

    joined_path, joined_warnings = _write_joined_table(
        package_dir=package_dir,
        features=features,
        spec=spec,
        paths=paths,
    )
    joined = pd.read_csv(joined_path)
    weights = pd.to_numeric(joined["gc_balancing_weight"], errors="coerce").fillna(1.0)
    balance_path = _write_balance_summary(
        package_dir=package_dir,
        features=features,
        spec=spec,
        weights=weights,
    )
    (
        arcgis_style_propensity,
        arcgis_style_weights,
        arcgis_style_calibrated_weights,
        arcgis_style_grid_path,
        arcgis_style_balance_path,
        arcgis_style_calibrated_balance_path,
        arcgis_style_summary,
        arcgis_style_warnings,
    ) = _write_arcgis_style_matching_outputs(
        package_dir=package_dir,
        features=features,
        spec=spec,
    )
    joined["gc_arcgis_style_propensity_score"] = arcgis_style_propensity.reset_index(drop=True)
    joined["gc_arcgis_style_matching_weight"] = arcgis_style_weights.reset_index(drop=True)
    joined["gc_arcgis_style_calibrated_weight"] = arcgis_style_calibrated_weights.reset_index(drop=True)
    joined.to_csv(joined_path, index=False, encoding="utf-8-sig")
    arcgis_style_erf_path, arcgis_style_erf_summary, arcgis_style_erf_warnings = _write_arcgis_style_erf_200(
        package_dir=package_dir,
        features=features,
        spec=spec,
        weights=arcgis_style_weights,
    )
    erf_path, erf_warnings = _write_erf_200(package_dir, paths)

    generated_files = {
        "analysis_joined": joined_path.name,
        "gis_balance_summary": balance_path.name,
        "gis_erf_curve_200": erf_path.name,
        "gis_arcgis_style_erf_curve_200": arcgis_style_erf_path.name,
        "arcgis_style_matching_grid": arcgis_style_grid_path.name,
        "arcgis_style_balance_summary": arcgis_style_balance_path.name,
        "arcgis_style_calibrated_balance_summary": arcgis_style_calibrated_balance_path.name,
        "gis_run_summary_json": "gis_run_summary.json",
        "gis_run_summary_markdown": "gis_run_summary.md",
    }
    warnings = [*joined_warnings, *erf_warnings, *arcgis_style_warnings, *arcgis_style_erf_warnings]
    summary = {
        "package_name": "Open GIS Analysis Package",
        "package_dir": PACKAGE_DIR_NAME,
        "case_name": config.case_name,
        "row_count": manifest.get("row_count"),
        "retained_row_count": int(len(features)),
        "exposure": config.variables.exposure,
        "outcome": config.variables.outcome,
        "confounders": list(config.variables.confounders),
        "context_columns": list(config.context.columns),
        "evidence_grade": manifest.get("evidence_grade"),
        "evidence_grade_reasons": manifest.get("evidence_grade_reasons", []),
        "result_summary": manifest.get("result_summary", {}),
        "arcgis_style_matching": arcgis_style_summary,
        "arcgis_style_erf": arcgis_style_erf_summary,
        "generated_files": generated_files,
        "warnings": warnings,
    }
    (package_dir / "gis_run_summary.json").write_text(
        json.dumps(_json_ready(summary), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    markdown = "# Open GIS Analysis Package\n\n"
    markdown += f"- Case: `{config.case_name}`\n"
    markdown += f"- Exposure: `{config.variables.exposure}`\n"
    markdown += f"- Outcome: `{config.variables.outcome}`\n"
    markdown += f"- Evidence grade: `{summary['evidence_grade']}`\n"
    markdown += "\n## Files\n\n"
    markdown += "\n".join(f"- {key}: `{value}`" for key, value in generated_files.items())
    markdown += "\n"
    if warnings:
        markdown += "\n## Warnings\n\n"
        markdown += "\n".join(f"- {warning}" for warning in warnings)
        markdown += "\n"
    (package_dir / "gis_run_summary.md").write_text(markdown, encoding="utf-8")
    return summary
