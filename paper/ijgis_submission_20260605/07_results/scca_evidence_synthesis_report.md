# SCCA Evidence Synthesis Report

This report is the evidence boundary for the revised Paper 6 manuscript.
The grade rule version is `scca-evidence-grade-rules-2026-06-30`.
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

### synthetic_core_support_control

- Grade: `core_support`
- Best adjustment: adjusted OLS on the correct measured set
- Effect/diagnostic: ATT_hat = 0.505 (true 0.5); rel. bias = 0.009
- Balance: max post-adjust SMD = 0.092
- Robustness: residual Moran I = -0.011 (p = 0.185); neighbor-exposure p = 0.420
- Grade rules: ``
- Grade reasons: No downgrade rules fire on a clean, well-identified design.
- Limitation: Synthetic positive control only; demonstrates grade discrimination, not real-world validity.
- Manuscript use: Use as the core_support positive control that exercises the grade engine.

### chongqing_uhi

- Grade: `bounded_support`
- Best adjustment: pre_treatment (pre-treatment confounder set)
- Effect/diagnostic: ATT = 0.303 C; 95% CI [0.220, 0.383]; over-adjusted full-RS ATT = 0.244 C; cluster-robust building ATT = 0.268 (CR SE 0.054), pixel-aggregated ATT = 0.546
- Balance: max post-match SMD = 0.104; balance pass = False
- Robustness: threshold placebo, spatial bootstrap, residual spatial, and change-of-support diagnostics available
- Grade rules: `moderate_credibility; material_residual_moran`
- Grade reasons: Credibility diagnostics only support a moderate claim.; Residual spatial autocorrelation is both statistically significant and materially large (Moran's I=0.112, p=0.010).
- Limitation: Outcome retrieved at ~1 km while treatment is building-level (change-of-support), residual spatial structure remains, and Sentinel surfaces may be post-treatment; these bound the causal strength.
- Manuscript use: Use as the main real-data SCCA case; report the pre-treatment estimate with change-of-support and residual-spatial caution.

### county_social_capital_spatial_notebook

- Grade: `bounded_support`
- Best adjustment: SLX-style spatial lag sensitivity over coordinate-kNN graphs
- Effect/diagnostic: baseline coef = 0.181; spatial-lag coef = 0.145; SLX total effect = 0.215
- Balance: matched spatial layer rows = 3044/3108; enriched fields = gc_spatial_direct_effect, gc_spatial_indirect_effect, gc_spatial_total_effect, gc_spatial_out_neighbor_count, gc_spatial_incoming_weight_sum
- Robustness: residual Moran I = 0.313; spatial bootstrap sign stability = 1.000; graph sensitivity sign stable = True
- Grade rules: `material_residual_moran; significant_neighbor_exposure`
- Grade reasons: Residual spatial autocorrelation is both statistically significant and materially large (Moran's I=0.313, p=0.010).; Neighboring exposure remains associated with the outcome after adjustment (p=0.000).
- Limitation: Residual spatial autocorrelation and a significant neighboring-exposure term remain, so this is spatially cautioned external evidence rather than identification evidence.
- Manuscript use: Use as the GIS/notebook spatial-output demonstration and as spatially bounded external SCCA evidence.

## Grade Counts

- `bounded_support`: 3
- `core_support`: 1
