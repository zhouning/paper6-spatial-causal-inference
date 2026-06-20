# SCCA Evidence Grade Rules

- Rule version: `scca-evidence-grade-rules-2026-06-20`

## Grade Meanings

- `core_support`: Strong credibility, robust support, and no material spatial caution under the declared thresholds.
- `bounded_support`: Useful SCCA evidence with explicit credibility, robustness, support, or spatial-diagnostic limits.
- `negative_ablation`: A candidate context source was tested and did not improve the diagnostic design.
- `auxiliary_only`: An output may support interpretation or software development but is not causal evidence for SCCA.

## Thresholds

- `max_balance_corr_moderate`: `0.5`
- `overlap_boundary_mass_moderate`: `0.25`
- `bootstrap_sign_stability_min`: `0.8`
- `erf_monotonic_fraction_min`: `0.8`
- `material_residual_moran_abs`: `0.2`
- `spatial_p_value_max`: `0.05`
- `spatial_adjustment_relative_change_max`: `0.25`

## Downgrade Rules

### `strong_nonspatial_and_robust`

- Scope: core_support gate
- Condition: credibility_decision == strong_support and robustness_interpretation == robust_support
- Effect: Required, but not sufficient, for core_support.

### `moderate_credibility`

- Scope: credibility
- Condition: credibility_decision == moderate_support
- Effect: Downgrade final manuscript evidence to bounded_support.

### `weak_credibility`

- Scope: credibility
- Condition: credibility_decision == weak_or_failed_support
- Effect: Downgrade final manuscript evidence to bounded_support.

### `high_exposure_balance_correlation`

- Scope: credibility
- Condition: max absolute exposure-balance correlation > 0.50
- Effect: Downgrade credibility to moderate_support and final evidence to bounded_support.

### `high_overlap_boundary_mass`

- Scope: credibility
- Condition: exposure boundary mass > 0.25
- Effect: Downgrade credibility to moderate_support and final evidence to bounded_support.

### `bounded_robustness`

- Scope: robustness
- Condition: robustness_interpretation == bounded_support
- Effect: Downgrade final manuscript evidence to bounded_support.

### `fragile_robustness`

- Scope: robustness
- Condition: robustness_interpretation == fragile_support
- Effect: Downgrade final manuscript evidence to bounded_support.

### `material_residual_moran`

- Scope: spatial diagnostics
- Condition: |residual Moran's I| >= 0.20 and permutation p <= 0.05
- Effect: Downgrade final manuscript evidence to bounded_support.

### `significant_neighbor_exposure`

- Scope: spatial diagnostics
- Condition: neighbor-exposure p <= 0.05 after adjustment
- Effect: Downgrade final manuscript evidence to bounded_support.

### `material_spatial_adjustment_shift`

- Scope: spatial diagnostics
- Condition: max relative main-effect change across spatial adjustments >= 0.25
- Effect: Downgrade final manuscript evidence to bounded_support.

### `graph_sign_unstable`

- Scope: spatial diagnostics
- Condition: graph-sensitivity sign stability is false
- Effect: Downgrade final manuscript evidence to bounded_support.
