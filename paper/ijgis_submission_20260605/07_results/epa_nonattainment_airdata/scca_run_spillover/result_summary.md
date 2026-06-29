# epa_nonattainment_airdata Result Summary

## Numeric Summary
- Baseline adjusted OLS estimates the main exposure coefficient at -1.000 (95% CI -1.000 to -1.000, p=<0.001).
- After adding neighboring exposure, the main coefficient is -1.000; the neighbor-exposure coefficient is 5.54e-11 (p=0.364).
- The spatial adjustment changes the main coefficient by 0.0% and sign stability is True.
- Formal SLX output gives direct effect not estimable and indirect effect not estimable (p=not estimable), for total effect not estimable (95% CI not estimable to not estimable, p=not estimable).
- Spatial diagnostics use coordinate_knn with 20740 edges; exposure Moran's I is -0.079 (p=0.010) and residual Moran's I is 0.808 (p=0.010).
- Spatial block bootstrap validates the neighbor-adjusted coefficient with 50 valid replicates: median -1.000, 95% interval -1.000 to -1.000, sign stability 1.000.
- Spatial graph sensitivity across 4 coordinate-kNN specifications gives neighbor-adjusted coefficient range -1.000 to -1.000, with sign stability True.
- Spatial spillover decomposition treats the neighbor-adjusted coefficient as a direct-effect proxy (-1.000) and the neighbor-exposure coefficient as a spillover proxy (5.54e-11); the absolute spillover share is 5.54e-11.
- Exposure mapping based on the fitted spatial model gives mean indirect effect 5.54e-11 and mean total effect -1.000; the indirect effect 10th to 90th percentile range is 1.46e-11 to 1.78e-10.

## Decision
- Credibility decision: weak_or_failed_support
- Robustness interpretation: fragile_support
- Evidence grade: bounded_support
- Evidence grade rules: weak_credibility, fragile_robustness, material_residual_moran

## Spatial Outputs
- GeoPackage/GeoJSON layers include target-exposure fields when target outcomes are configured.
- When spatial exposure mapping is estimable, spatial layers include `gc_spatial_direct_effect`, `gc_spatial_indirect_effect`, `gc_spatial_total_effect`, and graph-weight fields.
- QGIS styles are written under `spatial_outputs/qgis_styles/` when spatial output generation is run.
