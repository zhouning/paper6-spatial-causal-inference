# SCCA Robustness Report

## Case

`epa_nonattainment_airdata`

## Interpretation

`bounded_support`

## Main Result

- Original decision: `weak_or_failed_support`
- Main coefficient: `-0.999999999972544`
- Main limitation: Exposure boundary mass is high (0.512).; Maximum exposure-balance correlation is high (0.915).; Leave-one-subgroup-out spatial robustness is not estimable.; Core estimator status is unstable: baseline_adjusted_ols, difference_outcome_ols.; Residual spatial autocorrelation detected (Moran's I=0.816, p=0.010).

## Robustness Checks

- Ablation direction stable: `True`
- Placebo weaker than main: `True`
- Bootstrap sign stability: `1.0`
- ERF monotonic direction: `decreasing`

## Reasons

- Ablation, placebo, bootstrap, and ERF checks support the current interpretation.
