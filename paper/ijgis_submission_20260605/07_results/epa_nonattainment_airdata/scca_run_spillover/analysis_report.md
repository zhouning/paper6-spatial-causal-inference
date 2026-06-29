# SCCA Analysis Report

## Study

- Name: `epa_nonattainment_airdata`
- Exposure: `nonattainment_lag1`
- Outcome: `annual_mean`
- Baseline outcome: `baseline_annual_mean`

## Result Summary

- Baseline adjusted OLS estimates the main exposure coefficient at -1.000 (95% CI -1.000 to -1.000, p=<0.001).
- After adding neighboring exposure, the main coefficient is -1.000; the neighbor-exposure coefficient is 5.54e-11 (p=0.364).
- The spatial adjustment changes the main coefficient by 0.0% and sign stability is True.
- Formal SLX output gives direct effect not estimable and indirect effect not estimable (p=not estimable), for total effect not estimable (95% CI not estimable to not estimable, p=not estimable).
- Spatial diagnostics use coordinate_knn with 20740 edges; exposure Moran's I is -0.079 (p=0.010) and residual Moran's I is 0.808 (p=0.010).
- Spatial block bootstrap validates the neighbor-adjusted coefficient with 50 valid replicates: median -1.000, 95% interval -1.000 to -1.000, sign stability 1.000.
- Spatial graph sensitivity across 4 coordinate-kNN specifications gives neighbor-adjusted coefficient range -1.000 to -1.000, with sign stability True.
- Spatial spillover decomposition treats the neighbor-adjusted coefficient as a direct-effect proxy (-1.000) and the neighbor-exposure coefficient as a spillover proxy (5.54e-11); the absolute spillover share is 5.54e-11.
- Exposure mapping based on the fitted spatial model gives mean indirect effect 5.54e-11 and mean total effect -1.000; the indirect effect 10th to 90th percentile range is 1.46e-11 to 1.78e-10.

## Credibility Decision

`weak_or_failed_support`

## Evidence Grade

`bounded_support`

## Reasons

- Exposure boundary mass is high (0.512).
- Maximum exposure-balance correlation is high (0.915).
- Leave-one-subgroup-out spatial robustness is not estimable.
- Core estimator status is unstable: baseline_adjusted_ols, difference_outcome_ols.
- Residual spatial autocorrelation detected (Moran's I=0.808, p=0.010).

## Output Files

- Data Profile: `data_profile.json`
- Variable Candidates: `variable_candidates.csv`
- Context Features: `context_features.csv`
- Context Manifest: `context_feature_manifest.json`
- Design Plan: `design_plan.json`
- Effect Estimates: `effect_estimates.csv`
- Erf Curve: `erf_curve.csv`
- Model Diagnostics: `model_diagnostics.json`
- Balance Summary: `balance_summary.csv`
- Overlap Summary: `overlap_summary.json`
- Spatial Robustness: `spatial_robustness.csv`
- Credibility Report: `credibility_report.json`
- Analysis Report: `analysis_report.md`
- Manifest: `manifest.json`
- Spatial Diagnostics: `spatial_diagnostics.json`
- Spatial Bootstrap Robustness: `spatial_bootstrap_robustness.csv`
- Spatial Bootstrap Summary: `spatial_bootstrap_summary.json`
- Spatial Graph Sensitivity: `spatial_graph_sensitivity.csv`
- Spatial Graph Sensitivity Summary: `spatial_graph_sensitivity_summary.json`
- Spatial Slx Estimates: `spatial_slx_estimates.csv`
- Spatial Slx Summary: `spatial_slx_summary.json`
- Spatial Spillover Decomposition: `spatial_spillover_decomposition.csv`
- Spatial Spillover Summary: `spatial_spillover_summary.json`
- Spatial Exposure Mapping: `spatial_exposure_mapping.csv`
- Spatial Exposure Mapping Summary: `spatial_exposure_mapping_summary.json`
