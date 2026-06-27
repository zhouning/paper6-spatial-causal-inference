# Synthetic Benchmark Audit

This report summarizes which Paper 6 synthetic estimators remained robust under stress and which combinations were fragile.

## Scenario Summary

- `CausalForest`: robust=2, bounded=2, fragile=0, preferred=`standard`/bounded, preferred_fragile=0, diagnostic_fragile=0, score_range=[0.90, 0.99]
- `DiD`: robust=3, bounded=1, fragile=0, preferred=`standard`/bounded, preferred_fragile=0, diagnostic_fragile=0, score_range=[0.78, 0.98]
- `ERF`: robust=2, bounded=2, fragile=0, preferred=`standard`/bounded, preferred_fragile=0, diagnostic_fragile=0, score_range=[0.84, 0.90]
- `GCCM`: robust=11, bounded=1, fragile=0, preferred=`standard`/robust, preferred_fragile=0, diagnostic_fragile=0, score_range=[0.83, 1.00]
- `Granger`: robust=2, bounded=1, fragile=1, preferred=`standard`/fragile, preferred_fragile=1, diagnostic_fragile=0, score_range=[0.17, 0.87]
- `PSM`: robust=4, bounded=0, fragile=16, preferred=`ols_adjusted`/robust, preferred_fragile=0, diagnostic_fragile=16, score_range=[0.12, 0.98]

## Most Fragile Rows

- `PSM` / `severe_stress` / `standard`: fragile; normalized_rmse=1.228 exceeded 0.40; estimate_mean=8253, rmse=1.842e+04
- `PSM` / `severe_stress` / `kernel`: fragile; normalized_rmse=1.228 exceeded 0.40; estimate_mean=8253, rmse=1.842e+04
- `PSM` / `severe_stress` / `caliper`: fragile; normalized_rmse=1.086 exceeded 0.40; estimate_mean=3185, rmse=1.629e+04
- `Granger` / `severe_stress` / `standard`: fragile; direction_accuracy=0.17 fell below 0.50; estimate_mean=0.1667, rmse=0.9129
- `PSM` / `small_sample` / `caliper`: fragile; normalized_rmse=0.824 exceeded 0.40; estimate_mean=3614, rmse=1.237e+04
- `PSM` / `small_sample` / `kernel`: fragile; normalized_rmse=0.742 exceeded 0.40; estimate_mean=5439, rmse=1.113e+04
- `PSM` / `small_sample` / `standard`: fragile; normalized_rmse=0.742 exceeded 0.40; estimate_mean=5439, rmse=1.113e+04
- `PSM` / `severe_stress` / `naive_difference`: fragile; normalized_rmse=0.689 exceeded 0.40; estimate_mean=2.483e+04, rmse=1.033e+04

## Strongest Rows

- `GCCM` / `baseline` / `knn_k2`: robust; direction_accuracy=1.00 met robust threshold; estimate_mean=1, rmse=0
- `GCCM` / `baseline` / `standard`: robust; direction_accuracy=1.00 met robust threshold; estimate_mean=1, rmse=0
- `GCCM` / `severe_stress` / `queen`: robust; direction_accuracy=1.00 met robust threshold; estimate_mean=1, rmse=0
- `GCCM` / `noisy_outcome` / `standard`: robust; direction_accuracy=1.00 met robust threshold; estimate_mean=1, rmse=0
- `GCCM` / `small_sample` / `standard`: robust; direction_accuracy=1.00 met robust threshold; estimate_mean=1, rmse=0
- `CausalForest` / `baseline` / `standard`: robust; normalized_rmse=0.018 stayed within 0.15; estimate_mean=99.8, rmse=1.841
- `PSM` / `baseline` / `ols_adjusted`: robust; normalized_rmse=0.027 stayed within 0.15; estimate_mean=1.501e+04, rmse=411.9
- `DiD` / `baseline` / `standard`: robust; normalized_rmse=0.026 stayed within 0.15; estimate_mean=-8.045, rmse=0.2066

## PSM Notes

- Weakest audited row: `severe_stress` / `standard` with fragile (normalized_rmse=1.228 exceeded 0.40).
- Strongest audited row: `baseline` / `ols_adjusted` with robust (normalized_rmse=0.027 stayed within 0.15).

## GCCM Notes

- Weakest audited row: `small_sample` / `knn_k2` with bounded (direction_accuracy=0.83 was mixed).
- Strongest audited row: `small_sample` / `standard` with robust (direction_accuracy=1.00 met robust threshold).
