# ArcGIS GPS Balance Upgrade Design

## Goal

Improve Paper 6's ArcGIS-replacement evidence by making the Open GIS causal workflow expose an explicit OLS-vs-gradient-boosting generalized propensity score route, ArcGIS-compatible balance summary fields, and a deterministic nonlinear synthetic benchmark that verifies when the gradient-boosting GPS is the better balancing model.

## Scope

This upgrade stays inside the current `open-gis-parity-package` PR branch. It does not create a new branch and does not touch the main checkout's uncommitted ArcGIS toolbox metadata.

In scope:

- Add explicit GPS method metadata to `geocausal.arcgis_style_matching`.
- Support OLS and gradient-boosting GPS fits for ArcGIS-style continuous-exposure matching.
- Let the grid search evaluate both methods and select the method with the lowest absolute weighted-correlation objective.
- Add ArcGIS-compatible aliases and aggregate balance fields to Open GIS outputs.
- Add a synthetic nonlinear benchmark and tests showing the selected GBM GPS improves balance over an OLS-only route.
- Update ArcGIS parity documentation and generated parity matrix wording.

Out of scope:

- New UI work or ArcGIS-native popup parity.
- New remote branches.
- Replacing the existing SCCA estimator family.
- Propensity-score trimming controls; this remains a follow-on item.

## Architecture

The existing `geocausal.arcgis_style_matching` module remains the single home for ArcGIS-style continuous-exposure matching. The current OLS GPS fit is kept as the baseline method. A new GBM GPS fit uses `sklearn.ensemble.GradientBoostingRegressor` on min-max scaled exposure and covariates, then estimates the observed conditional density from residual normal density. Both methods return the same `_GPSFit` interface, so matching count weights and balance scoring remain shared.

`arcgis_style_matching_search` gains a `gps_methods` argument. Its default evaluates both `ols` and `gbm`, records `gps_method` in the candidate grid, and returns the selected method in `ArcGISStyleMatchingResult`. Existing callers can force OLS-only behavior with `gps_methods=("ols",)`.

`geocausal.open_gis` uses the selected method to add ArcGIS-facing fields in `analysis_joined.csv` and aggregate balance fields in the run summary and balance CSVs. The field names are deliberately explicit:

- `gc_arcgis_propensity_score`
- `gc_arcgis_matching_weight`
- `gc_arcgis_calibrated_weight`
- `gc_arcgis_gps_method`
- `arcgis_mean_abs_weighted_correlation`
- `arcgis_median_abs_weighted_correlation`
- `arcgis_max_abs_weighted_correlation`
- `arcgis_balanced_at_0_1`

## Data Flow

1. `write_open_gis_package` calls `arcgis_style_matching_search`.
2. The search builds complete numeric rows for exposure plus confounders.
3. Each requested GPS method fits a `_GPSFit`.
4. For each method, bin count, and scale candidate, matching count weights are computed.
5. Balance is scored with absolute weighted Spearman correlation.
6. The lowest mean absolute correlation candidate is selected.
7. Open GIS output tables receive the selected propensity scores, weights, method name, and aggregate balance metrics.
8. A synthetic nonlinear benchmark runs OLS-only and GBM-only searches, then writes a compact CSV/JSON evidence artifact.

## Error Handling

If a method cannot fit, the search records a warning and continues with other methods. If no method fits, the existing empty result behavior remains: unit weights, NaN propensity scores, empty balance summaries, and warnings in the run summary.

Aggregate balance fields use `None` in JSON and `NaN` in CSV when no finite correlation is available.

## Testing

Tests should prove behavior at three levels:

- `arcgis_style_matching_search` includes method metadata, can force OLS or GBM, and selects GBM on a nonlinear fixture.
- `write_open_gis_package` writes ArcGIS aliases and aggregate balance fields.
- The synthetic benchmark writes OLS-vs-GBM comparison artifacts and records a GBM balance win.

Regression tests must preserve existing Open GIS package outputs and ArcGIS-style ERF behavior.

## Success Criteria

- New tests fail before implementation and pass after implementation.
- Existing pipeline and ArcGIS parity tests continue to pass.
- `git diff --check` is clean.
- The active PR branch is pushed with the implementation and documentation.
