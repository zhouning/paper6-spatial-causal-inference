# SCCA Analysis Report

## Study

- Name: `county_social_capital_example`
- Exposure: `SocialAssoc`
- Outcome: `AveAgeDeath`
- Baseline outcome: `None`

## Result Summary

- Baseline adjusted OLS estimates the main exposure coefficient at 0.181 (95% CI 0.166 to 0.197, p=<0.001).
- Formal SLX output gives direct effect not estimable and indirect effect not estimable (p=not estimable), for total effect not estimable (95% CI not estimable to not estimable, p=not estimable).
- Spatial diagnostics use unavailable with 0 edges; exposure Moran's I is not estimable (p=not estimable) and residual Moran's I is not estimable (p=not estimable).
- Spatial block bootstrap is not estimable: Spatial blocks could not be constructed..
- Spatial graph sensitivity is not estimable: No coordinates were available for graph sensitivity analysis..
- Spatial spillover decomposition is not estimable.
- Spatial exposure mapping is not estimable.

## Credibility Decision

`strong_support`

## Evidence Grade

`core_support`

## Reasons

- No credibility downgrade warnings were triggered.

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
