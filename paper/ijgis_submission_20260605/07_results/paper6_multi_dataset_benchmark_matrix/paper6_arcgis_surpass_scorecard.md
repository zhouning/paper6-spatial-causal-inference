# Paper 6 ArcGIS Surpass Scorecard

This scorecard converts the benchmark matrix into explicit gates for judging ArcGIS replacement and superiority claims.

- Overall status: `not_yet_claimable`
- Blocking gates: `3`
- Surpassing gates: `2`
- Near-parity gates: `1`
- Known-truth passes: `1`

## Blocking Gates

- `county_arcgis_style_calibrated_erf`: `open_gap` - Use calibrated ERF as the preferred ArcGIS-compatible Open GIS curve when it improves parity.
- `county_default_erf_gap`: `open_gap` - Tune the default ERF smoother/bandwidth or promote the open ArcGIS-style ERF as the default benchmark mode.
- `synthetic_fragility`: `open_gap` - Prioritize fragile synthetic scenarios before claiming robust algorithmic superiority.

## Scorecard

| criterion_id                          | category                     | status              |   metric_value |   arcgis_reference | threshold                                                     | evidence_case              | interpretation                                                                                   | next_action                                                                                                 |
|:--------------------------------------|:-----------------------------|:--------------------|---------------:|-------------------:|:--------------------------------------------------------------|:---------------------------|:-------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------|
| county_calibrated_balance             | direct_arcgis_metric         | surpasses_arcgis    |    0.0452788   |             0.0559 | lower than ArcGIS weighted correlation                        | county_arcgis_builtin      | GeoCausal calibrated ArcGIS-style weights beat the ArcGIS balance score on the county benchmark. | Replicate the calibrated-balance win on additional real ArcGIS comparisons.                                 |
| county_arcgis_style_erf               | direct_arcgis_metric         | near_parity         |    0.0428985   |           nan      | MAE <= 0.05                                                   | county_arcgis_builtin      | ArcGIS-style open ERF closely reproduces the ArcGIS ERF curve.                                   | Keep this as parity benchmark output while improving the default GeoCausal ERF.                             |
| county_arcgis_style_calibrated_erf    | direct_arcgis_metric         | open_gap            |    0.149091    |           nan      | MAE <= 0.05                                                   | county_arcgis_builtin      | Calibrated ArcGIS-style ERF is not yet close enough to the ArcGIS reference.                     | Use calibrated ERF as the preferred ArcGIS-compatible Open GIS curve when it improves parity.               |
| county_default_erf_gap                | direct_arcgis_metric         | open_gap            |    1.27364     |           nan      | MAE <= 0.25                                                   | county_arcgis_builtin      | Default GeoCausal ERF is still numerically far from the ArcGIS ERF reference.                    | Tune the default ERF smoother/bandwidth or promote the open ArcGIS-style ERF as the default benchmark mode. |
| direct_arcgis_real_dataset_coverage   | evidence_coverage            | sufficient_evidence |    3           |           nan      | 3                                                             | all_arcgis_available_rows  | Direct ArcGIS comparisons cover enough real datasets for a stronger claim.                       | Add additional real ArcGIS comparisons before claiming broad superiority.                                   |
| direct_arcgis_calibrated_balance_wins | direct_arcgis_metric         | surpasses_arcgis    |    3           |             3      | GeoCausal calibrated balance lower on every direct ArcGIS row | all_arcgis_available_rows  | GeoCausal calibrated balance beats ArcGIS on every direct ArcGIS comparison row.                 | Keep adding real ArcGIS comparisons and preserve the calibrated-balance win rate.                           |
| synthetic_fragility                   | known_truth_robustness       | open_gap            |   29           |           nan      | 0                                                             | synthetic_known_truth_rows | Synthetic known-truth audit still contains fragile method/scenario rows.                         | Prioritize fragile synthetic scenarios before claiming robust algorithmic superiority.                      |
| epa_known_truth_recovery              | policy_structure_known_truth | passes_known_truth  |    4.38336e-11 |           nan      | 1e-06                                                         | epa_nonattainment_airdata  | GeoCausal recovers the known EPA policy-structure semi-synthetic effect within tolerance.        | Replace the deterministic outcome with direct AQS AirData observational estimates when available.           |
| overall_arcgis_surpass_readiness      | overall_gate                 | not_yet_claimable   |    3           |           nan      | 0                                                             | all_scorecard_rows         | Evidence supports partial wins, but not a broad ArcGIS-superiority claim yet.                    | Add additional real ArcGIS comparisons and close open synthetic/default-ERF gaps.                           |
