# SG-SCCA ArcGIS Causal Inference Upgrade Design

Date: 2026-07-02

## Objective

Upgrade Paper 6 from a spatial causal audit workflow into a theory-backed
algorithmic contribution that specifically exceeds the ArcGIS Pro Causal
Inference / Spatial Causal Inference style tool used in the county social
capital comparison.

The target is not to exceed the entire ArcGIS platform. The target is narrower:
go beyond an ArcGIS-style causal inference tool that estimates exposure-response
relationships after trimming and balancing observed confounders.

## Baseline To Exceed

The local ArcGIS comparison report records the relevant baseline:

- Exposure trimming at the 0.01 and 0.99 quantiles.
- 3044 analysis records after removing 64 tail observations.
- Weighted average balance of 0.056, below the 0.10 threshold.
- Increasing exposure-response function for social capital and longevity.
- Qualitative shape interpretation: the slope becomes steeper after
  SocialAssoc is about 13.
- Target exposure example: a county at 4.6 social capital and 64.1 average age
  at death would need social capital around 34.6 to target age 70.

GeoCausal already reproduces the direction and magnitude of that result and
adds a knot-13 slope test in the ArcGIS-compatible trimmed sample. The upgrade
must turn this from an engineering comparison into a theoretical and algorithmic
advance.

## Core Claim

SG-SCCA extends ArcGIS-style spatial causal inference by adding:

- Scale-aware estimands for treatment and outcome measured on different spatial
  supports.
- Graph-orthogonal adjustment to reduce residual spatial confounding risk.
- Spatial block cross-fitting for nuisance models.
- Residual spatial bias bounds instead of purely heuristic evidence grades.
- Variable-role audits that distinguish confounders from mediators,
  post-treatment variables, and collider-risk variables.
- Spatial interference warnings through neighbor-exposure and graph sensitivity
  diagnostics.

The manuscript claim should be:

> ArcGIS-style causal inference tools estimate exposure-response relationships
> after observed-covariate balancing, but do not formalize residual spatial
> confounding, post-treatment spatial context risk, graph-dependent interference
> warnings, or treatment-outcome scale mismatch. SG-SCCA provides a
> scale-aware graph-orthogonal extension with estimand audits and residual
> spatial bias bounds.

## Theory Design

### Spatial causal graph

Use a graph-augmented causal structure:

- T: treatment or exposure.
- Y: outcome.
- X: non-spatial observed confounders.
- C: observed spatial context.
- U: latent graph-smooth spatial field.
- W T: neighbor exposure or spillover signal.
- G = (V, E): spatial graph.
- L: graph Laplacian.
- A: aggregation operator from fine treatment support to coarse outcome support.

The causal graph must explicitly allow:

- C -> T and C -> Y for observed spatial context.
- U -> T and U -> Y for unobserved spatial confounding.
- T -> W T -> Y or W T -> Y as an interference warning path.
- A(T_fine) -> Y_coarse for change-of-support cases.

### Scale-aware estimand

For same-support data, retain standard binary or continuous exposure estimands.
For change-of-support data, define the primary estimand on the outcome support:

beta_scale = d E[Y_s | A(T_f), A(X_f), A(C_f)] / d A(T_f)

This prevents a building-level ATT from being reported as the primary result
when the measured outcome is a MODIS pixel-level response.

### Graph-orthogonal adjustment

Let R_T be the treatment residual after removing observed non-spatial and
spatial context. Let Phi_k be the first k low-frequency eigenvectors of the
graph Laplacian L. SG-SCCA penalizes or removes projection of R_T onto Phi_k:

R_T_orth = R_T - Phi_k (Phi_k' Phi_k)^(-1) Phi_k' R_T

The estimator uses R_T_orth in an orthogonal score so that the treatment
contrast is less aligned with graph-smooth latent spatial structure.

### Bias-bound target

The theory should prove a conservative statement:

If latent spatial confounding U is graph-smooth and remaining projection of the
treatment residual on the graph-smooth subspace is small, then residual bias in
the treatment coefficient is bounded by a product of:

- graph-smoothness of U,
- remaining low-frequency projection of R_T_orth,
- residual outcome variation not explained by observed context.

This does not claim full identification under arbitrary unmeasured confounding.
It gives a measurable warning bound that ArcGIS-style tools do not provide.

## Algorithm Design

Algorithm name: Scale-aware Graph-Orthogonal Spatial Causal Adjustment
(SG-SCCA).

Inputs:

- Spatial units or table with coordinates/geometry.
- Treatment/exposure column.
- Outcome column.
- Observed confounders.
- Spatial context variables.
- Optional fine-to-coarse mapping or aggregation support.
- Spatial graph specification: adjacency, distance kernel, or kNN.
- Variable-role declarations.

Outputs:

- Primary same-scale or scale-aware estimand.
- ArcGIS-compatible ERF where relevant.
- Graph-orthogonal estimate and interval.
- Residual spatial bias-bound report.
- Residual Moran's I and permutation result.
- Neighbor exposure and graph sensitivity diagnostics.
- Variable-role audit.
- Scale estimand audit.
- Evidence grade tied to bound and diagnostics.

Steps:

1. Validate variable roles and reject impossible causal roles where declared.
2. Build G and L from geometry, coordinates, or user-provided graph.
3. If treatment and outcome supports differ, build A and aggregate to outcome
   support.
4. Fit nuisance models for treatment and outcome using spatial block
   cross-fitting.
5. Compute treatment residuals and graph low-frequency basis Phi_k.
6. Apply graph orthogonalization to treatment residuals.
7. Estimate the causal slope or ERF with an orthogonal score.
8. Compute residual spatial diagnostics and graph sensitivity.
9. Compute the residual spatial bias-bound score.
10. Generate a GIS-facing report and machine-readable JSON outputs.

## ArcGIS-Specific Superiority Tests

The upgrade should demonstrate superiority against the ArcGIS-style tool on
capabilities, not just on reproducing the same ERF.

Required comparison dimensions:

1. ArcGIS ERF reproduction
   - Same trimmed sample count.
   - Same direction and similar magnitude.
   - Knot-13 shape test reported quantitatively.

2. Spatial residual risk
   - Show whether the ArcGIS-compatible result still has residual Moran's I.
   - Show whether neighbor exposure is significant.
   - Report whether graph sensitivity changes sign or magnitude.

3. Variable-role risk
   - Show which context variables are safe confounders.
   - Flag possible post-treatment or mediator variables.
   - Demonstrate that lower balance does not automatically imply worse causal
     validity if a variable is not admissible.

4. Scale-aware risk
   - Use Chongqing as the main change-of-support example.
   - Show why an ArcGIS-style same-unit output would be misleading there.
   - Report the pixel-scale slope as primary and building-level ATT as
     diagnostic only.

5. Bias-bound output
   - Report a residual spatial bias-bound score that ArcGIS does not provide.
   - Show how the bound changes after graph orthogonalization.

## Experiment Matrix

### Synthetic benchmark

Create controlled data-generating processes with known effects:

- No latent spatial confounding.
- SAR latent confounding.
- CAR latent confounding.
- Distance-kernel latent confounding.
- Non-stationary latent field.
- Neighbor exposure / interference.
- Change-of-support from fine treatment to coarse outcome.

For each family, compare:

- ArcGIS-compatible ERF baseline.
- Existing SCCA workflow.
- SG-SCCA without graph orthogonalization.
- SG-SCCA with graph orthogonalization.

Metrics:

- Bias.
- RMSE.
- Coverage.
- Sign stability.
- Residual Moran's I.
- Neighbor-exposure false positive and true positive behavior.
- Bias-bound calibration.

### County social capital comparison

Use the existing ArcGIS-compatible county run as the direct tool comparison:

- Preserve 3044-row trimmed mode.
- Preserve ERF and knot-13 test.
- Add graph orthogonalization and residual bias-bound reporting.
- Show what SG-SCCA adds beyond the ArcGIS causal inference result.

### Chongqing urban heat case

Use Chongqing for the scale-aware estimand contribution:

- Fine treatment: building-level high-rise status or share.
- Coarse outcome: MODIS LST pixel.
- Primary estimand: pixel-scale high-rise-share slope.
- Diagnostic estimand: building-level matching ATT.
- Show scale audit, graph orthogonalization, residual spatial diagnostics, and
  bias-bound behavior.

### Fully open real-data case

Add or preserve a fully open case that does not depend on restricted Chongqing
inputs. This case should demonstrate reproducibility and prevent the paper from
depending solely on restricted data for the main empirical claim.

## Code Architecture

New modules should stay inside the existing SCCA package:

- data_agent/scca/scale.py
  - aggregation operators and same-support checks.
- data_agent/scca/graph_orthogonal.py
  - graph construction wrappers, Laplacian basis, residual projection, and
    graph-orthogonal residuals.
- data_agent/scca/orthogonal_estimators.py
  - spatial block cross-fitting and orthogonal score estimators.
- data_agent/scca/bias_bounds.py
  - residual spatial bias-bound computation and report fields.
- data_agent/experiments/run_sg_scca_arcgis_comparison.py
  - direct ArcGIS-compatible comparison rerun.
- data_agent/experiments/run_sg_scca_synthetic_benchmark.py
  - multi-family benchmark.

Existing ArcGIS, QGIS, CLI, and notebook surfaces should call the shared core
rather than duplicating logic.

## Testing Strategy

Unit tests:

- Aggregation operator preserves expected group means and counts.
- Graph orthogonalization reduces low-frequency projection of treatment
  residuals.
- Spatial block cross-fitting never trains and predicts on the same spatial
  block.
- Bias-bound output is monotonic with residual low-frequency projection in
  controlled fixtures.

Integration tests:

- County ArcGIS-compatible run still matches the 3044-row trimmed sample.
- Existing SCCA outputs remain backward compatible.
- SG-SCCA outputs include the new estimate, bias bound, role audit, and scale
  audit.

Benchmark tests:

- Synthetic no-confounding case keeps low bias.
- Graph-smooth latent confounding case improves over ArcGIS-compatible ERF and
  existing SCCA.
- Interference case triggers neighbor-exposure warnings.
- Change-of-support case reports coarse-scale estimand as primary.

## Manuscript Restructure

Proposed title:

Scale-aware Graph-Orthogonal Causal Adjustment for Geographic Observational
Studies

Revised structure:

1. Introduction: ArcGIS-style spatial causal inference is useful but incomplete.
2. Related work: spatial causal inference, graph signal processing, scale
   mismatch, GIS causal tools.
3. Theory: spatial causal graph, scale-aware estimand, graph-orthogonal
   adjustment, bias-bound proposition.
4. Algorithm: SG-SCCA workflow and outputs.
5. Experiments: synthetic benchmark, ArcGIS county comparison, Chongqing
   change-of-support, open real-data case.
6. Discussion: what SG-SCCA exceeds, what remains unidentifiable, and why the
   result is a bounded causal audit rather than causal certainty.

## Risks And Constraints

- The theorem must remain conservative. It should bound residual spatial bias
  under graph-smooth confounding, not claim full identification.
- Graph orthogonalization can remove true treatment signal if treatment itself
  is spatially smooth. The paper must report this trade-off.
- ArcGIS behavior is represented by the local PPT-derived comparison, not a full
  reverse-engineering of Esri internals.
- Chongqing restricted data cannot be the sole reproducibility evidence.
- The tool should not claim to reproduce all ArcGIS internals; it should claim
  to extend and audit the causal interpretation beyond ArcGIS-style outputs.

## Acceptance Criteria

The upgrade is complete when:

- The paper defines SG-SCCA as a model and estimator, not only a workflow.
- At least one theorem or proposition gives a residual spatial bias-bound
  statement.
- The algorithm has executable implementation and tests.
- The county case reproduces the ArcGIS-compatible baseline and adds SG-SCCA
  diagnostics.
- The synthetic benchmark shows when SG-SCCA improves, fails, and warns.
- The Chongqing case is reframed around scale-aware estimands.
- The manuscript clearly says that SG-SCCA exceeds ArcGIS Causal Inference in
  causal-risk auditing and spatial bias-bound reporting, not in general GIS
  platform functionality.
