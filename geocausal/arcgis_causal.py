from __future__ import annotations

import csv
import importlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


ARCGIS_CAUSAL_TOOL = "arcpy.stats.CausalInferenceAnalysis"
ARCGIS_CAUSAL_DOC_URL = (
    "https://pro.arcgis.com/en/pro-app/latest/tool-reference/"
    "spatial-statistics/causal-inference-analysis.htm"
)


@dataclass(frozen=True)
class ArcGISCausalInferenceRequest:
    in_features: str
    outcome_field: str
    exposure_field: str
    confounders: tuple[str, ...]
    output_workspace: str
    output_stem: str = "arcgis_causal"
    ps_method: str = "REGRESSION"
    balancing_method: str = "MATCHING"
    enable_erf_popups: str = "NO_POPUP"
    target_outcomes: tuple[float, ...] = ()
    target_exposures: tuple[float, ...] = ()
    lower_exp_trim: float | None = 0.01
    upper_exp_trim: float | None = 0.99
    lower_ps_trim: float | None = 0.0
    upper_ps_trim: float | None = 1.0
    num_bins: int | None = None
    scale: float | None = None
    balance_type: str = "MEAN"
    balance_threshold: float | None = 0.1
    bw_method: str = "PLUG_IN"
    bandwidth: float | None = None
    create_bootstrap_ci: str = "NO_CI"
    output_csv_dir: str | None = None


def parse_arcgis_confounder_specs(confounders: Iterable[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw_spec in confounders:
        spec = str(raw_spec).strip()
        if not spec:
            continue
        if ":" in spec:
            field, role = spec.rsplit(":", 1)
            role = role.strip().upper()
        else:
            field, role = spec, "NUMERIC"
        field = field.strip()
        if not field:
            continue
        if role not in {"NUMERIC", "CATEGORICAL"}:
            raise ValueError(
                f"Unsupported ArcGIS confounder type for {field!r}: {role!r}. "
                "Use NUMERIC or CATEGORICAL."
            )
        rows.append([field, role])
    if not rows:
        raise ValueError("At least one confounding variable is required.")
    return rows


def _build_arcgis_confounder_value_table(arcpy: Any, rows: list[list[str]]) -> Any:
    value_table = arcpy.ValueTable(2)
    for field, role in rows:
        value_table.addRow(f"{field} {role}")
    return value_table


def _arcgis_table_path(workspace: Path, name: str) -> str:
    return str(workspace / name)


def _ensure_output_workspace(arcpy: Any, workspace: Path) -> None:
    workspace.parent.mkdir(parents=True, exist_ok=True)
    if workspace.suffix.lower() == ".gdb" and not arcpy.Exists(str(workspace)):
        arcpy.management.CreateFileGDB(str(workspace.parent), workspace.name)
    elif workspace.suffix.lower() != ".gdb":
        workspace.mkdir(parents=True, exist_ok=True)


def _prepare_input_table(arcpy: Any, request: ArcGISCausalInferenceRequest, workspace: Path) -> str:
    input_path = Path(request.in_features)
    if input_path.suffix.lower() not in {".csv", ".txt"}:
        return request.in_features
    table_name = f"{request.output_stem}_input"
    arcpy.conversion.TableToTable(
        in_rows=str(input_path),
        out_path=str(workspace),
        out_name=table_name,
    )
    return _arcgis_table_path(workspace, table_name)


def _target_values(values: tuple[float, ...]) -> list[float] | None:
    return list(values) if values else None


def _arcgis_version(arcpy: Any) -> str | None:
    try:
        info = arcpy.GetInstallInfo()
    except Exception:
        return None
    return info.get("Version") if isinstance(info, dict) else None


def _arcgis_product(arcpy: Any) -> str | None:
    try:
        return str(arcpy.ProductInfo())
    except Exception:
        return None


def _arcgis_messages(arcpy: Any) -> str:
    try:
        return str(arcpy.GetMessages())
    except Exception:
        return ""


def summarize_arcgis_causal_messages(messages: str) -> dict[str, int | float]:
    summary: dict[str, int | float] = {}

    int_patterns = {
        "original_n": r"Original number of records\s+(\d+)",
        "exposure_trimmed_n": r"Number of records removed by exposure trimming\s+(\d+)",
        "propensity_score_trimmed_n": r"Number of records removed by propensity score trimming\s+(\d+)",
        "final_n": r"Final number of records\s+(\d+)",
        "selected_num_bins": r"Number of exposure bins\s+(\d+)",
    }
    for key, pattern in int_patterns.items():
        match = re.search(pattern, messages)
        if match:
            summary[key] = int(match.group(1))

    float_patterns = {
        "selected_propensity_exposure_scale": (
            r"Relative weight of propensity score to exposure\s+([-+0-9.eE]+)"
        ),
        "bandwidth": r"Bandwidth \([^)]+\):\s+([-+0-9.eE]+)",
    }
    for key, pattern in float_patterns.items():
        match = re.search(pattern, messages)
        if match:
            summary[key] = float(match.group(1))

    mean_match = re.search(r"^\[Mean\]\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)", messages, re.MULTILINE)
    if mean_match:
        summary["mean_original_correlation"] = float(mean_match.group(1))
        summary["mean_weighted_correlation"] = float(mean_match.group(2))
    return summary


def _export_table_to_csv(arcpy: Any, table: str, csv_path: Path) -> str:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    field_names = [
        field.name
        for field in arcpy.ListFields(table)
        if getattr(field, "type", "") not in {"Blob", "Geometry", "OID", "Raster"}
    ]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(field_names)
        with arcpy.da.SearchCursor(table, field_names) as cursor:
            writer.writerows(cursor)
    return str(csv_path)


def run_arcgis_causal_inference(
    request: ArcGISCausalInferenceRequest,
    *,
    arcpy_module: Any | None = None,
    manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    arcpy = arcpy_module or importlib.import_module("arcpy")
    arcpy.env.overwriteOutput = True

    workspace = Path(request.output_workspace)
    _ensure_output_workspace(arcpy, workspace)
    in_features = _prepare_input_table(arcpy, request, workspace)
    out_features = _arcgis_table_path(workspace, f"{request.output_stem}_features")
    out_erf_table = _arcgis_table_path(workspace, f"{request.output_stem}_erf")
    confounder_table = parse_arcgis_confounder_specs(request.confounders)
    confounder_value_table = _build_arcgis_confounder_value_table(arcpy, confounder_table)

    arcpy.stats.CausalInferenceAnalysis(
        in_features=in_features,
        outcome_field=request.outcome_field,
        exposure_field=request.exposure_field,
        confounding_variables=confounder_value_table,
        out_features=out_features,
        ps_method=request.ps_method,
        balancing_method=request.balancing_method,
        enable_erf_popups=request.enable_erf_popups,
        out_erf_table=out_erf_table,
        target_outcomes=_target_values(request.target_outcomes),
        target_exposures=_target_values(request.target_exposures),
        lower_exp_trim=request.lower_exp_trim,
        upper_exp_trim=request.upper_exp_trim,
        lower_ps_trim=request.lower_ps_trim,
        upper_ps_trim=request.upper_ps_trim,
        num_bins=request.num_bins,
        scale=request.scale,
        balance_type=request.balance_type,
        balance_threshold=request.balance_threshold,
        bw_method=request.bw_method,
        bandwidth=request.bandwidth,
        create_bootstrap_ci=request.create_bootstrap_ci,
    )

    messages = _arcgis_messages(arcpy)
    exported_csvs: dict[str, str] = {}
    if request.output_csv_dir:
        csv_dir = Path(request.output_csv_dir)
        exported_csvs["out_features_csv"] = _export_table_to_csv(
            arcpy,
            out_features,
            csv_dir / f"{request.output_stem}_features.csv",
        )
        exported_csvs["out_erf_table_csv"] = _export_table_to_csv(
            arcpy,
            out_erf_table,
            csv_dir / f"{request.output_stem}_erf.csv",
        )

    manifest = {
        "tool": ARCGIS_CAUSAL_TOOL,
        "doc_url": ARCGIS_CAUSAL_DOC_URL,
        "arcgis_version": _arcgis_version(arcpy),
        "product": _arcgis_product(arcpy),
        "input_features": request.in_features,
        "prepared_input_features": in_features,
        "out_features": out_features,
        "out_erf_table": out_erf_table,
        "output_csvs": exported_csvs,
        "parameters": asdict(request),
        "confounding_variables": confounder_table,
        "summary": summarize_arcgis_causal_messages(messages),
        "messages": messages,
    }
    if manifest_path:
        path = Path(manifest_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        manifest["manifest"] = str(path)
    return manifest