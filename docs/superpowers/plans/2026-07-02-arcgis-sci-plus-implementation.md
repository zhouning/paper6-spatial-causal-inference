# ArcGIS SCI Plus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a focused GeoCausal extension that surpasses the ArcGIS Spatial Causal Inference / Causal Inference tool outputs, without claiming to exceed the full ArcGIS platform.

**Architecture:** Preserve ArcGIS-style exposure trimming, ERF, balance, and target-analysis comparability, then add open causal-risk auditing: residual spatial diagnostics, variable-role warnings, scale-aware estimands, and reproducible JSON/Markdown artifacts. Reuse completed SG-SCCA support commits only where they serve this narrower target.

**Tech Stack:** Python, pandas, numpy, statsmodels, pytest, existing `data_agent.scca` modules.

---

## Scope

This plan supersedes the broader SG-SCCA implementation plan for execution purposes. The target is ArcGIS SCI Plus, not a universal graph-orthogonal spatial causal theory platform.

Already completed commits that remain useful:

- `0e7feef` adds SG-SCCA path/spec support.
- `00a793c` and `07033b8` add scale-aware aggregation.
- `8403383` adds graph-orthogonal utilities as optional support, not the headline claim.

## Tasks

### Task A: ArcGIS SCI Plus helpers

**Files:**
- Create: `data_agent/scca/arcgis_sci_plus.py`
- Test: `data_agent/test_arcgis_sci_plus.py`

- [ ] Write tests for `arcgis_quantile_trim`, `solve_target_exposure`, and `build_arcgis_sci_plus_report`.
- [ ] Implement quantile trimming with 0.01/0.99 defaults.
- [ ] Implement nearest-ERF target exposure solver.
- [ ] Implement combined report with `arcgis_sci_parity` and `geo_causal_extensions`.
- [ ] Run `D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_arcgis_sci_plus.py -q`.
- [ ] Commit with `git commit -m "feat: add ArcGIS SCI Plus helpers"`.

### Task B: County ArcGIS SCI Plus runner

**Files:**
- Create: `data_agent/experiments/run_arcgis_sci_plus_county.py`
- Test: `data_agent/test_arcgis_sci_plus_county.py`

- [ ] Write a fixture workbook test that runs the county pipeline and writes `arcgis_sci_plus_report.json`.
- [ ] Implement runner using existing county loader, `build_context_features`, `select_design`, `estimate_effects`, `build_scale_summary`, and ArcGIS SCI Plus helpers.
- [ ] Manifest must include `arcgis_sci_plus_report`, `effect_estimates`, `erf_curve`, and `scale_summary`.
- [ ] Run `D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_arcgis_sci_plus_county.py -q`.
- [ ] Commit with `git commit -m "feat: add ArcGIS SCI Plus county runner"`.

### Task C: Manuscript framing

**Files:**
- Create: `paper/ijgis_submission_20260605/04_theory/arcgis_sci_plus_framing.md`

- [ ] Add a concise framing note stating that the comparison target is ArcGIS Spatial Causal Inference / Causal Inference, not the full ArcGIS platform.
- [ ] State the revised contribution: reproduce ArcGIS-style outputs and extend them with open spatial causal-risk diagnostics.
- [ ] Include claims to avoid: exceeding the ArcGIS platform, universal identification theory, and residual diagnostics proving no confounding.
- [ ] Verify with `rg -n "ArcGIS Spatial Causal Inference|not the full ArcGIS platform|target-analysis|spatial causal-risk|Claims to avoid" paper/ijgis_submission_20260605/04_theory/arcgis_sci_plus_framing.md`.
- [ ] Commit with `git commit -m "docs: frame ArcGIS SCI Plus contribution"`.

### Task D: Final verification

**Files:**
- Verify scoped implementation.

- [ ] Run `D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_arcgis_sci_plus.py data_agent/test_arcgis_sci_plus_county.py data_agent/test_sg_scca_scale.py data_agent/test_sg_scca_paths.py -q`.
- [ ] Run `D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_county_social_capital.py data_agent/test_scca_evidence_rules.py -q`.
- [ ] Run `git status --short --branch` and confirm a clean working tree.
