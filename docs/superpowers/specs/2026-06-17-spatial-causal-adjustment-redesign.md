# Paper6 Redesign Spec: Spatial Context Causal Adjustment

Date: 2026-06-17

## Purpose

Paper6 should be rebuilt around a real, auditable spatial causal-analysis algorithm rather than a broad integration story. The revised scientific question is:

> Given limited geographic observational data, can an algorithm construct spatial-context adjustment features, estimate exposure effects, and diagnose whether the resulting causal interpretation is credible?

The goal is not to force a positive result. The workflow must be able to conclude that a dataset supports only spatial association or mechanism exploration when balance, overlap, placebo, or spatial robustness diagnostics fail.

## Recommended Direction

Use a three-tier evidence design:

1. Main scientific case: South London cholera water-supplier data from `snow8/subdistricts.csv`.
2. Spatial mechanism case: Soho Broad Street pump data from `snow1` through `snow7`.
3. External cross-domain validation: US county social-capital/longevity data from `CausalInferAnalysis/CausalInferAnalysis/CountyData_TableToExcel.xlsx`.

The paper's core contribution becomes a spatial-context causal adjustment workflow. LLM reasoning, GeoFM embeddings, and world-model simulation become optional or future-facing modules, not evidence-bearing core claims.

## Data Inventory

### South London Cholera Case

Source:

- `D:\北大MEM\01-课程学习\02-技术核心课\数据可视化技术及应用\snow\snow8\subdistricts.csv`

Observed fields:

- Spatial units: `district`, `subdist`, and polygon geometry in the matching `subdistricts` shapefile/GeoJSON.
- Exposure: `perc_sou`, `perc_lam`, `supplierID`.
- Outcome: `rate1854`, optionally `deaths1854` with population offset `pop1854`.
- Baseline and confounding controls: `rate1849`, `deaths1849`, `pop1849`, `pop1851`, `pop_house`.
- Additional historical variables: `d_sou`, `d_lam`, `d_pump`, `d_thames`, `d_unasc`, `rAvSupR_49`, `rAvSupR_54`.

Primary causal estimand:

- Exposure-response effect of the Southwark and Vauxhall supply share (`perc_sou`) on 1854 cholera death rate, adjusted for pre-treatment mortality and demographic/spatial context.

Candidate designs:

- Continuous exposure generalized propensity score weighting.
- Baseline-adjusted outcome model using `rate1849` as pre-treatment control.
- Difference-style outcome: `rate1854 - rate1849`.
- Spatially robust uncertainty using adjacency or coordinate-derived block resampling.

### Soho Broad Street Pump Case

Sources:

- `snow1/deaths_nd_by_house.csv`
- `snow2/deaths_by_bldg.csv`
- `snow3/deaths_by_block.csv`
- `snow4/deaths_by_bsrings.csv`
- `snow5/deaths_by_8rings.csv`
- `snow6/pumps.csv`
- `snow7/sewergrates_ventilators.csv`

Observed fields:

- Outcomes: `deaths`, `death_dum`, `deathdens`.
- Exposure: `dis_bspump`, `distBSpump`, `distpump`, pump-ring `dist`, nearest `pumpID`.
- Spatial context and competing explanations: `dis_pestf`, `dis_sewers`, `pestfield`, `ventilator`, `date_code`, coordinates.

Primary role:

- Mechanism and diagnostic benchmark, not the main causal-identification case.

Candidate designs:

- Spatial exposure-response curve for distance to Broad Street pump.
- Placebo-pump analysis using other pumps from `snow6`.
- Negative-control or competing-mechanism checks using sewer/pestfield proximity.
- Spatial clustering of residuals after distance/context adjustment.

### US Social Capital and Longevity Case

Source:

- `D:\北大MEM\01-课程学习\02-技术核心课\数据可视化技术及应用\CausalInferAnalysis\CausalInferAnalysis\CountyData_TableToExcel.xlsx`

Observed fields:

- Exposure: `SocialAssoc`.
- Outcome: `AveAgeDeath`.
- Candidate confounders: `UnemployRate`, `pHHinPoverty`, `pNoHealthInsur`, `MentalHealth`, `pAdultSmoking`, `pAdultObesity`, `FastFood`, `pInsufficientSleep`, `pAlcohol`, `pSuicideDeaths`, `AirPollution`.
- Spatial identifiers: `STATE_NAME`, `CountyCode`, `County`, `FIPS`.

Primary role:

- Cross-domain validation of the continuous-exposure adjustment workflow.

Limitations:

- The currently inspected Excel file does not expose geometry directly, only identifiers and shape metrics. Spatial-neighbor diagnostics require joining county geometries by FIPS or limiting this case to non-spatial external validation.

## Algorithm Design

Name:

- Spatial Context Causal Adjustment (SCCA)

### Inputs

The algorithm accepts a tabular or geospatial dataset plus a study specification:

- unit id
- geometry or coordinates, when available
- exposure variable
- outcome variable
- optional baseline outcome
- candidate confounders
- optional known competing exposures or placebo exposures

The study specification can be manually provided in the first implementation. A later ADK/LLM layer may suggest variable roles, but final roles must remain explicit and auditable.

### Module 1: Data Profiler

Responsibilities:

- Load CSV, Excel, GeoJSON, shapefile, or GeoPackage where supported by the existing project environment.
- Infer column types, missingness, value ranges, and unique counts.
- Detect coordinates, geometry, spatial identifiers, candidate time/baseline fields, and obvious outcome/exposure candidates.
- Produce a machine-readable data audit JSON.

Outputs:

- `data_profile.json`
- `variable_candidates.csv`

### Module 2: Spatial Context Builder

Responsibilities:

- Generate context features that can act as observed spatial-confounding controls.
- Use only data available in the current dataset unless external context is explicitly configured.

Feature families:

- Coordinate terms: x/y, centered coordinates, polynomial or spline basis.
- Distance features: distance to named facilities, nearest facility id, ring/bin indicators.
- Neighborhood features: spatial lag of outcome baseline, spatial lag of confounders, local density.
- Areal context: area, population density, boundary-derived adjacency.
- Optional remote-sensing or GeoFM features in future work.

Outputs:

- `context_features.parquet` or `.csv`
- `context_feature_manifest.json`

### Module 3: Causal Design Selector

Responsibilities:

- Choose the analysis path from exposure and data structure.

Rules:

- Binary exposure: propensity score matching/weighting, ATT/ATE, balance diagnostics.
- Continuous exposure: generalized propensity score or covariate-balancing weighting, exposure-response function.
- Baseline outcome available: baseline-adjusted ERF, ANCOVA-style adjustment, or difference outcome.
- Small areal units: warn when sample size is too low for high-dimensional covariates.

Outputs:

- `design_plan.json`
- clear warnings when assumptions are weak.

### Module 4: Estimation Engine

Responsibilities:

- Estimate the configured causal effect.
- Keep estimator outputs comparable across datasets.

Required estimators:

- Continuous exposure ERF with covariate adjustment.
- Inverse probability / generalized propensity weighting.
- Baseline-adjusted regression for `rate1854 ~ exposure + rate1849 + context`.
- Optional matching for binary or thresholded exposures.
- Optional CATE model only after the main estimand is stable.

Outputs:

- `effect_estimates.csv`
- `erf_curve.csv`
- `model_diagnostics.json`

### Module 5: Audit and Robustness

This is the main difference from the current manuscript. Every effect estimate must come with credibility diagnostics.

Required diagnostics:

- Common support or exposure-overlap summary.
- Pre/post balance for confounders.
- Residual spatial autocorrelation where geometry is available.
- Spatial block or leave-area-out robustness.
- Placebo exposure test when available.
- Sensitivity to context feature set:
  - no context
  - coordinates only
  - observed confounders
  - observed confounders plus spatial context
  - reduced spatial context

Outputs:

- `balance_summary.csv`
- `overlap_summary.json`
- `spatial_robustness.csv`
- `placebo_tests.csv`
- `credibility_report.json`

### Module 6: Report Generator

Responsibilities:

- Generate reproducible tables, figures, and a concise narrative.
- Explicitly state whether the analysis supports causal interpretation, bounded causal interpretation, or association-only interpretation.

Outputs:

- `analysis_report.md`
- `figures/*.pdf`
- `tables/*.csv`

## Result Decision Rules

The workflow must support three possible conclusions.

### Strong Support

Criteria:

- Overlap is adequate.
- Main confounders are balanced after weighting/matching.
- Effect direction is stable across key specifications.
- Placebo exposures do not reproduce the main effect.
- Spatial residual autocorrelation is not driving the result, or robust uncertainty handles it.

Paper conclusion:

- SCCA improves credible spatial causal adjustment on the evaluated data.

### Moderate Support

Criteria:

- The estimator runs and diagnostics are informative.
- Some specifications are stable, but at least one important diagnostic remains weak.
- The workflow helps bound the conclusion and identify where the design is fragile.

Paper conclusion:

- SCCA is useful as an auditable decision-support workflow, but not all results support strong causal interpretation.

### Weak or Failed Support

Criteria:

- Poor overlap.
- Balance cannot be achieved.
- Placebo exposures are similarly strong.
- Spatial residual dependence remains large.
- Results reverse under minor specification changes.

Paper conclusion:

- The dataset supports spatial association or mechanism exploration only. The algorithm is valuable because it prevents overclaiming.

## Revised Paper Structure

1. Introduction
   - Problem: geographic causal studies often overclaim because spatial confounding and diagnostic failures are not systematically audited.
   - Contribution: SCCA workflow for spatial-context construction, estimation, and credibility diagnosis.

2. Related Work
   - Spatial causal inference.
   - Generalized propensity score and ERF.
   - Spatial confounding and spatial diagnostics.
   - GIS decision-support workflows.
   - LLM/GIS agents only as workflow support, not causal evidence.

3. Method
   - Formal problem setup.
   - Spatial context features.
   - Design selector.
   - Estimators.
   - Audit and robustness rules.

4. Data and Case Studies
   - South London water-supplier data.
   - Soho pump spatial mechanism data.
   - US social capital data.

5. Experiments
   - Context-feature ablations.
   - Balance and overlap diagnostics.
   - ERF/effect estimation.
   - Placebo and spatial robustness tests.
   - Cross-domain validation.

6. Results
   - Report results neutrally according to the decision rules above.

7. Discussion
   - What the workflow can and cannot establish.
   - When spatial context helps.
   - Why diagnostics matter as much as effect estimates.
   - Limits of the available data.

8. Conclusion
   - Reframe from "integrated AI causal system" to "auditable spatial causal adjustment workflow."

## Practical Product Direction

The algorithm should eventually power a GIS causal analyst workflow:

1. User provides a dataset and study question.
2. System profiles the data and proposes variable roles.
3. User confirms exposure, outcome, and confounders.
4. System builds spatial context features.
5. System estimates effects and runs diagnostics.
6. System returns:
   - a map-aware causal report,
   - tables and figures,
   - warnings about invalid causal claims.

The LLM layer may be useful for variable-role suggestions, plain-language explanations, and report drafting, but it must not be the source of causal validity.

## Implementation Scope for the Next Phase

No implementation is approved by this spec alone. The next phase should create an implementation plan with small checkpoints.

Suggested first checkpoint:

- Build a standalone SCCA experiment runner for `snow8/subdistricts.csv`.
- Produce a profile, design plan, ERF/effect estimates, balance diagnostics, and result decision.

Suggested second checkpoint:

- Add Soho pump placebo analysis and spatial exposure-response.

Suggested third checkpoint:

- Add US county social-capital validation.

Suggested fourth checkpoint:

- Rewrite the manuscript around observed results.

## Success Criteria

Minimum success for the project:

- The workflow runs end-to-end on at least one provided dataset.
- It produces effect estimates and diagnostics in reproducible files.
- It can return an "association-only" or "not credible for causal interpretation" result without failure.

Publication-level success:

- At least one case study shows stable, interpretable effects with acceptable diagnostics.
- At least one robustness or placebo test demonstrates why the audit layer is necessary.
- The manuscript claims are aligned with actual diagnostic outcomes.

Product-level success:

- A user can provide a GIS dataset and receive a structured causal-analysis report with explicit assumptions and credibility warnings.

## Open Risks

- The South London sample has only 32 spatial units, limiting model complexity and inference power.
- The Soho pump data is historically important but not a modern randomized or longitudinal design.
- The US county data may need external geometry for spatial diagnostics.
- Current Paper6 code may need restructuring to separate reusable causal algorithms from ADK/demo wrappers.
- If all diagnostics are weak, the paper must be written as a boundary-setting methods paper rather than a strong algorithm-performance paper.

## Non-Goals

- Do not claim GeoFM-specific validity unless new GeoFM features are directly evaluated.
- Do not claim world-model causal prediction without held-out spatiotemporal validation.
- Do not let LLM-generated DAGs replace identification assumptions or expert variable selection.
- Do not optimize figures or manuscript wording before the experimental evidence is rebuilt.
