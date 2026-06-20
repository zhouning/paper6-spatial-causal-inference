# SCCA Evidence Synthesis Report

This report is the evidence boundary for the revised Paper 6 manuscript.
The grade rule version is `scca-evidence-grade-rules-2026-06-20`.
The main paper should use `core_support` and `bounded_support` rows as SCCA evidence,
treat `negative_ablation` rows as boundary findings, and keep `auxiliary_only` rows out of the core claim.

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

### snow8

- Grade: `bounded_support`
- Best adjustment: SCCA robustness interpretation = bounded_support
- Effect/diagnostic: main coefficient = 83.172
- Balance: ablation direction stable = True; placebo weaker = True
- Robustness: bootstrap sign stability = 0.985; ERF direction = increasing
- Grade rules: `moderate_credibility; high_exposure_balance_correlation; bounded_robustness`
- Grade reasons: Credibility diagnostics only support a moderate claim.; Maximum exposure-balance correlation exceeds the threshold (0.828 > 0.50).; Robustness checks support only a bounded interpretation.
- Limitation: Maximum exposure-balance correlation is high (0.828).
- Manuscript use: Use as a bounded historical SCCA replication case.

### soho

- Grade: `bounded_support`
- Best adjustment: SCCA robustness interpretation = bounded_support
- Effect/diagnostic: main coefficient = 1.087
- Balance: ablation direction stable = True; placebo weaker = True
- Robustness: bootstrap sign stability = 1.000; ERF direction = increasing
- Grade rules: `moderate_credibility; high_exposure_balance_correlation; bounded_robustness`
- Grade reasons: Credibility diagnostics only support a moderate claim.; Maximum exposure-balance correlation exceeds the threshold (0.543 > 0.50).; Robustness checks support only a bounded interpretation.
- Limitation: Maximum exposure-balance correlation is high (0.543).
- Manuscript use: Use as a bounded mechanism-focused SCCA case.

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

### geofm_alphaearth_ablation

- Grade: `negative_ablation`
- Best adjustment: geometry_rs_context outperformed AlphaEarth variants on balance
- Effect/diagnostic: observed RS SMD 0.061; best AlphaEarth variant geometry_alphaearth_pca SMD 0.268
- Balance: claim guidance = geofm_no_clear_gain
- Robustness: negative ablation under the current Chongqing sampling design
- Grade rules: `negative_ablation`
- Grade reasons: AlphaEarth embedding variants did not improve balance in the current run.
- Limitation: Only 199 complete AlphaEarth rows were available in this run, so the result is a bounded negative diagnostic.
- Manuscript use: Use to state that GeoFM is a candidate context source with no clear gain in the current evidence.

### llm_dag_validation

- Grade: `auxiliary_only`
- Best adjustment: not an SCCA adjustment source
- Effect/diagnostic: mean F1 = 0.666
- Balance: not_applicable
- Robustness: offline proxy only
- Grade rules: `auxiliary_only`
- Grade reasons: Offline DAG validation does not estimate treatment effects.
- Limitation: Does not identify treatment effects or validate SCCA adjustment sets.
- Manuscript use: Exclude from core evidence; mention only as optional interpretive tooling if needed.

### world_model_holdout_validation

- Grade: `auxiliary_only`
- Best adjustment: not an SCCA adjustment source
- Effect/diagnostic: horizon-1 RMSE persistence 0.067, world model 0.080
- Balance: not_applicable
- Robustness: persistence baseline beat world-model baseline in the offline fixture
- Grade rules: `auxiliary_only`
- Grade reasons: Scenario simulation is not identified treatment-effect evidence.
- Limitation: Scenario simulation only; no real held-out causal validation.
- Manuscript use: Exclude from core SCCA evidence; use only to bound future simulation claims.

## Grade Counts

- `auxiliary_only`: 2
- `bounded_support`: 4
- `core_support`: 1
- `negative_ablation`: 1
