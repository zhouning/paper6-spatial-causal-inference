from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from geocausal.adapters import build_analysis_joined_table


def _format_float(value: Any, *, digits: int = 3) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "not available"
    return f"{numeric:.{digits}f}"


def parse_multivalue_text(parameter: Any) -> tuple[str, ...]:
    values = getattr(parameter, "values", None)
    if values:
        return tuple(str(value).strip() for value in values if str(value).strip())
    text = getattr(parameter, "valueAsText", None)
    if not text:
        return ()
    return tuple(part.strip() for part in str(text).split(";") if part.strip())


def parse_multivalue_floats(parameter: Any) -> tuple[float, ...]:
    values = getattr(parameter, "values", None)
    if values:
        return tuple(float(value) for value in values if str(value).strip())
    text = getattr(parameter, "valueAsText", None)
    if not text:
        return ()
    return tuple(float(part.strip()) for part in str(text).split(";") if part.strip())


def validate_requested_fields(
    *,
    requested_fields: tuple[str, ...],
    available_fields: tuple[str, ...],
    x_field: str | None = None,
    y_field: str | None = None,
) -> None:
    requested = []
    for field in (*requested_fields, x_field, y_field):
        if field and field not in requested:
            requested.append(field)
    available = set(available_fields)
    missing = [field for field in requested if field not in available]
    if missing:
        available_text = ", ".join(available_fields) if available_fields else "none"
        raise ValueError(
            "ArcGIS input is missing requested fields: "
            + ", ".join(missing)
            + f". Available fields: {available_text}"
        )


def export_input_dataset(
    input_dataset: str,
    csv_path: Path,
    *,
    fields: tuple[str, ...],
    x_field: str | None = None,
    y_field: str | None = None,
) -> dict[str, Any]:
    import arcpy

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    requested_fields = []
    for field in fields:
        if field and field not in requested_fields:
            requested_fields.append(field)

    available_fields = tuple(field.name for field in arcpy.ListFields(input_dataset))
    validate_requested_fields(
        requested_fields=tuple(requested_fields),
        available_fields=available_fields,
        x_field=x_field,
        y_field=y_field,
    )

    describe = arcpy.Describe(input_dataset)
    has_geometry = bool(getattr(describe, "shapeType", None))
    cursor_fields = list(requested_fields)
    for coordinate_field in (x_field, y_field):
        if coordinate_field and coordinate_field not in cursor_fields:
            cursor_fields.append(coordinate_field)
    derive_coordinates = has_geometry and not (x_field and y_field)
    if derive_coordinates:
        cursor_fields.append("SHAPE@")

    rows: list[dict[str, Any]] = []
    with arcpy.da.SearchCursor(input_dataset, cursor_fields) as cursor:
        for raw_row in cursor:
            record: dict[str, Any] = {}
            geometry = None
            for index, field_name in enumerate(cursor_fields):
                if field_name == "SHAPE@":
                    geometry = raw_row[index]
                else:
                    record[field_name] = raw_row[index]
            if derive_coordinates:
                point = None
                if geometry is not None:
                    point = getattr(geometry, "trueCentroid", None) or getattr(geometry, "centroid", None)
                record["_gc_x"] = getattr(point, "X", None)
                record["_gc_y"] = getattr(point, "Y", None)
            rows.append(record)

    pd.DataFrame(rows).to_csv(csv_path, index=False, encoding="utf-8-sig")
    return {
        "csv_path": str(csv_path),
        "coordinate_columns": (x_field, y_field)
        if x_field and y_field
        else (("_gc_x", "_gc_y") if derive_coordinates else None),
        "row_count": len(rows),
        "derived_coordinates": derive_coordinates,
    }


def summarize_manifest_messages(manifest: dict[str, Any]) -> list[str]:
    messages = [
        f"Case: {manifest.get('case_name')}",
        f"Rows analyzed: {manifest.get('row_count')}",
        f"Exposure: {manifest.get('exposure')}",
        f"Outcome: {manifest.get('outcome')}",
        f"Credibility: {manifest.get('credibility_decision')}",
        f"Robustness: {manifest.get('robustness_interpretation')}",
    ]
    evidence_grade = manifest.get("evidence_grade")
    if not evidence_grade:
        credibility = str(manifest.get("credibility_decision") or "")
        robustness = str(manifest.get("robustness_interpretation") or "")
        if credibility == "strong_support" and robustness == "robust_support":
            evidence_grade = "core_support"
        elif credibility or robustness:
            evidence_grade = "bounded_support"
    rule_ids = manifest.get("evidence_grade_rule_ids") or []
    rule_text = ", ".join(map(str, rule_ids)) if isinstance(rule_ids, list) else str(rule_ids)
    if evidence_grade:
        messages.append(f"Evidence grade: {evidence_grade} ({rule_text or 'no downgrade rules'}).")
    preprocessing = manifest.get("preprocessing", {})
    trim = preprocessing.get("exposure_trim", {}) if isinstance(preprocessing, dict) else {}
    removed_n = trim.get("removed_n")
    if removed_n is not None:
        messages.append(f"Exposure trimming removed {removed_n} records.")
    target_file = manifest.get("files", {}).get("target_exposures")
    if target_file:
        messages.append(f"Target exposure table: {target_file}")
    result_summary = manifest.get("result_summary", {})
    if isinstance(result_summary, dict):
        spatial = result_summary.get("spatial_diagnostics")
        if isinstance(spatial, dict):
            messages.append(
                "Spatial diagnostics: "
                f"{spatial.get('graph_method', 'unknown graph')}, "
                f"{spatial.get('edge_count', 'unknown')} edges, "
                f"exposure Moran I={_format_float(spatial.get('exposure_moran_i'))}, "
                f"residual Moran I={_format_float(spatial.get('residual_moran_i'))}."
            )
        slx = result_summary.get("spatial_slx_model")
        if isinstance(slx, dict) and slx.get("status") == "ok":
            messages.append(
                "SLX total effect: "
                f"{_format_float(slx.get('total_effect'))} "
                f"(p={_format_float(slx.get('total_p_value'))})."
            )
    result_summary_file = manifest.get("files", {}).get("result_summary_markdown")
    if result_summary_file:
        messages.append(f"Result summary: {result_summary_file}")
    return messages


def split_arcgis_output_table_path(output_table: str) -> tuple[str, str]:
    normalized = str(output_table).rstrip("\\/")
    lower = normalized.lower()
    for marker in (".gdb\\", ".gdb/"):
        index = lower.rfind(marker)
        if index >= 0:
            workspace_end = index + len(marker) - 1
            return normalized[:workspace_end], normalized[workspace_end + 1 :]
    path = Path(normalized)
    return str(path.parent), path.name


def copy_csv_to_arcgis_table(csv_path: Path, output_table: str | None) -> str | None:
    if not output_table:
        return None
    import arcpy

    out_path, out_name = split_arcgis_output_table_path(output_table)
    arcpy.conversion.TableToTable(
        in_rows=str(csv_path),
        out_path=out_path,
        out_name=out_name,
    )
    return output_table
