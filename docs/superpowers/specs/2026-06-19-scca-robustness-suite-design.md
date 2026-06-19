# SCCA Robustness Suite Design

Date: 2026-06-19

## Goal

Strengthen the experimental evidence for the existing SCCA workflow before revising the manuscript. The current repository has three reproducible SCCA case studies, but the experimental conclusion still rests on one main adjusted estimate, one generalized-propensity ERF, and a small set of credibility diagnostics per case. This robustness suite should add cross-case ablations, placebo or negative-control tests, uncertainty checks, and ERF stability summaries so that the eventual paper can distinguish robust causal-support evidence from fragile spatial association.

## Scope

Included:

- South London Snow8 cholera supplier case.
- Soho Broad Street pump mechanism case.
- US county social-capital/longevity validation case.
- Reusable SCCA robustness helpers where they reduce duplication.
- Case-specific robustness runners that write new result artifacts under each existing case output directory.
- Tests for robustness calculations and runner output contracts.
- README commands for reproducing robustness outputs.

Excluded:

- Manuscript LaTeX edits.
- New datasets or a fourth case study.
- GeoFM, LLM, or world-model experiments.
- External county geometry joins.
- Full spatial econometric models such as CAR/SAR.

## Current Evidence State

### Snow8

Output directory:

- `paper/ijgis_submission_20260605/07_results/scca_snow8/`

Current result:

- Decision: `moderate_support`
- Baseline adjusted OLS coefficient: `83.17184030435816`
- OLS p-value: `0.0010203976314732412`
- Generalized propensity ERF range effect: `153.72327222942863`
- Main limitation: max exposure-balance correlation is high (`0.8282298232481067`)
- Existing leave-one-district-out sign stability: `true`

Main unresolved questions:

- Does the effect survive context-set ablations?
- Is the Southwark/Vauxhall exposure stronger than a plausible supplier placebo?
- How unstable is the estimate under small-sample resampling?

### Soho

Output directory:

- `paper/ijgis_submission_20260605/07_results/scca_soho/`

Current result:

- Decision: `moderate_support`
- Baseline adjusted OLS coefficient: `1.0873063923785589`
- OLS p-value: `1.1367236433101878e-37`
- Generalized propensity ERF range effect: `3.67581688920074`
- Main limitation: max exposure-balance correlation is high (`0.5425202150298992`)
- Existing leave-group robustness: not configured

Main unresolved questions:

- Does Broad Street pump proximity remain stronger than competing spatial explanations?
- Can coordinate-grid block robustness show that the result is not one local cluster?
- Do sewer and pestfield proximity act as competing exposures or confounders?

### County Social Capital

Output directory:

- `paper/ijgis_submission_20260605/07_results/scca_county_social_capital/`

Current result:

- Decision: `strong_support`
- Adjusted OLS coefficient: `0.1465206143525702`
- OLS p-value: `1.8919630150876344e-98`
- Generalized propensity ERF range effect: `6.735344715224969`
- Max exposure-balance correlation: `0.4261582467059024`
- Existing leave-one-state-out sign stability: `true`

Main unresolved questions:

- Is the social-association exposure stronger than weakly spatial or low-theory placebo exposures?
- Does the coefficient remain stable under state-cluster bootstrap?
- How much does each covariate family change the estimate?

## Robustness Modules

### Module 1: Context Ablation

Purpose:

- Test whether SCCA's context adjustment changes or stabilizes estimates rather than simply reporting one fully adjusted model.

Required output:

- `context_ablation.csv`

Rows:

- One row per ablation specification and estimator.

Required columns:

- `case`
- `specification`
- `estimator`
- `coef`
- `se`
- `p_value`
- `ci_lower`
- `ci_upper`
- `r_squared`
- `n`
- `included_columns`
- `status`

Common ablation specifications:

- `exposure_only`: exposure only.
- `confounders_only`: observed non-spatial confounders.
- `context_only`: spatial/context columns only.
- `confounders_plus_context`: current main specification.

Case-specific notes:

- Snow8 confounders: `rate1849`, `pop_house`, `pop1851`.
- Snow8 context: `d_sou`, `d_lam`, `d_pump`, `d_thames`, `d_unasc`.
- Soho confounders: `dis_pestf`, `dis_sewers`, `pestfield`.
- Soho context: `COORD_X`, `COORD_Y`.
- County confounders: socioeconomic, health, behavior, and environmental variables from the county spec.
- County context: `Shape_Length`, `Shape_Area`.

Interpretation:

- A main effect that appears only in the exposure-only model but collapses after confounder/context adjustment is not robust causal evidence.
- A main effect that remains directionally stable across plausible adjustment sets is stronger evidence.

### Module 2: Placebo and Negative-Control Exposures

Purpose:

- Test whether the workflow assigns similar effects to theoretically weaker or competing exposures.

Required output:

- `placebo_tests.csv`

Required columns:

- `case`
- `test_name`
- `exposure`
- `role`
- `expected_relation`
- `estimator`
- `coef`
- `se`
- `p_value`
- `ci_lower`
- `ci_upper`
- `n`
- `status`
- `interpretation`

Case-specific tests:

Snow8:

- Main exposure: `perc_sou`.
- Placebo or competing exposure: `perc_lam` when available.
- Expected relation: `perc_lam` should not reproduce the same harmful direction as `perc_sou`; if it does, supplier contrast interpretation is weak.

Soho:

- Main exposure: `bspump_proximity`.
- Competing exposures:
  - `pestfield_proximity = -log1p(dis_pestf)`.
  - `sewer_proximity = -log1p(dis_sewers)`.
- Expected relation:
  - Broad Street pump proximity should be stronger and more stable than competing proximity measures if the mechanism is pump-centered.
  - Strong competing effects should downgrade causal interpretation or be reported as rival mechanism evidence.

County:

- Main exposure: `SocialAssoc`.
- Placebo exposures:
  - `Shape_Length`.
  - `Shape_Area`.
- Expected relation:
  - Weakly spatial shape metrics should not provide a similarly interpretable longevity effect once confounders are controlled.
  - If shape metrics are strong, the case should be framed as vulnerable to residual spatial structure.

### Module 3: Bootstrap and Block Robustness

Purpose:

- Estimate whether effect direction and approximate magnitude are stable under resampling that respects case structure.

Required output:

- `bootstrap_robustness.csv`
- `bootstrap_summary.json`

Required CSV columns:

- `case`
- `bootstrap_type`
- `replicate`
- `coef`
- `n`
- `status`

Required JSON fields:

- `case`
- `bootstrap_type`
- `n_replicates_requested`
- `n_replicates_valid`
- `coef_mean`
- `coef_median`
- `coef_std`
- `ci_lower_2_5`
- `ci_upper_97_5`
- `sign_stability`
- `failure_count`

Case-specific bootstrap designs:

Snow8:

- Use district block bootstrap where `district` is available.
- Use a small default replicate count suitable for CI and local runs, such as 200.
- If too few unique districts make some replicates singular, record failures instead of hiding them.

Soho:

- Build coordinate grid blocks from `COORD_X` and `COORD_Y`.
- Default grid: 4 by 4 quantile bins.
- Resample grid blocks with replacement.
- Fit the main adjusted OLS in each replicate.

County:

- Use state block bootstrap by `STATE_NAME`.
- Default replicate count: 200.
- Fit the main adjusted OLS in each replicate.

Interpretation:

- High sign stability supports directional robustness.
- Wide intervals or high failure rates should be treated as evidence of fragility.

### Module 4: ERF Stability Summary

Purpose:

- Convert the ERF curve from a single range-effect number into a checkable response-shape artifact.

Required output:

- `erf_stability.json`

Required fields:

- `case`
- `n_grid`
- `response_at_min_exposure`
- `response_at_median_exposure`
- `response_at_max_exposure`
- `range_effect`
- `median_split_effect`
- `monotonic_direction`
- `monotonic_fraction`
- `max_adjacent_response_jump`
- `interpretation`

Interpretation:

- A mostly monotonic ERF in the expected direction strengthens continuous-exposure interpretation.
- A range effect driven by one endpoint or abrupt adjacent jump should be reported as fragile.

## Case-Level Output Contract

After implementation, each case output directory should contain the original SCCA artifacts plus:

- `context_ablation.csv`
- `placebo_tests.csv`
- `bootstrap_robustness.csv`
- `bootstrap_summary.json`
- `erf_stability.json`
- `robustness_report.md`
- `robustness_manifest.json`

The robustness report should be short and factual:

- main result recap,
- ablation stability,
- placebo/negative-control comparison,
- bootstrap sign stability and interval,
- ERF shape summary,
- final robustness interpretation.

## Cross-Case Summary

Add a consolidated output directory:

- `paper/ijgis_submission_20260605/07_results/scca_robustness_summary/`

Required files:

- `case_robustness_summary.csv`
- `case_robustness_report.md`

Required CSV columns:

- `case`
- `original_decision`
- `robustness_interpretation`
- `main_coef`
- `ablation_direction_stable`
- `placebo_weaker_than_main`
- `bootstrap_sign_stability`
- `erf_monotonic_direction`
- `main_limitation`

This cross-case table is intended to become a future manuscript results table after the user decides to revise the paper.

## Decision Rules

The robustness suite should not overwrite the original `credibility_report.json`. Instead, it should produce a second-layer interpretation:

- `robust_support`: original estimate is directionally stable, placebo tests do not reproduce the main effect, bootstrap sign stability is high, and ERF shape is interpretable.
- `bounded_support`: original estimate is consistent but at least one diagnostic remains weak.
- `fragile_support`: main estimate exists but placebo, ablation, bootstrap, or ERF checks suggest overinterpretation risk.

Expected starting hypothesis:

- Snow8 likely remains `bounded_support` because of high exposure-balance correlation and small sample size.
- Soho likely remains `bounded_support` unless competing proximity effects are weak.
- County may reach `robust_support` if shape placebo tests are weaker and state bootstrap remains stable.

## Implementation Approach

Prefer one reusable module plus small case runner updates:

- Create `data_agent/scca/robustness.py` for generic ablation, placebo, bootstrap, and ERF-summary functions.
- Add or update case-specific runners:
  - `data_agent/experiments/run_scca_snow8_robustness.py`
  - `data_agent/experiments/run_scca_soho_robustness.py`
  - `data_agent/experiments/run_scca_county_social_capital_robustness.py`
  - `data_agent/experiments/run_scca_robustness_summary.py`
- Add tests:
  - `data_agent/test_scca_robustness.py`
  - Extend case-specific tests only if needed for CLI contracts.

Keep the original SCCA runners and original generated outputs intact except when rerunning is explicitly required for compatibility.

## Testing Strategy

Use TDD.

Minimum tests:

- Context ablation writes the expected specifications and preserves the main adjusted estimate when using `confounders_plus_context`.
- Placebo tests run with alternate exposure names and do not mutate the original feature frame.
- Bootstrap summary reports valid replicate counts, confidence intervals, and sign stability.
- ERF stability summary detects increasing, decreasing, and non-monotonic curves.
- Each robustness runner writes its manifest and all expected files on a small fixture.
- Existing SCCA tests still pass.

Final verification commands:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_robustness.py data_agent/test_scca_county_social_capital.py data_agent/test_scca_soho.py data_agent/test_scca_snow8.py -q
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_causal_inference.py -q
```

## Acceptance Criteria

The robustness phase is complete when:

- All three case directories contain the robustness output contract files.
- The consolidated `scca_robustness_summary` directory exists.
- Each case has a second-layer robustness interpretation.
- Existing original SCCA results remain reproducible and are not overwritten in meaning.
- README contains reproduction commands for the robustness suite.
- The final response reports how the robustness suite changes the confidence level for Snow8, Soho, and County.

