# SCCA Manuscript Rebuild Design

## Decision

Paper 6 will abandon the original three-angle framework as the main manuscript claim. The current evidence does not support presenting statistical estimators, LLM causal reasoning, and geospatial world-model simulation as a validated integrated framework. The revised paper will instead be a method paper centered on Spatial Context Causal Adjustment (SCCA).

## Core Argument

In geographic observational studies, we show that SCCA makes spatial causal adjustment explicit and testable by constructing spatial-context adjustment sets, checking overlap and balance, running robustness diagnostics, and grading evidence across synthetic and real-data cases, with GeoFM embeddings treated only as one candidate context source whose current ablation shows no clear gain.

## Scope

The main manuscript will focus on:

- SCCA task formulation: exposure, outcome, observed confounders, spatial-context variables, adjustment set, diagnostics, and evidence grade.
- SCCA workflow: context feature construction, adjustment-set selection, overlap/common-support checks, balance diagnostics, effect estimation, spatial/block robustness, placebo checks, and reporting.
- Evidence synthesis: controlled synthetic benchmark audit, Chongqing UHI ablation and robustness, Snow cholera subdistrict case, Soho Broad Street pump case, and county social-capital external validation.
- Boundary evidence: AlphaEarth/GeoFM ablation remains in the paper as a negative or bounded result. It must not be claimed as an improvement.

The main manuscript will not claim:

- a validated three-angle framework;
- LLM-derived DAGs as causal evidence;
- world-model simulation as identified causal inference;
- GeoFM embeddings as superior to conventional remote-sensing/terrain covariates.

LLM DAG validation and world-model holdout validation may be mentioned only as auxiliary diagnostics or excluded from the main text. If mentioned, the text must state that they are not core evidence for SCCA.

## Evidence Requirements

The rebuild needs one additional experiment layer: a unified SCCA evidence synthesis table. It will standardize existing outputs into a reviewer-facing matrix with one row per major evidence component and explicit claim boundaries.

Required output files:

- `paper/ijgis_submission_20260605/07_results/scca_evidence_synthesis.csv`
- `paper/ijgis_submission_20260605/07_results/scca_evidence_synthesis_report.md`
- `paper/ijgis_submission_20260605/07_results/scca_evidence_synthesis_manifest.json`

Required table columns:

- `case`
- `data_type`
- `exposure`
- `outcome`
- `context_source`
- `best_adjustment`
- `effect_estimate`
- `balance_status`
- `robustness_status`
- `evidence_grade`
- `limitation`
- `manuscript_use`

Evidence grading:

- `core_support`: credible balance or robust synthetic performance plus useful robustness diagnostics.
- `bounded_support`: useful evidence but with clear support, scale, balance, or external-validity limits.
- `negative_ablation`: tested candidate source does not improve diagnostics or fails balance.
- `auxiliary_only`: not core SCCA evidence.

## Manuscript Architecture

The revised manuscript will use this structure:

1. Introduction: spatial confounding and weak adjustment diagnostics in GIS observational studies.
2. Related work: spatial causal inference, spatial confounding, matching/weighting diagnostics, and representation-based context variables.
3. SCCA method: formal problem definition and workflow.
4. Experiments: synthetic benchmark audit, Chongqing UHI ablation, cross-case robustness, GeoFM ablation.
5. Discussion: what SCCA solves, what it does not solve, GeoFM negative evidence, and why the former three-angle framing was not retained.
6. Conclusion: bounded contribution and reproducibility.

## Acceptance Criteria

- The manuscript title, abstract, contribution list, method, results, discussion, and conclusion are rewritten around SCCA.
- "Three-angle", "Angle A", "Angle B", and "Angle C" are removed from the main claim.
- The old Chongqing sign-reversal narrative is replaced by the current credible-balance result: the strongest observed SCCA specification is positive and modest, with `full_rs_context` ATT about `0.244` and max post-match SMD about `0.061`.
- GeoFM/AlphaEarth is reported as `geofm_no_clear_gain`.
- The evidence synthesis files are generated and covered by tests.
- README top-level framing matches the SCCA method paper direction.
