# Chongqing UHI Ablation and Robustness Design

Date: 2026-06-20

## Goal

Strengthen the Paper 6 Chongqing urban heat island case before editing the
manuscript. The new experiment should replace the current two-row PSM summary
with reproducible ablation, balance, matched-count, threshold-placebo, spatial
bootstrap, and residual spatial diagnostics outputs.

## Scope

Included:

- A reusable, testable analysis module for the Chongqing UHI case.
- PSM ablations across raw, coordinate, geometry, terrain, Sentinel index,
  Sentinel band, full remote-sensing context, and PCA context specifications.
- Standardized covariates, common-support trimming, nearest-neighbor matching,
  explicit propensity-score calipers, matched counts, and per-covariate SMD
  before and after matching.
- Spatial block bootstrap using coordinate grid blocks.
- Treatment-threshold placebos for 8, 10, and 12 floors.
- Residual spatial autocorrelation diagnostics using a distance-band Moran-like
  statistic with permutation p-values.
- Output files required by the IJGIS internal review note.
- Script wiring so `scripts/causal_case_study.py` remains the data-extraction
  entry point but delegates analysis to the reusable module.

Excluded:

- QGIS provider work.
- Notebook work.
- Manuscript prose edits.
- Direct AlphaEarth / GeoFM ablation. That remains a separate experiment.

## Current Evidence State

The existing `scripts/causal_case_study_results.json` reports a large sign
change after matching, but the match diagnostics are not credible enough:

- no continuous-covariate standardization before propensity estimation,
- no common-support trimming,
- no enforced caliper in the reported rows,
- no per-covariate pre/post SMD table,
- max post-match SMD around `1.34`, far above the usual `0.1` threshold.

The case should therefore be treated as unproven until the new diagnostics show
acceptable balance or force the paper to report it as a fragile association.

## Design

### Analysis Module

Create `data_agent/experiments/chongqing_uhi_analysis.py`.

Responsibilities:

1. Define the feature groups used by the ablation table.
2. Prepare numeric analysis frames from extracted building, LST, Sentinel, and
   DEM columns.
3. Estimate propensity scores on standardized continuous covariates.
4. Enforce common support by retaining observations inside overlapping treated
   and control propensity-score ranges.
5. Match treated units to nearest controls by propensity score using a caliper.
6. Compute ATT, bootstrap CI over matched pairs, matched counts, drop rates, and
   pre/post SMD for every covariate.
7. Run threshold-placebo analyses by rebuilding treatment indicators at 8, 10,
   and 12 floors.
8. Run spatial block bootstrap by resampling coordinate grid blocks.
9. Compute residual spatial diagnostics on matched residuals.
10. Write all required CSV/JSON/Markdown artifacts.

The module should avoid Google Earth Engine dependencies. GEE extraction stays
in the existing script wrapper.

### Feature Specifications

Required ablation variants:

- `raw`: no covariates, reported as raw treated-control difference.
- `coordinates_only`: `centroid_x`, `centroid_y`.
- `geometry`: `centroid_x`, `centroid_y`, `area_m2`.
- `terrain`: geometry plus `elevation`, `slope`.
- `sentinel_indices`: geometry plus `NDVI`, `NDBI`, `MNDWI`, `BSI`.
- `sentinel_bands`: geometry plus `B2`, `B3`, `B4`, `B8`, `B11`, `B12`.
- `full_rs_context`: geometry plus all Sentinel and DEM features.
- `pca_context`: geometry plus PCA components explaining at least 95 percent of
  remote-sensing feature variance.

The module should accept both plain names such as `NDVI` and legacy
script-produced `rs_NDVI` names.

### Matching Protocol

For every non-raw variant:

1. Convert listed covariates, treatment, outcome, floor, and coordinates to
   numeric values.
2. Drop rows with missing required values.
3. Standardize covariates before fitting the propensity model.
4. Estimate propensity scores with logistic regression by default.
5. Compute common support as overlap of treated/control propensity ranges.
6. Match treated to control units one-to-one by propensity score.
7. Keep only pairs with absolute propensity distance within
   `caliper * sd(propensity_score)`, default `0.2`.
8. Use replacement for control matches by default because the treated/control
   support can be imbalanced after common-support trimming.
9. Mark balance as passing only when max post-match absolute SMD is below `0.1`.

### Outputs

Required IJGIS review outputs:

- `paper/ijgis_submission_20260605/07_results/chongqing_uhi_ablation.csv`
- `paper/ijgis_submission_20260605/07_results/chongqing_uhi_balance.csv`
- `paper/ijgis_submission_20260605/07_results/chongqing_uhi_matched_counts.csv`
- `paper/ijgis_submission_20260605/07_results/chongqing_spatial_bootstrap.csv`
- `paper/ijgis_submission_20260605/07_results/chongqing_placebo_thresholds.csv`
- `paper/ijgis_submission_20260605/07_results/chongqing_residual_spatial_diagnostics.csv`

Additional helpful outputs:

- `chongqing_uhi_analysis_manifest.json`
- `chongqing_uhi_analysis_report.md`
- `chongqing_uhi_analysis_sample.csv` when the script creates or reuses a
  sampled analysis frame.

### Robustness Interpretation

The analysis report should be conservative:

- `credible_balance`: at least one substantive specification has max post-match
  SMD below `0.1`.
- `bounded_balance`: no row reaches `0.1`, but one or more rows are below `0.25`.
- `failed_balance`: all substantive rows remain above `0.25`.

If balance fails, the report should say the Chongqing case is not yet strong
causal evidence. It can still be used to motivate spatial confounding, but not
as a decisive causal sign-reversal result.

## Testing Strategy

Use TDD.

Minimum tests:

- Feature specs include all required variants and normalize `rs_` prefixed
  feature names.
- Matching standardizes covariates, enforces common support, reports caliper,
  matched counts, and per-covariate SMD.
- The writer creates all required CSV/JSON/Markdown files.
- Threshold placebo outputs include 8, 10, and 12 floors.
- Spatial bootstrap and residual diagnostics return finite, interpretable rows
  on a deterministic fixture.
- `scripts/causal_case_study.py` calls the analysis module rather than keeping
  ad hoc PSM logic.

## Acceptance Criteria

This task is complete when:

- The new module passes focused tests.
- `scripts/causal_case_study.py` delegates all post-extraction analysis to the
  module.
- The required IJGIS output files exist under
  `paper/ijgis_submission_20260605/07_results/`.
- The output manifest records sample size, treatment threshold, caliper,
  bootstrap settings, and balance interpretation.
- If a GEE-authenticated run is unavailable in the current environment, the
  script still produces a clearly labeled smoke/fallback run and the limitation
  is recorded in the manifest/report.
