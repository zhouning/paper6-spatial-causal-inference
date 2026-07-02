from __future__ import annotations

import json
from typing import Iterable

import numpy as np
import pandas as pd

from .specs import SCCAPaths, StudySpec


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        return numeric if np.isfinite(numeric) else None
    return value


def _available(columns: Iterable[str], frame: pd.DataFrame) -> list[str]:
    return [column for column in columns if column in frame.columns]


def aggregate_to_outcome_support(
    frame: pd.DataFrame,
    spec: StudySpec,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Aggregate fine-support rows to the configured outcome support."""

    if not spec.aggregation_group:
        summary = {
            "scale_status": "same_support",
            "treatment_support": spec.treatment_support,
            "outcome_support": spec.outcome_support,
            "aggregation_group": None,
            "fine_units": int(len(frame)),
            "outcome_units": int(len(frame)),
            "warnings": [],
        }
        return frame.copy(), summary

    if spec.aggregation_group not in frame.columns:
        raise KeyError(f"Aggregation group column is missing: {spec.aggregation_group}")
    required = [spec.exposure, spec.outcome]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise KeyError(f"Required column(s) missing for scale aggregation: {', '.join(missing)}")

    numeric_columns = _available((spec.exposure, spec.outcome, *spec.confounders, *spec.context_columns), frame)
    working = frame[[spec.aggregation_group, *numeric_columns]].copy()
    warnings = []
    for column in numeric_columns:
        originally_missing = working[column].isna()
        working[column] = pd.to_numeric(working[column], errors="coerce")
        introduced_missing = int((working[column].isna() & ~originally_missing).sum())
        if introduced_missing:
            warnings.append(f"Column {column} has {introduced_missing} missing value(s) after numeric coercion.")

    grouped = working.groupby(spec.aggregation_group, dropna=False)
    aggregated = grouped[numeric_columns].mean().reset_index()
    counts = grouped.size().rename("n_fine_units").reset_index()
    aggregated = aggregated.merge(counts, on=spec.aggregation_group, how="left")
    mean_fine_units = None if aggregated.empty else float(aggregated["n_fine_units"].mean())
    summary = {
        "scale_status": "change_of_support",
        "treatment_support": spec.treatment_support,
        "outcome_support": spec.outcome_support,
        "aggregation_group": spec.aggregation_group,
        "fine_units": int(len(frame)),
        "outcome_units": int(len(aggregated)),
        "mean_fine_units_per_outcome": mean_fine_units,
        "warnings": warnings,
    }
    return aggregated, summary


def build_scale_summary(
    frame: pd.DataFrame,
    spec: StudySpec,
    paths: SCCAPaths,
) -> dict[str, object]:
    """Write and return a compact scale-support summary for one run."""

    _, summary = aggregate_to_outcome_support(frame, spec)
    json_ready_summary = _json_ready(summary)
    paths.ensure()
    paths.scale_summary.write_text(
        json.dumps(json_ready_summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return json_ready_summary
