# SCCA Robustness Report

## Case

`snow8`

## Interpretation

`bounded_support`

## Main Result

- Original decision: `moderate_support`
- Main coefficient: `83.17184030435816`
- Main limitation: Maximum exposure-balance correlation is high (0.828).

## Robustness Checks

- Ablation direction stable: `True`
- Placebo weaker than main: `True`
- Bootstrap sign stability: `0.985`
- ERF monotonic direction: `increasing`

## Reasons

- Ablation, placebo, bootstrap, and ERF checks support the current interpretation.
