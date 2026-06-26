# SCCA Evidence Synthesis Report

This report is the evidence boundary for the revised Paper 6 manuscript.
The grade rule version is `scca-evidence-grade-rules-2026-06-20`.
The main paper should use the Chongqing row as the main empirical case,
the synthetic row as estimator stress-test evidence,
and the county row as a GIS/notebook reproducibility and spatial-diagnostic boundary check.

## Evidence Rows

### synthetic_benchmark_audit

- Grade: `bounded_support`
- Best adjustment: multi-seed audit across CausalForest, DiD, ERF, GCCM, Granger, PSM
- Effect/diagnostic: 48 benchmark rows over configured seeds
- Balance: not_applicable
- Robustness: 13/48 robust rows; 29 fragile rows
- Grade rules: `synthetic_fragility`
- Grade reasons: At least one controlled scenario produced fragile estimator behavior.
- Limitation: Stress audit found fragile estimator settings, especially for direction-recovery cases.
- Manuscript use: Use as estimator stress-test evidence, not as real-world causal validation.

### chongqing_uhi

- Grade: `core_support`
- Best adjustment: full_rs_context
- Effect/diagnostic: ATT = 0.244 C; 95% CI [0.148, 0.346]
- Balance: max post-match SMD = 0.061; balance pass = True
- Robustness: threshold placebo, spatial bootstrap, and residual spatial diagnostics available
- Grade rules: ``
- Grade reasons: No downgrade rules triggered.
- Limitation: MODIS LST scale, building-level treatment assignment, and spatial interference limit causal strength.
- Manuscript use: Use as the main real-data SCCA ablation; report the modest positive balanced estimate.

### epa_nonattainment_airdata

- Grade: `bounded_support`
- Best adjustment: GeoCausal SCCA annual county-year panel with semi-synthetic known-effect checks
- Effect/diagnostic: policy-structure semi-synthetic coefficient = -1.000; semi-synthetic median absolute error = 0.000
- Balance: 4880 county-year rows, 2005-2024
- Robustness: 3 semi-synthetic scenarios; spatial caution scenarios = spatial_confounding, spillover, stable_known_effect
- Grade rules: `weak_credibility; bounded_robustness; material_residual_moran`
- Grade reasons: Credibility diagnostics indicate weak or failed support.; Robustness checks support only a bounded interpretation.; Residual spatial autocorrelation is both statistically significant and materially large (Moran's I=0.876, p=0.010).
- Limitation: This run uses a deterministic known-effect outcome on real EPA policy geography; it is not an observational causal policy estimate until AQS AirData acquisition succeeds.
- Manuscript use: Use as a public spatiotemporal benchmark; rely on the semi-synthetic known-effect layer for validation, while treating observational AirData validation as pending.

### county_social_capital_spatial_notebook

- Grade: `bounded_support`
- Best adjustment: SLX-style spatial lag sensitivity over coordinate-kNN graphs
- Effect/diagnostic: baseline coef = 0.181; spatial-lag coef = 0.145; SLX total effect = 0.215
- Balance: matched spatial layer rows = 3044/3108; enriched fields = gc_spatial_direct_effect, gc_spatial_indirect_effect, gc_spatial_total_effect, gc_spatial_out_neighbor_count, gc_spatial_incoming_weight_sum
- Robustness: residual Moran I = 0.313; spatial bootstrap sign stability = 1.000; graph sensitivity sign stable = True
- Grade rules: `material_residual_moran; significant_neighbor_exposure`
- Grade reasons: Residual spatial autocorrelation is both statistically significant and materially large (Moran's I=0.313, p=0.010).; Neighboring exposure remains associated with the outcome after adjustment (p=0.000).
- Limitation: Residual spatial autocorrelation and a significant neighboring-exposure term remain, so this is spatially cautioned external evidence rather than definitive identification.
- Manuscript use: Use as the GIS/notebook spatial-output demonstration and as spatially bounded external SCCA evidence.

## Grade Counts

- `bounded_support`: 3
- `core_support`: 1
