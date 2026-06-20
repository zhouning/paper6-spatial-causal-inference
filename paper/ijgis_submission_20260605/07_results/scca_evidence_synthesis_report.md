# SCCA Evidence Synthesis Report

This report is the evidence boundary for the revised Paper 6 manuscript.
The main paper should use `core_support` and `bounded_support` rows as SCCA evidence,
treat `negative_ablation` rows as boundary findings, and keep `auxiliary_only` rows out of the core claim.

## Evidence Rows

### synthetic_benchmark_audit

- Grade: `bounded_support`
- Best adjustment: multi-seed audit across CausalForest, DiD, ERF, GCCM, Granger, PSM
- Effect/diagnostic: 48 benchmark rows over configured seeds
- Balance: not_applicable
- Robustness: 13/48 robust rows; 29 fragile rows
- Limitation: Stress audit found fragile estimator settings, especially for direction-recovery cases.
- Manuscript use: Use as estimator stress-test evidence, not as real-world causal validation.

### chongqing_uhi

- Grade: `core_support`
- Best adjustment: full_rs_context
- Effect/diagnostic: ATT = 0.244 C; 95% CI [0.148, 0.346]
- Balance: max post-match SMD = 0.061; balance pass = True
- Robustness: threshold placebo, spatial bootstrap, and residual spatial diagnostics available
- Limitation: MODIS LST scale, building-level treatment assignment, and spatial interference limit causal strength.
- Manuscript use: Use as the main real-data SCCA ablation; report the modest positive balanced estimate.

### snow8

- Grade: `bounded_support`
- Best adjustment: SCCA robustness interpretation = bounded_support
- Effect/diagnostic: main coefficient = 83.172
- Balance: ablation direction stable = True; placebo weaker = True
- Robustness: bootstrap sign stability = 0.985; ERF direction = increasing
- Limitation: Maximum exposure-balance correlation is high (0.828).
- Manuscript use: Use as a bounded historical SCCA replication case.

### soho

- Grade: `bounded_support`
- Best adjustment: SCCA robustness interpretation = bounded_support
- Effect/diagnostic: main coefficient = 1.087
- Balance: ablation direction stable = True; placebo weaker = True
- Robustness: bootstrap sign stability = 1.000; ERF direction = increasing
- Limitation: Maximum exposure-balance correlation is high (0.543).
- Manuscript use: Use as a bounded mechanism-focused SCCA case.

### county_social_capital

- Grade: `core_support`
- Best adjustment: SCCA robustness interpretation = robust_support
- Effect/diagnostic: main coefficient = 0.147
- Balance: ablation direction stable = True; placebo weaker = True
- Robustness: bootstrap sign stability = 1.000; ERF direction = increasing
- Limitation: No credibility downgrade warnings were triggered.
- Manuscript use: Use as the strongest external SCCA validation row.

### geofm_alphaearth_ablation

- Grade: `negative_ablation`
- Best adjustment: geometry_rs_context outperformed AlphaEarth variants on balance
- Effect/diagnostic: observed RS SMD 0.061; best AlphaEarth variant geometry_alphaearth_pca SMD 0.268
- Balance: claim guidance = geofm_no_clear_gain
- Robustness: negative ablation under the current Chongqing sampling design
- Limitation: Only 199 complete AlphaEarth rows were available in this run, so the result is a bounded negative diagnostic.
- Manuscript use: Use to state that GeoFM is a candidate context source with no clear gain in the current evidence.

### llm_dag_validation

- Grade: `auxiliary_only`
- Best adjustment: not an SCCA adjustment source
- Effect/diagnostic: mean F1 = 0.666
- Balance: not_applicable
- Robustness: offline proxy only
- Limitation: Does not identify treatment effects or validate SCCA adjustment sets.
- Manuscript use: Exclude from core evidence; mention only as optional interpretive tooling if needed.

### world_model_holdout_validation

- Grade: `auxiliary_only`
- Best adjustment: not an SCCA adjustment source
- Effect/diagnostic: horizon-1 RMSE persistence 0.067, world model 0.080
- Balance: not_applicable
- Robustness: persistence baseline beat world-model baseline in the offline fixture
- Limitation: Scenario simulation only; no real held-out causal validation.
- Manuscript use: Exclude from core SCCA evidence; use only to bound future simulation claims.

## Grade Counts

- `auxiliary_only`: 2
- `bounded_support`: 3
- `core_support`: 2
- `negative_ablation`: 1
