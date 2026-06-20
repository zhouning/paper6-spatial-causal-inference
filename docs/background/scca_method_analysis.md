# SCCA Method Analysis

## Scope

This document explains the current SCCA method used in this repository for the
macOS notebook and QGIS workflow, with emphasis on:

- algorithmic principle
- theoretical basis
- similarities and differences versus other spatial or spatiotemporal causal methods
- how spatial and temporal factors affect causal interpretation

The explanation is grounded in the current repository implementation under
`geocausal/` and `data_agent/scca/`.

## What SCCA Is in This Repository

SCCA in this repository means **Spatial Context Causal Adjustment**.

It is best understood as a spatial observational causal-adjustment workflow, not
as a full spatiotemporal dynamic causal model.

For the county notebook case, the data are county-level spatial observations.
The workflow estimates the relationship between:

- exposure `A_i`
- outcome `Y_i`
- observed confounders `X_i`
- spatial context variables `S_i`

for each spatial unit `i`.

The causal target is the potential-outcome style quantity:

`E[Y_i(a)]`

which asks what the outcome would be if a unit's exposure were set to level
`a`, under the model assumptions.

## What the Current Implementation Actually Does

The implementation is centered in:

- `data_agent/scca/context.py`
- `data_agent/scca/design.py`
- `data_agent/scca/estimators.py`
- `data_agent/scca/diagnostics.py`
- `data_agent/scca/robustness.py`
- `geocausal/pipeline.py`

The workflow is:

1. Build an analysis table.
   - Read exposure, outcome, confounders, context columns, and optional grouping
     fields into one table.
   - For the county case, the main context variables are weak spatial descriptors
     such as `Shape_Length` and `Shape_Area`.

2. Estimate a main adjusted effect.
   - The main estimator is baseline-adjusted OLS:

     `Y = beta0 + beta1 * A + gamma * X + delta * S + error`

   - Here `beta1` is the main adjusted exposure effect.

3. Estimate a continuous-exposure response curve when exposure is not binary.
   - The implementation uses a generalized propensity score style weighting step
     and then estimates an exposure-response function, abbreviated ERF.

4. Audit credibility.
   - Check overlap
   - Check exposure-balance correlations
   - Check leave-one-group-out sign stability
   - Downgrade decisions when estimators are unstable or skipped

5. Run robustness checks.
   - context ablation
   - placebo tests
   - grouped bootstrap
   - ERF shape and monotonicity summary

6. Run spatial diagnostics.
   - build a spatial graph from polygon adjacency when geometry is available
   - fall back to coordinate k-nearest-neighbor graph when coordinate columns are
     available
   - report exposure Moran's I
   - report adjusted-model residual Moran's I
   - estimate whether neighboring exposure remains associated with the outcome
     after adjustment
   - compare the main exposure coefficient before and after adding neighboring
     exposure as a spatial sensitivity check

7. Append a formal spatially adjusted sensitivity estimator.
   - write an additional estimate to `effect_estimates.csv` using the main
     exposure plus neighboring exposure in the same regression
   - record how much the main exposure coefficient changes under that spatial
     adjustment

8. Run spatial block bootstrap for the spatially adjusted estimator.
   - split observations into coordinate quantile blocks
   - resample spatial blocks rather than individual units
   - report bootstrap mean, interval, and sign stability for the spatially
     adjusted coefficient

9. Run a richer spatial-lag adjustment when enough observations are available.
   - add neighboring exposure to the main adjusted regression
   - add neighboring confounder and neighboring spatial-context means
   - report `spatial_lag_adjusted_ols` as a stricter sensitivity estimator
   - use it to distinguish a pure neighboring-exposure signal from broader
     spatial clustering in neighboring socioeconomic or environmental context

10. Emit a formal SLX summary and coefficient table.
   - fit a spatial lag of X specification with local exposure/covariates and
     row-standardized neighboring exposure/covariates
   - write a coefficient table for direct exposure, neighboring exposure, local
     covariates, and neighboring covariates
   - summarize direct, indirect, and total effects implied by the fitted SLX
     model

11. Run spatial-graph specification sensitivity checks.
   - rebuild coordinate k-nearest-neighbor graphs with multiple `k` values
   - re-estimate Moran diagnostics and spatially adjusted coefficients under
     each graph
   - summarize whether the substantive conclusion depends on one arbitrary
     neighborhood definition

12. Run exposure-mapping sensitivity summaries.
   - use the fitted neighbor-exposure model together with the row-standardized
     spatial graph
   - summarize direct, indirect, and total exposure contributions implied by
     the graph
   - treat these as sensitivity-style exposure mappings, not as a fully
     identified network experiment

13. Optionally compute target-exposure outputs.
   - Given a target outcome, estimate the exposure change required to reach that
      target under the fitted model.

## Core Statistical Principle

The central idea is:

if the observed confounders `X` and the spatial context variables `S` are rich
enough, then after conditioning on them, the remaining association between
exposure `A` and outcome `Y` is more interpretable as a causal signal.

In shorthand:

`Y(a) independent of A | X, S`

This is not guaranteed by the data alone. It is an identifying assumption. SCCA
tries to make that assumption more plausible by explicitly forcing spatially
relevant context into the adjustment and by exposing robustness diagnostics.

## Theoretical Sources and Basis

### 1. Potential outcomes

The method follows the Neyman-Rubin potential outcomes tradition. The core
question is not just whether `A` and `Y` are associated, but how the outcome
would differ under alternative exposure values for the same spatial unit.

This brings in the standard observational identification assumptions:

- consistency
- conditional exchangeability / no unmeasured confounding given observed covariates
- positivity / overlap

### 2. Covariate adjustment and backdoor logic

The adjusted OLS part follows the standard causal-adjustment logic that if
relevant common causes of exposure and outcome are controlled, the remaining
effect estimate is more causally interpretable.

In Pearl-style language, this is a backdoor-adjustment strategy. In
Rubin-style language, it is outcome modeling under an ignorability assumption.

### 3. Generalized propensity score for continuous exposure

The county case uses a continuous exposure rather than a binary treatment.
Accordingly, the workflow uses a generalized propensity score style step rather
than simple binary propensity score matching.

In the current implementation:

- exposure is predicted from observed covariates using gradient boosting
- residual density is used to form weights
- weighted least squares is used to estimate an exposure-response curve

This is conceptually aligned with the generalized propensity score and
continuous-treatment dose-response literature.

### 4. Spatial confounding and spatial robustness

The spatial part is not a full spatial process model. Instead, it treats spatial
variables as context that may confound or distort causal interpretation.

This aligns with the broad spatial causal inference idea that geography can act
as:

- a source of confounding
- a source of dependence
- a source of heterogeneity
- a source of interference

SCCA addresses these primarily through adjustment and robustness diagnostics,
not through a full latent spatial random-field model.

### 5. Spatial econometric reference point: SLX

The richer spatial sensitivity layer now has a clearer spatial econometric
interpretation: it is closest to an **SLX model** (spatial lag of X).

In simplified notation:

`Y = beta0 + beta1 * A + theta * W A + gamma * X + phi * W X + error`

where `W` is a row-standardized spatial weights matrix derived from polygon
adjacency or coordinate k-nearest-neighbor relationships.

This matters because:

- `beta1` is the model-implied direct effect of local exposure
- `theta` is the model-implied indirect or spillover sensitivity tied to
  neighboring exposure
- `phi` captures neighboring confounder or neighboring context structure

Theoretical basis here comes from spatial econometrics rather than from the
potential-outcomes literature alone. In other words, the repository now
combines causal adjustment logic with a lightweight SLX-style spatial
regression layer for sensitivity analysis.

## How Spatial Factors Affect Causal Inference

Spatial factors matter in several distinct ways.

### 1. Spatial confounding

Space can influence both exposure and outcome.

For example, region-level socioeconomic conditions, health systems, urban form,
policy environment, pollution, and demographic structure may simultaneously
affect:

- how much social association a county has
- how high its average age at death is

If these spatially structured factors are not adjusted, the estimated effect of
the exposure can be biased.

This is the main reason SCCA introduces explicit spatial context variables.

### 2. Spatial dependence

Nearby units are often statistically dependent rather than independent.

Adjacent counties can share:

- healthcare systems
- environmental exposure
- labor markets
- transportation links
- policy environments

If this dependence is ignored, uncertainty can be understated and significance
can look stronger than it should.

The current implementation partially addresses this through:

- grouped bootstrap
- leave-one-group-out robustness
- geometry-based grid grouping when coordinates exist
- Moran-style residual autocorrelation diagnostics
- neighbor-exposure diagnostic regression
- spatial block bootstrap for the neighbor-adjusted estimator
- a richer spatial-lag sensitivity model that also adjusts neighboring
  confounders and neighboring context variables
- a formal SLX coefficient table and direct/indirect/total effect summary
- multi-graph sensitivity checks across alternative coordinate kNN definitions

It does not yet implement a full simultaneous spatial econometric model such as
SAR or CAR. The current implementation is closer to an operational SLX
sensitivity regression: it asks whether the main exposure coefficient is stable
after adding neighbor exposure and neighbor covariate or context summaries, and
it reports model-implied direct and indirect effects under that specification.

### 3. Spatial heterogeneity

The causal effect may vary by region.

An exposure may have one effect in dense urban areas and another in rural or
resource-based regions. In that sense, space can moderate the treatment effect.

The current SCCA implementation does not explicitly estimate a spatially varying
coefficient surface. Instead, it looks for instability through subgroup removal
and robustness patterns.

### 4. Spatial interference

In many spatial systems, one unit's exposure can affect another unit's outcome.

Examples:

- pollution transport
- spillover from nearby infrastructure
- commuting networks
- cross-county service use

This violates the simplest no-interference version of SUTVA.

The current SCCA workflow does not separately identify direct and indirect
spillover effects. The neighbor-exposure and spatial-lag adjusted estimates are
sensitivity analyses: they test whether a result is stable after introducing a
simple neighborhood exposure term, but they do not by themselves prove an
interference mechanism. Therefore, any setting with strong interference should
still be interpreted cautiously.

## How Temporal Factors Affect Causal Inference

For the current county notebook workflow, the method is mostly spatial and
cross-sectional rather than fully spatiotemporal.

Time enters only weakly in the present codebase:

- when a baseline outcome is available, the workflow can run
  `difference_outcome_ols`
- `context.py` can generate `outcome_change`
- study design can include a pre-treatment outcome as a confounder or baseline
  adjustment variable

This means the current implementation can use before-after style information as
an adjustment aid, but it is not a dynamic time-series or panel causal model.

It does not currently implement:

- difference-in-differences as a core estimator
- panel fixed effects
- marginal structural models over time
- dynamic treatment regimes
- Granger-style temporal causality
- explicit temporal spillover or lag structure

So for the county case, it is more accurate to call the method spatial causal
adjustment with limited temporal support, not a full spatiotemporal causal
engine.

## Similarities and Differences Versus Other Causal Methods

### Versus standard adjusted regression

Similarity:

- both estimate adjusted associations using covariates

Difference:

- SCCA adds explicit spatial context handling, overlap diagnostics, grouped
  spatial robustness, ERF outputs, placebo tests, and credibility grading

So SCCA is not just "run one regression", even though its core estimator is
still an adjusted regression.

### Versus propensity score matching or inverse probability weighting

Similarity:

- both aim to reduce confounding by modeling treatment assignment

Difference:

- SCCA handles continuous exposure using a generalized propensity score style
  approach and combines it with spatial context and GIS-facing outputs

### Versus difference-in-differences and synthetic control

Similarity:

- all are trying to recover causal effects from non-randomized data

Difference:

- DiD and synthetic control rely on explicit time structure and assumptions such
  as parallel trends
- SCCA is better suited to spatial observational settings without a clean
  treatment timing structure

The county notebook case should not be described as DiD-like identification.

### Versus spatial econometric models such as SAR, CAR, BYM, or GWR

Similarity:

- all acknowledge that space matters

Difference:

- spatial econometric models explicitly model spatial autocorrelation,
  neighborhood structure, or local coefficients
- SCCA focuses on causal adjustment, transparent variable roles, target-outcome
  reasoning, and robustness auditing

The current SCCA implementation now builds a spatial graph and uses it for
Moran diagnostics, neighbor exposure, spatial block bootstrap, and a richer
spatial-lag sensitivity regression with a formal SLX output table. It still
does not estimate a simultaneous SAR/CAR likelihood or a latent spatial random
effect.

More specifically:

- versus SLX:
  the current implementation is now quite close in regression form, but it uses
  SLX mainly as a sensitivity and interpretation layer inside a broader causal
  workflow rather than as a stand-alone spatial econometric endpoint
- versus SAR or SEM:
  current SCCA does not model simultaneous outcome feedback through `W Y` or a
  spatially correlated error process
- versus CAR/BYM:
  current SCCA does not place a Bayesian prior on latent areal spatial effects
- versus GWR:
  current SCCA does not estimate a smoothly varying local coefficient surface

### Versus causal forest or double machine learning

Similarity:

- all can be used for observational causal estimation

Difference:

- causal forest and DML are stronger for nonlinear high-dimensional adjustment
  and heterogeneous treatment effect estimation
- SCCA is more transparent, easier to audit in GIS/notebook workflows, and more
  explicit about spatial-context diagnostics

### Versus Bayesian spatiotemporal causal models

Similarity:

- both aim to make causal statements in spatial or spatiotemporal settings

Difference:

- Bayesian spatiotemporal models can explicitly represent latent spatial fields,
  temporal dynamics, and full posterior uncertainty
- SCCA is lighter-weight, more operational, and more explainable to GIS users,
  but less complete statistically

### Versus interference-aware spatial causal inference

Similarity:

- both recognize that geography may alter causal interpretation

Difference:

- interference-aware methods explicitly model spillover or neighborhood exposure
- current SCCA now reports a neighbor-average-exposure-based spillover
  sensitivity decomposition, but it still does not identify direct and indirect
  effects under a formal interference design

## What the Current Method Can Legitimately Claim

For the county notebook example, the strongest defensible claim is:

after adjusting for observed socioeconomic, health, environmental, and weak
spatial-context variables, the county-level exposure shows a stable positive
association with the outcome, and that result receives support from ERF,
bootstrap, ablation, placebo, and leave-one-group-out diagnostics.

After the spatial-diagnostic extension, the same county example is more
cautiously interpreted. The notebook run builds a coordinate k-nearest-neighbor
graph from county representative-point coordinates, finds positive exposure
spatial autocorrelation, and detects residual spatial autocorrelation after the
main adjusted model. It also finds that neighboring exposure remains associated
with the outcome after adjustment. The stricter spatial-lag adjustment further
adds neighboring confounder and neighboring context means; in the current county
run, the main coefficient remains positive but is smaller than the baseline
adjusted OLS estimate. The formal SLX summary likewise reports a positive local
direct effect together with a positive neighboring-exposure indirect component.
The credibility label is therefore downgraded from strong support to moderate
support, and the robustness summary becomes bounded support.

What it should not claim is:

- that the result proves a fully identified dynamic spatiotemporal causal effect
- that unmeasured spatial confounding has been eliminated
- that spillovers have been fully identified under a formal causal interference
  design
- that the workflow is equivalent to a full spatial adjacency or temporal panel
  causal model

## Practical Interpretation for This Repository

In this repository, SCCA should be understood as:

- a research-grade spatial causal adjustment workflow
- built around explicit covariate and spatial-context adjustment
- extended to continuous exposure through GPS/ERF logic
- strengthened by auditable diagnostics and robustness outputs
- suitable for notebook, ArcGIS, and QGIS integration

It is therefore closer to a transparent spatial causal evidence package than to
a universal spatiotemporal causal solver.

## Summary

The current SCCA workflow combines:

- potential-outcome causal reasoning
- observed confounder adjustment
- generalized propensity score style continuous-exposure handling
- exposure-response function estimation
- spatial context construction
- spatially aware robustness checks
- spatial graph diagnostics for residual spatial structure and neighboring
  exposure association
- formal spatial-neighbor and richer spatial-lag adjusted sensitivity
  estimators
- formal SLX direct/indirect/total effect summaries and full coefficient tables
- spatial block bootstrap for neighborhood-aware uncertainty checking
- spatial spillover sensitivity decomposition based on neighbor-average exposure
  terms
- exposure-mapping summaries for direct, indirect, and total graph-implied
  effects

Its main contribution is not that it solves every spatial or temporal causal
problem. Its contribution is that it turns spatial-context adjustment into a
reproducible, inspectable workflow that can run inside GIS and notebook
environments while keeping the causal assumptions visible.
