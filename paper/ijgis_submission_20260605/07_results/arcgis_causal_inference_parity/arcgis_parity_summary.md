# ArcGIS Causal Inference Analysis Parity Benchmark

Official ArcGIS baseline: https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-statistics/causal-inference-analysis.htm

## Positioning

SCCA is positioned as an open spatial-diagnostic enhancement layer for GIS causal workflows.
The benchmark does not claim that SCCA reproduces proprietary ArcGIS internals or fully replaces ArcGIS Pro.

## Status Counts

- `gap`: 1
- `matched`: 6
- `partial`: 3
- `scca_only_differentiator`: 1

## County Parity Metrics

- Input rows: 3108
- Included rows after support trimming: 3044
- Baseline adjusted coefficient: 0.181
- Neighbor-adjusted coefficient: 0.146
- Spatial-lag adjusted coefficient: 0.145
- Residual Moran's I: 0.313
- Residual Moran p-value: 0.010
- Spatial files available: True
- Visualization files available: True

## Capability Matrix

| ArcGIS capability | Product meaning | SCCA status | Priority | Evidence | Next action |
|---|---|---:|---:|---|---|
| continuous_exposure_outcome_workflow | Continuous exposure with continuous or binary outcome causal workflow. | matched | P0 | county social-capital notebook and SCCA AnalysisRequest workflow | Keep as the primary ArcGIS-facing commercial parity benchmark. |
| user_declared_confounders | User-selected adjustment variables define the causal design. | matched | P0 | AnalysisRequest.confounders | Expose the same design vocabulary in GIS-facing product docs. |
| ols_or_gradient_boosting_propensity_score | OLS propensity score by default, with gradient boosting fallback. | matched | P0 | OLS/GBM GPS grid search, Open GIS score aliases, and nonlinear balance benchmark | Keep arcgis_gps_balance_benchmark refreshed as GPS method selection changes. |
| propensity_score_matching | Balance observations through propensity-score matching. | partial | P0 | binary case matching modules | Define a continuous-exposure matching output contract. |
| inverse_propensity_score_weighting | Use inverse propensity score weights as a faster balancing method. | partial | P0 | ERF weighting outputs | Write ArcGIS-compatible score and weight aliases to GIS tables. |
| one_to_ninetynine_exposure_trimming | Trim observations outside the 1st and 99th exposure percentiles. | matched | P0 | county workflow retains 3,044 of 3,108 rows | Keep row accounting visible in every generated report. |
| weighted_correlation_balance_threshold | Judge confounder balance with weighted correlation and a threshold. | matched | P0 | Open GIS balance summaries expose mean/median/max absolute weighted-correlation fields | Keep mean/median/max balance fields stable in every Open GIS package. |
| erf_table | Exposure-response function table over exposure support. | matched | P0 | SCCA ERF curve outputs | Add a fixed 200-point ArcGIS parity option if product demos require it. |
| target_exposure_and_target_outcome_fields | What-if outcome and required-exposure fields for target values. | partial | P0 | county target-exposure spatial outputs | Verify and document target-outcome output contract. |
| local_erf_popups | Per-feature local ERF chart interaction in the GIS interface. | gap | P2 | notebook and HTML map alternatives | Defer ArcGIS-native popup parity until after CLI/toolbox MVP. |
| spatial_residual_diagnostics | Spatial diagnostic and evidence-boundary layer beyond the ArcGIS causal workflow. | scca_only_differentiator | P0 | residual Moran's I and evidence-grade downgrade rules | Make this the main product differentiation, not an overclaim of identification. |

## Commercial Interpretation

The county benchmark demonstrates ArcGIS-style row accounting and continuous-exposure output shape, while the residual spatial diagnostics define the evidence boundary. This is the product-facing SCCA value: make GIS causal workflows auditable under spatial dependence rather than presenting an unchecked causal estimate.
