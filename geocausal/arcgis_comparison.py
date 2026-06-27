from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


OUTPUT_FILES = {
    "comparison_csv": "arcgis_geocausal_comparison.csv",
    "report_md": "arcgis_geocausal_comparison.md",
    "manifest_json": "arcgis_geocausal_comparison_manifest.json",
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame()


def _path_from_manifest(value: Any, manifest_dir: Path) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    return path if path.is_absolute() else manifest_dir / path


def _finite_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _numeric_column(frame: pd.DataFrame, *names: str) -> pd.Series:
    lookup = {str(column).lower(): column for column in frame.columns}
    for name in names:
        column = lookup.get(name.lower())
        if column is not None:
            return pd.to_numeric(frame[column], errors="coerce")
    return pd.Series(dtype="float64")


def _safe_mean(series: pd.Series) -> float | None:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return None
    return float(numeric.mean())


def _safe_max(series: pd.Series) -> float | None:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return None
    return float(numeric.max())


def _erf_metrics(arcgis_erf: pd.DataFrame, geocausal_erf: pd.DataFrame) -> dict[str, float | int | None]:
    arc_exposure = _numeric_column(arcgis_erf, "EXPOSURE", "exposure")
    arc_response = _numeric_column(arcgis_erf, "RESPONSE", "response")
    geo_exposure = _numeric_column(geocausal_erf, "exposure", "EXPOSURE")
    geo_response = _numeric_column(geocausal_erf, "response", "RESPONSE")
    common_n = min(len(arc_exposure), len(geo_exposure), len(arc_response), len(geo_response))
    if common_n <= 0:
        return {
            "erf_common_rows": 0,
            "erf_exposure_mae": None,
            "erf_response_mae": None,
            "erf_response_rmse": None,
        }
    exposure_delta = arc_exposure.iloc[:common_n].to_numpy() - geo_exposure.iloc[:common_n].to_numpy()
    response_delta = arc_response.iloc[:common_n].to_numpy() - geo_response.iloc[:common_n].to_numpy()
    response_delta = response_delta[np.isfinite(response_delta)]
    exposure_delta = exposure_delta[np.isfinite(exposure_delta)]
    return {
        "erf_common_rows": int(common_n),
        "erf_exposure_mae": float(np.mean(np.abs(exposure_delta))) if exposure_delta.size else None,
        "erf_response_mae": float(np.mean(np.abs(response_delta))) if response_delta.size else None,
        "erf_response_rmse": float(np.sqrt(np.mean(response_delta**2))) if response_delta.size else None,
    }


def _balance_metrics(balance: pd.DataFrame) -> dict[str, float | None]:
    if balance.empty:
        return {
            "geocausal_confounder_mean_abs_weighted_correlation": None,
            "geocausal_all_mean_abs_weighted_correlation": None,
            "geocausal_max_abs_weighted_correlation": None,
        }
    if "absolute_weighted_correlation" in balance.columns:
        abs_weighted = pd.to_numeric(balance["absolute_weighted_correlation"], errors="coerce")
    else:
        abs_weighted = pd.to_numeric(balance.get("weighted_correlation"), errors="coerce").abs()
    roles = balance.get("role", pd.Series([""] * len(balance))).astype(str).str.lower()
    confounders = abs_weighted.loc[roles == "confounder"]
    return {
        "geocausal_confounder_mean_abs_weighted_correlation": _safe_mean(confounders),
        "geocausal_all_mean_abs_weighted_correlation": _safe_mean(abs_weighted),
        "geocausal_max_abs_weighted_correlation": _safe_max(abs_weighted),
    }


def _status_exact(left: Any, right: Any) -> str:
    return "match" if left == right and left is not None else "different"


def _status_lower_better(arcgis_value: float | None, geocausal_value: float | None) -> str:
    if arcgis_value is None or geocausal_value is None:
        return "unavailable"
    if abs(arcgis_value - geocausal_value) <= 1e-12:
        return "match"
    return "geocausal_lower" if geocausal_value < arcgis_value else "arcgis_lower"


def _metric_row(
    metric: str,
    arcgis: Any,
    geocausal: Any,
    *,
    status: str,
    interpretation: str,
) -> dict[str, Any]:
    delta = None
    arcgis_numeric = _finite_float(arcgis)
    geocausal_numeric = _finite_float(geocausal)
    if arcgis_numeric is not None and geocausal_numeric is not None:
        delta = geocausal_numeric - arcgis_numeric
    return {
        "metric": metric,
        "arcgis": arcgis,
        "geocausal": geocausal,
        "delta_geocausal_minus_arcgis": delta,
        "status": status,
        "interpretation": interpretation,
    }


def _comparison_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _metric_row(
            "analysis_rows",
            metrics.get("arcgis_final_n"),
            metrics.get("geocausal_joined_rows"),
            status=_status_exact(metrics.get("arcgis_final_n"), metrics.get("geocausal_joined_rows")),
            interpretation="Analysis-row parity after exposure trimming.",
        ),
        _metric_row(
            "erf_rows",
            metrics.get("arcgis_erf_rows"),
            metrics.get("geocausal_erf_rows"),
            status=_status_exact(metrics.get("arcgis_erf_rows"), metrics.get("geocausal_erf_rows")),
            interpretation="Both tools should emit a stable ERF grid for comparison.",
        ),
        _metric_row(
            "erf_response_mae",
            None,
            metrics.get("erf_response_mae"),
            status="computed" if metrics.get("erf_response_mae") is not None else "unavailable",
            interpretation="Mean absolute response difference on the common ERF grid.",
        ),
        _metric_row(
            "erf_response_rmse",
            None,
            metrics.get("erf_response_rmse"),
            status="computed" if metrics.get("erf_response_rmse") is not None else "unavailable",
            interpretation="Root-mean-square response difference on the common ERF grid.",
        ),
        _metric_row(
            "mean_weighted_balance",
            metrics.get("arcgis_mean_weighted_correlation"),
            metrics.get("geocausal_confounder_mean_abs_weighted_correlation"),
            status=_status_lower_better(
                metrics.get("arcgis_mean_weighted_correlation"),
                metrics.get("geocausal_confounder_mean_abs_weighted_correlation"),
            ),
            interpretation="Lower mean absolute weighted exposure-confounder correlation is better.",
        ),
    ]


def _render_report(rows: pd.DataFrame, metrics: dict[str, Any]) -> str:
    lines = [
        "# ArcGIS vs GeoCausal Benchmark",
        "",
        "## Summary Metrics",
        "",
        f"- ArcGIS analysis rows: `{metrics.get('arcgis_final_n')}`",
        f"- GeoCausal joined rows: `{metrics.get('geocausal_joined_rows')}`",
        f"- ArcGIS ERF rows: `{metrics.get('arcgis_erf_rows')}`",
        f"- GeoCausal ERF rows: `{metrics.get('geocausal_erf_rows')}`",
        f"- ERF response MAE: `{metrics.get('erf_response_mae')}`",
        f"- ERF response RMSE: `{metrics.get('erf_response_rmse')}`",
        f"- ArcGIS mean weighted balance: `{metrics.get('arcgis_mean_weighted_correlation')}`",
        "- GeoCausal confounder mean absolute weighted balance: "
        f"`{metrics.get('geocausal_confounder_mean_abs_weighted_correlation')}`",
        "",
        "## Comparison Table",
        "",
        rows.to_markdown(index=False),
        "",
    ]
    return "\n".join(lines)


def build_arcgis_geocausal_comparison(
    *,
    arcgis_manifest_path: str | Path,
    open_gis_dir: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    arcgis_manifest_path = Path(arcgis_manifest_path)
    open_gis_dir = Path(open_gis_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    arcgis_manifest = _read_json(arcgis_manifest_path)
    arcgis_summary = arcgis_manifest.get("summary", {}) if isinstance(arcgis_manifest, dict) else {}
    output_csvs = arcgis_manifest.get("output_csvs", {}) if isinstance(arcgis_manifest, dict) else {}
    arcgis_erf_path = _path_from_manifest(output_csvs.get("out_erf_table_csv"), arcgis_manifest_path.parent)
    arcgis_features_path = _path_from_manifest(output_csvs.get("out_features_csv"), arcgis_manifest_path.parent)

    arcgis_erf = _read_csv(arcgis_erf_path) if arcgis_erf_path else pd.DataFrame()
    arcgis_features = _read_csv(arcgis_features_path) if arcgis_features_path else pd.DataFrame()
    geocausal_joined = _read_csv(open_gis_dir / "analysis_joined.csv")
    geocausal_erf = _read_csv(open_gis_dir / "gis_erf_curve_200.csv")
    geocausal_balance = _read_csv(open_gis_dir / "gis_balance_summary.csv")
    geocausal_summary = _read_json(open_gis_dir / "gis_run_summary.json")

    metrics: dict[str, Any] = {
        "arcgis_original_n": arcgis_summary.get("original_n"),
        "arcgis_final_n": arcgis_summary.get("final_n"),
        "arcgis_exposure_trimmed_n": arcgis_summary.get("exposure_trimmed_n"),
        "arcgis_feature_rows": int(len(arcgis_features)) if not arcgis_features.empty else None,
        "arcgis_record_used_n": int(pd.to_numeric(arcgis_features.get("RECRD_USED"), errors="coerce").sum())
        if "RECRD_USED" in arcgis_features.columns
        else None,
        "arcgis_erf_rows": int(len(arcgis_erf)) if not arcgis_erf.empty else None,
        "arcgis_mean_weighted_correlation": arcgis_summary.get("mean_weighted_correlation"),
        "geocausal_joined_rows": int(len(geocausal_joined)) if not geocausal_joined.empty else None,
        "geocausal_erf_rows": int(len(geocausal_erf)) if not geocausal_erf.empty else None,
        "geocausal_evidence_grade": geocausal_summary.get("evidence_grade"),
    }
    metrics.update(_erf_metrics(arcgis_erf, geocausal_erf))
    metrics.update(_balance_metrics(geocausal_balance))

    rows = pd.DataFrame(_comparison_rows(metrics))
    comparison_path = output_dir / OUTPUT_FILES["comparison_csv"]
    report_path = output_dir / OUTPUT_FILES["report_md"]
    manifest_path = output_dir / OUTPUT_FILES["manifest_json"]
    rows.to_csv(comparison_path, index=False, encoding="utf-8")
    report_path.write_text(_render_report(rows, metrics), encoding="utf-8")

    manifest = {
        "arcgis_manifest_path": str(arcgis_manifest_path),
        "open_gis_dir": str(open_gis_dir),
        "comparison_csv": str(comparison_path),
        "report_md": str(report_path),
        "manifest_json": str(manifest_path),
        "metrics": metrics,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest