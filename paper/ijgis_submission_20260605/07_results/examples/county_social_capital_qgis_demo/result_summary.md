# county_social_capital_qgis_demo Result Summary

## Numeric Summary
- Baseline adjusted OLS estimates the main exposure coefficient at 0.181 (95% CI 0.166 to 0.197, p=<0.001).
- Formal SLX output gives direct effect not estimable and indirect effect not estimable (p=not estimable), for total effect not estimable (95% CI not estimable to not estimable, p=not estimable).
- Spatial diagnostics use unavailable with 0 edges; exposure Moran's I is not estimable (p=not estimable) and residual Moran's I is not estimable (p=not estimable).
- Spatial block bootstrap is not estimable: Spatial blocks could not be constructed..
- Spatial graph sensitivity is not estimable: No coordinates were available for graph sensitivity analysis..
- Spatial spillover decomposition is not estimable.
- Spatial exposure mapping is not estimable.

## Decision
- Credibility decision: strong_support
- Robustness interpretation: robust_support
- Evidence grade: core_support
- Evidence grade rules: none

## Spatial Outputs
- GeoPackage/GeoJSON layers include target-exposure fields when target outcomes are configured.
- When spatial exposure mapping is estimable, spatial layers include `gc_spatial_direct_effect`, `gc_spatial_indirect_effect`, `gc_spatial_total_effect`, and graph-weight fields.
- QGIS styles are written under `spatial_outputs/qgis_styles/` when spatial output generation is run.
