"""ArcGIS runtime audit for Paper 6 direct comparison evidence."""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results"
DEFAULT_OUTPUT_PATH = (
    DEFAULT_RESULTS_DIR
    / "paper6_multi_dataset_benchmark_matrix"
    / "arcgis_runtime_audit_snapshot.json"
)
ARCGIS_CAUSAL_TOOL = "arcpy.stats.CausalInferenceAnalysis"
ARCGIS_CAUSAL_DOC_URL = (
    "https://pro.arcgis.com/en/pro-app/latest/tool-reference/"
    "spatial-statistics/causal-inference-analysis.htm"
)


def _read_json(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    path = Path(path)
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _finite_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if np.isfinite(numeric) else None


def _arcgis_comparison_case_id(manifest_path: str | Path, manifest: dict[str, Any]) -> str:
    arcgis_manifest = _read_json(manifest.get("arcgis_manifest_path"))
    parameters = arcgis_manifest.get("parameters") if isinstance(arcgis_manifest, dict) else None
    if isinstance(parameters, dict) and parameters.get("output_stem"):
        return str(parameters["output_stem"])
    stem = Path(str(manifest_path)).stem.lower()
    if stem in {"arcgis_comparison_manifest", "arcgis_geocausal_comparison_manifest"}:
        return "county_arcgis_builtin"
    return stem.replace("_comparison_manifest", "").replace("arcgis_geocausal_comparison", "arcgis_builtin")


def _tool_metadata(arcpy_module: Any | None = None) -> dict[str, Any]:
    try:
        arcpy = arcpy_module or importlib.import_module("arcpy")
    except Exception as exc:  # pragma: no cover - depends on local ArcGIS licensing.
        return {
            "runtime_available": False,
            "tool": ARCGIS_CAUSAL_TOOL,
            "doc_url": ARCGIS_CAUSAL_DOC_URL,
            "runtime_error": str(exc),
        }

    stats = getattr(arcpy, "stats", None)
    tool = getattr(stats, "CausalInferenceAnalysis", None)
    signature = None
    if tool is not None:
        try:
            signature = str(inspect.signature(tool))
        except (TypeError, ValueError):
            signature = None
    try:
        install_info = arcpy.GetInstallInfo()
    except Exception:
        install_info = {}
    try:
        product = str(arcpy.ProductInfo())
    except Exception:
        product = None
    return {
        "runtime_available": tool is not None,
        "tool": ARCGIS_CAUSAL_TOOL,
        "doc_url": ARCGIS_CAUSAL_DOC_URL,
        "arcgis_version": install_info.get("Version") if isinstance(install_info, dict) else None,
        "product": product,
        "tool_signature": signature,
        "tool_doc_excerpt": (getattr(tool, "__doc__", "") or "")[:1200] if tool is not None else None,
    }


def _comparison_manifest_summary(path: str | Path) -> dict[str, Any]:
    manifest = _read_json(path)
    metrics = manifest.get("metrics") if isinstance(manifest, dict) else None
    metrics = metrics if isinstance(metrics, dict) else {}
    arcgis_balance = _finite_float(metrics.get("arcgis_mean_weighted_correlation"))
    geocausal_balance = _finite_float(
        metrics.get("geocausal_arcgis_style_calibrated_confounder_mean_abs_weighted_correlation")
    )
    return {
        "case_id": _arcgis_comparison_case_id(path, manifest),
        "comparison_manifest": str(path),
        "arcgis_manifest_path": manifest.get("arcgis_manifest_path"),
        "arcgis_balance": arcgis_balance,
        "geocausal_calibrated_balance": geocausal_balance,
        "calibrated_balance_win": (
            geocausal_balance is not None
            and arcgis_balance is not None
            and geocausal_balance < arcgis_balance
        ),
        "preferred_erf_response_mae": _finite_float(metrics.get("preferred_erf_response_mae")),
    }


def build_arcgis_runtime_audit(
    *,
    comparison_manifests: Sequence[str | Path],
    arcpy_module: Any | None = None,
) -> dict[str, Any]:
    comparisons = [_comparison_manifest_summary(path) for path in comparison_manifests]
    balance_wins = sum(1 for item in comparisons if item.get("calibrated_balance_win") is True)
    audit = _tool_metadata(arcpy_module)
    audit.update(
        {
            "n_direct_comparison_manifests": len(comparisons),
            "n_calibrated_balance_wins": balance_wins,
            "comparison_case_ids": [str(item["case_id"]) for item in comparisons],
            "comparison_manifests": comparisons,
        }
    )
    return audit


def write_arcgis_runtime_audit(
    *,
    comparison_manifests: Sequence[str | Path],
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    arcpy_module: Any | None = None,
) -> dict[str, Any]:
    audit = build_arcgis_runtime_audit(
        comparison_manifests=comparison_manifests,
        arcpy_module=arcpy_module,
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    audit["audit_json"] = str(path)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Write Paper 6 ArcGIS runtime audit snapshot.")
    parser.add_argument("--comparison-manifest", action="append", required=True)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args()
    audit = write_arcgis_runtime_audit(
        comparison_manifests=args.comparison_manifest,
        output_path=args.output,
    )
    print(json.dumps(audit, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
