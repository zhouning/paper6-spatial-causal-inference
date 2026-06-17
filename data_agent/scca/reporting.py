from __future__ import annotations

import json

from .specs import SCCAPaths, StudySpec


def write_report(
    spec: StudySpec,
    paths: SCCAPaths,
    credibility: dict[str, object],
    metadata: dict[str, object] | None = None,
) -> None:
    """Write a compact human-readable report and output manifest."""

    paths.ensure()
    reasons = credibility.get("reasons", [])
    reason_lines = "\n".join(f"- {reason}" for reason in reasons)
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
        "manifest": paths.manifest.name,
    }
    file_lines = "\n".join(
        f"- {key.replace('_', ' ').title()}: `{file_name}`"
        for key, file_name in files.items()
    )
    report = f"""# SCCA Analysis Report

## Study

- Name: `{spec.name}`
- Exposure: `{spec.exposure}`
- Outcome: `{spec.outcome}`
- Baseline outcome: `{spec.baseline_outcome}`

## Credibility Decision

`{credibility.get("decision")}`

## Reasons

{reason_lines}

## Output Files

{file_lines}
"""
    paths.analysis_report.write_text(report, encoding="utf-8")
    manifest = {
        "study": spec.name,
        "decision": credibility.get("decision"),
        "metadata": metadata or {},
        "files": files,
    }
    paths.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
