# Synthetic Benchmark Audit

This report summarizes which Paper 6 synthetic estimators remained robust under stress and which combinations were fragile.

## Scenario Summary

- `CausalForest`: robust=2, bounded=2, fragile=0, preferred=`standard`/bounded, preferred_fragile=0, diagnostic_fragile=0, score_range=[0.90, 0.99]
- `DiD`: robust=3, bounded=1, fragile=0, preferred=`standard`/bounded, preferred_fragile=0, diagnostic_fragile=0, score_range=[0.78, 0.98]
- `ERF`: robust=2, bounded=2, fragile=0, preferred=`standard`/bounded, preferred_fragile=0, diagnostic_fragile=0, score_range=[0.84, 0.90]
- `GCCM`: robust=0, bounded=0, fragile=12, preferred=`queen`/fragile, preferred_fragile=4, diagnostic_fragile=8, score_range=[0.07, 0.40]
- `Granger`: robust=2, bounded=1, fragile=1, preferred=`standard`/fragile, preferred_fragile=1, diagnostic_fragile=0, score_range=[0.17, 0.87]
- `PSM`: robust=4, bounded=0, fragile=16, preferred=`ols_adjusted`/robust, preferred_fragile=0, diagnostic_fragile=16, score_range=[0.12, 0.98]

## Most Fragile Rows

- `GCCM` / `baseline` / `knn_k2`: fragile; direction_accuracy=0.07 fell below 0.50; estimate_mean=0.06667, rmse=0.9661
- `GCCM` / `small_sample` / `knn_k2`: fragile; direction_accuracy=0.10 fell below 0.50; estimate_mean=0.1, rmse=0.9487
- `PSM` / `severe_stress` / `standard`: fragile; normalized_rmse=1.228 exceeded 0.40; estimate_mean=8253, rmse=1.842e+04
- `PSM` / `severe_stress` / `kernel`: fragile; normalized_rmse=1.228 exceeded 0.40; estimate_mean=8253, rmse=1.842e+04
- `PSM` / `severe_stress` / `caliper`: fragile; normalized_rmse=1.086 exceeded 0.40; estimate_mean=3185, rmse=1.629e+04
- `Granger` / `severe_stress` / `standard`: fragile; direction_accuracy=0.17 fell below 0.50; estimate_mean=0.1667, rmse=0.9129
- `GCCM` / `severe_stress` / `knn_k2`: fragile; direction_accuracy=0.20 fell below 0.50; estimate_mean=0.2, rmse=0.8944
- `GCCM` / `small_sample` / `standard`: fragile; direction_accuracy=0.23 fell below 0.50; estimate_mean=0.2333, rmse=0.8756

## Strongest Rows

- `CausalForest` / `baseline` / `standard`: robust; normalized_rmse=0.018 stayed within 0.15; estimate_mean=99.8, rmse=1.841
- `PSM` / `baseline` / `ols_adjusted`: robust; normalized_rmse=0.027 stayed within 0.15; estimate_mean=1.501e+04, rmse=411.9
- `DiD` / `baseline` / `standard`: robust; normalized_rmse=0.026 stayed within 0.15; estimate_mean=-8.045, rmse=0.2066
- `CausalForest` / `small_sample` / `standard`: robust; normalized_rmse=0.032 stayed within 0.15; estimate_mean=100.7, rmse=3.218
- `DiD` / `noisy_outcome` / `standard`: robust; normalized_rmse=0.035 stayed within 0.15; estimate_mean=-8.062, rmse=0.2801
- `PSM` / `noisy_outcome` / `ols_adjusted`: robust; normalized_rmse=0.048 stayed within 0.15; estimate_mean=1.502e+04, rmse=720.7
- `CausalForest` / `noisy_outcome` / `standard`: bounded; normalized_rmse=0.037 stayed within 0.40; estimate_mean=99.35, rmse=3.72
- `PSM` / `small_sample` / `ols_adjusted`: robust; normalized_rmse=0.057 stayed within 0.15; estimate_mean=1.467e+04, rmse=854.6

## PSM Notes

- Weakest audited row: `severe_stress` / `standard` with fragile (normalized_rmse=1.228 exceeded 0.40).
- Strongest audited row: `baseline` / `ols_adjusted` with robust (normalized_rmse=0.027 stayed within 0.15).

## GCCM Notes

- Weakest audited row: `baseline` / `knn_k2` with fragile (direction_accuracy=0.07 fell below 0.50).
- Strongest audited row: `noisy_outcome` / `queen` with fragile (direction_accuracy=0.40 fell below 0.50).
