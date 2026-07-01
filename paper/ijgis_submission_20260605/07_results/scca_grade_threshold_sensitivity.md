# SCCA Residual Moran Threshold Sensitivity

This report varies only `material_residual_moran_abs`; all other grade rules remain unchanged.

| Case | Residual Moran I | p-value | Threshold | Grade | Residual status | Grade rules | Flags |
|---|---:|---:|---:|---|---|---|---|
| chongqing_full_rs_context | 0.102 | 0.010 | 0.10 | bounded_support | material_significant | material_residual_moran | none |
| chongqing_full_rs_context | 0.102 | 0.010 | 0.15 | core_support | significant_below_material_threshold | none | significant_residual_moran_below_material_threshold |
| chongqing_full_rs_context | 0.102 | 0.010 | 0.20 | core_support | significant_below_material_threshold | none | significant_residual_moran_below_material_threshold |
| county_social_capital_spatial_notebook | 0.313 | 0.010 | 0.10 | bounded_support | material_significant | material_residual_moran; significant_neighbor_exposure | none |
| county_social_capital_spatial_notebook | 0.313 | 0.010 | 0.15 | bounded_support | material_significant | material_residual_moran; significant_neighbor_exposure | none |
| county_social_capital_spatial_notebook | 0.313 | 0.010 | 0.20 | bounded_support | material_significant | material_residual_moran; significant_neighbor_exposure | none |
