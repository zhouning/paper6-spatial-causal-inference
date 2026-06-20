# SCCA Method Comparison Report

- Grade rule version: `scca-evidence-grade-rules-2026-06-20`

This report directly compares simpler baselines with SCCA-enhanced analyses.

## county_nonspatial_vs_spatial

- Baseline: non-spatial adjusted OLS and grouped robustness
- SCCA-enhanced: SCCA spatial lag, residual Moran, graph sensitivity
- Effect change: 0.1812446003915234 -> 0.1445547494456812 (relative delta -0.2024327945030364)
- Grade change: `core_support` -> `bounded_support`
- Enhanced rule ids: `material_residual_moran; significant_neighbor_exposure`
- Interpretation: Spatial diagnostics preserve the positive direction but downgrade the county case from non-spatial core support to bounded support because residual spatial structure and neighboring exposure remain visible.

## chongqing_raw_vs_full_scca

- Baseline: raw treated-control difference
- SCCA-enhanced: full remote-sensing, terrain, and geometry SCCA matching
- Effect change: 0.2377372285714258 -> 0.2441250110161267 (relative delta 0.026869087702777482)
- Grade change: `bounded_support` -> `core_support`
- Enhanced rule ids: ``
- Interpretation: Full SCCA retains a modest positive UHI estimate while adding explicit balance and residual-spatial diagnostics that the raw comparison lacks.
