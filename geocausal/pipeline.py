from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from data_agent.scca.context import build_context_features
from data_agent.scca.design import select_design
from data_agent.scca.diagnostics import audit_effects
from data_agent.scca.estimators import estimate_effects
from data_agent.scca.profiling import profile_table
from data_agent.scca.reporting import write_report
from data_agent.scca.robustness import (
    ROBUSTNESS_FILES,
    make_quantile_grid_groups,
    run_context_ablation,
    run_group_bootstrap,
    run_placebo_tests,
    summarize_erf_stability,
    write_robustness_outputs,
)
from data_agent.scca.specs import SCCAPaths

from . import __version__
from .config import GeoCausalConfig, validate_config
from .errors import GeoCausalConfigError, GeoCausalPipelineError
from .io import LoadedDataset, load_dataset


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    try:
        import numpy as np

        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, (np.floating, float)):
            numeric = float(value)
            return numeric if np.isfinite(numeric) else None
    except Exception:
        pass
    return value


def _ensure_output_writable(output_dir: Path) -> bool:
    output_dir.mkdir(parents=True, exist_ok=True)
    probe = output_dir / ".geocausal_write_probe"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()
    return True


def diagnose_config(config: GeoCausalConfig) -> dict[str, Any]:
    loaded = load_dataset(config)
    warnings = [*loaded.warnings, *validate_config(config, loaded.columns)]
    output_directory = config.resolve_output_dir()
    output_writable = _ensure_output_writable(output_directory)
    return {
        "case_name": config.case_name,
        "input_path": str(loaded.path),
        "input_format": loaded.format,
        "input_rows": int(len(loaded.frame)),
        "input_columns": int(len(loaded.frame.columns)),
        "geometry_available": loaded.geometry_available,
        "output_directory": str(output_directory),
        "output_writable": output_writable,
        "warnings": warnings,
        "errors": [],
    }


def _main_effect(effect_estimates_path: Path) -> float:
    if not effect_estimates_path.exists():
        return float("nan")
    estimates = pd.read_csv(effect_estimates_path)
    if estimates.empty:
        return float("nan")
    baseline = estimates.loc[estimates["estimator"] == "baseline_adjusted_ols"]
    row = baseline.iloc[0] if not baseline.empty else estimates.iloc[0]
    return float(pd.to_numeric(pd.Series([row.get("coef")]), errors="coerce").iloc[0])


def _bootstrap_group(
    config: GeoCausalConfig,
    features: pd.DataFrame,
    loaded_frame: pd.DataFrame,
) -> tuple[pd.DataFrame, str]:
    group_column = config.robustness.bootstrap.group_column
    if group_column:
        if group_column not in features.columns:
            raise GeoCausalConfigError(
                f"robustness.bootstrap.group_column is missing from the analysis frame: {group_column}"
            )
        return features, group_column

    spec = config.to_study_spec()
    if spec.coordinate_columns and all(column in loaded_frame.columns for column in spec.coordinate_columns):
        x_col, y_col = spec.coordinate_columns
        grouped = features.copy()
        grouped[x_col] = loaded_frame.loc[grouped.index, x_col]
        grouped[y_col] = loaded_frame.loc[grouped.index, y_col]
        grouped["_gc_grid_group"] = make_quantile_grid_groups(grouped, x_col, y_col, bins=4)
        return grouped, "_gc_grid_group"

    raise GeoCausalConfigError(
        "robustness.bootstrap.group_column is required when coordinate columns are unavailable."
    )


def _write_geocausal_manifest(
    config: GeoCausalConfig,
    loaded: LoadedDataset,
    paths: SCCAPaths,
    credibility: dict[str, Any],
    robustness_manifest: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    files = {
        "data_profile": paths.data_profile.name,
        "variable_candidates": paths.variable_candidates.name,
        "context_features": paths.context_features.name,
        "context_manifest": paths.context_manifest.name,
        "design_plan": paths.design_plan.name,
        "effect_estimates": paths.effect_estimates.name,
        "erf_curve": paths.erf_curve.name,
        "model_diagnostics": paths.model_diagnostics.name,
        "balance_summary": paths.balance_summary.name,
        "overlap_summary": paths.overlap_summary.name,
        "spatial_robustness": paths.spatial_robustness.name,
        "credibility_report": paths.credibility_report.name,
        "analysis_report": paths.analysis_report.name,
        "context_ablation": ROBUSTNESS_FILES["context_ablation"],
        "placebo_tests": ROBUSTNESS_FILES["placebo_tests"],
        "bootstrap_robustness": ROBUSTNESS_FILES["bootstrap_robustness"],
        "bootstrap_summary": ROBUSTNESS_FILES["bootstrap_summary"],
        "erf_stability": ROBUSTNESS_FILES["erf_stability"],
        "robustness_report": ROBUSTNESS_FILES["robustness_report"],
        "robustness_manifest": ROBUSTNESS_FILES["robustness_manifest"],
        "manifest": paths.manifest.name,
    }
    manifest = {
        "geocausal_version": __version__,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "case_name": config.case_name,
        "study": config.case_name,
        "config_path": str(config.config_path),
        "input_path": str(loaded.path),
        "input_format": loaded.format,
        "row_count": int(len(loaded.frame)),
        "column_count": int(len(loaded.frame.columns)),
        "exposure": config.variables.exposure,
        "outcome": config.variables.outcome,
        "unit_id": config.variables.unit_id,
        "baseline_outcome": config.variables.baseline_outcome,
        "confounders": list(config.variables.confounders),
        "context_columns": list(config.context.columns),
        "credibility_decision": credibility.get("decision"),
        "robustness_interpretation": robustness_manifest.get("robustness_interpretation"),
        "warnings": warnings,
        "files": files,
    }
    paths.manifest.write_text(
        json.dumps(_json_ready(manifest), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest


def run_analysis(config: GeoCausalConfig) -> dict[str, Any]:
    try:
        diagnosis = diagnose_config(config)
        warnings = list(dict.fromkeys(diagnosis["warnings"]))
        loaded = load_dataset(config)
        spec = config.to_study_spec()
        paths = SCCAPaths(output_dir=config.resolve_output_dir())
        paths.ensure()

        profile_table(loaded.frame, spec, paths)
        features, _ = build_context_features(loaded.frame, spec, paths)
        select_design(features, spec, paths)
        estimate_effects(features, spec, paths)
        credibility = audit_effects(features, spec, paths)
        write_report(
            spec,
            paths,
            credibility,
            metadata={
                "source_path": str(loaded.path),
                "config_path": str(config.config_path),
                "geocausal_version": __version__,
            },
        )
        main_coef = _main_effect(paths.effect_estimates)
        ablation = run_context_ablation(features, spec, config.case_name)
        placebo = run_placebo_tests(
            features,
            spec,
            config.case_name,
            [item.to_robustness_test() for item in config.robustness.placebo_exposures],
        )
        bootstrap_features, group_column = _bootstrap_group(config, features, loaded.frame)
        bootstrap_rows, bootstrap_summary = run_group_bootstrap(
            bootstrap_features,
            spec,
            config.case_name,
            group_column=group_column,
            n_replicates=config.robustness.bootstrap.n_replicates,
        )
        erf_curve = pd.read_csv(paths.erf_curve)
        erf_summary = summarize_erf_stability(erf_curve, config.case_name)
        main_limitation = "; ".join(str(reason) for reason in credibility.get("reasons", []))
        robustness_manifest = write_robustness_outputs(
            output_dir=paths.output_dir,
            case_name=config.case_name,
            original_decision=str(credibility.get("decision", "unknown")),
            main_coef=main_coef,
            main_limitation=main_limitation,
            ablation=ablation,
            placebo=placebo,
            bootstrap_rows=bootstrap_rows,
            bootstrap_summary=bootstrap_summary,
            erf_summary=erf_summary,
        )
        return _write_geocausal_manifest(config, loaded, paths, credibility, robustness_manifest, warnings)
    except GeoCausalConfigError:
        raise
    except Exception as exc:
        raise GeoCausalPipelineError(f"GeoCausal analysis failed: {exc}") from exc


def rebuild_report(output_dir: str | Path) -> dict[str, Any]:
    target = Path(output_dir)
    manifest_path = target / "manifest.json"
    if not manifest_path.exists():
        raise GeoCausalPipelineError(f"manifest.json is missing in {target}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = f"""# GeoCausal Analysis Report

## Case

`{manifest.get("case_name") or manifest.get("study")}`

## Interpretation

`{manifest.get("robustness_interpretation")}`

## Files

{chr(10).join(f"- {key}: `{value}`" for key, value in manifest.get("files", {}).items())}
"""
    (target / "geocausal_report.md").write_text(report, encoding="utf-8")
    return manifest
