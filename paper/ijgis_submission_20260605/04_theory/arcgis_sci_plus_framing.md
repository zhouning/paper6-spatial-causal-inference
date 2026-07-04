# ArcGIS Causal Inference Plus Framing

Paper 6 should compare against the ArcGIS Causal Inference Analysis algorithmic tool, not the ArcGIS platform. The tested target is the documented continuous-exposure mode: 1%--99% exposure trimming, REGRESSION propensity scores, MATCHING balance, exposure-bin and propensity/exposure-scale settings, plug-in weighted-kernel ERF smoothing, and target-response lookup.

The revised contribution is:

GeoCausal implements this documented ArcGIS Causal Inference mode for the county social-capital case and validates it against a local ArcGIS Pro 3.7 arcpy run. The open runner matches the 3,044-row trimmed sample, selected 25-bin/0.8 scale setting, 200-point ERF contract, and plug-in bandwidth (2.439 vs ArcGIS 2.4415). The ERF response parity against native arcpy is MAE = 0.015 years and RMSE = 0.044 years. GeoCausal then extends the output with target-support warnings, field-level data provenance, spatial residual risk, neighbor-exposure risk when spatial supports are available, variable-role risk, scale-support risk, and reproducible JSON/CSV/Markdown artifacts.

Recommended manuscript claim:

> For the tested documented continuous-exposure mode, GeoCausal SCI Plus can replace the ArcGIS Causal Inference algorithmic task in open, scriptable workflows while adding spatial causal-risk diagnostics and reproducible audit artifacts. This is not a bit-for-bit claim for untested ArcGIS modes such as gradient boosting, weighting, cross-validated bandwidths, or bootstrap intervals.

Claims to avoid:

- GeoCausal exceeds the full ArcGIS platform.
- SG-SCCA is a universal spatial causal identification theory.
- Residual diagnostics prove the absence of spatial confounding.
- The implementation is bit-for-bit identical for every ArcGIS Causal Inference parameter mode.

Recommended evidence:

- Same 0.01--0.99 exposure trimming rule and 3,044-row county sample.
- Same native ArcGIS selected matching parameters for the direct comparison: 25 bins and scale 0.8.
- Plug-in bandwidth parity: 2.439 open vs 2.4415 arcpy.
- 200-point ERF response parity: MAE 0.015 years, RMSE 0.044 years.
- Additional plus report documenting target-support, spatial, role, scale, and residual bias-bound risks.
