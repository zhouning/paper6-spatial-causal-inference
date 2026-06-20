# Synthetic Benchmark Audit Design

Date: 2026-06-20

## Goal

Strengthen Paper 6 synthetic evidence by adding a second-layer benchmark audit that
goes beyond one summary row per estimator. The new audit should expose when each
synthetic estimator is robust, when it degrades under stress, and which failure
modes are estimator-specific versus scenario-specific.

## Scope

Included:

- All six synthetic estimators already used by Paper 6:
  - PSM
  - DiD
  - ERF
  - Granger
  - GCCM
  - CausalForest
- Multiple stress settings per estimator.
- Existing estimator variants where they are already meaningful.
- Audit summary, detailed JSON, manifest, and Markdown report.
- Tests for output contracts and fragility classification.
- A CLI entry for running the audit without replacing the existing
  `synthetic_multiseed` outputs.

Excluded:

- QGIS, notebook, or GeoCausal integration work.
- Real-data experiments.
- Manuscript edits.
- Replacing the existing `synthetic_multiseed_summary.csv` baseline files.

## Current Evidence State

The existing synthetic multi-seed benchmark already shows that the evidence is
uneven across methods:

- `PSM` standard matching strongly underestimates the generator effect under the
  current setup.
- `GCCM` direction recovery is unstable and sensitive to neighborhood choices.
- `DiD`, `CausalForest`, and `Granger` look stronger, but only under one default
  generator configuration each.
- `ERF` recovers the response shape imperfectly and should be stress-tested under
  noise and sample-size changes.

This means the next step is not another single table. It is an audit layer that
explicitly maps robustness boundaries.

## Design

### Separate Audit Output Directory

Keep the existing benchmark intact and add a new output directory:

- `paper/ijgis_submission_20260605/07_results/synthetic_benchmark_audit/`

This prevents the new audit from rewriting already committed benchmark artifacts.

### New Audit Module

Add a dedicated module under `data_agent/experiments/` that:

1. Defines scenario-specific stress settings.
2. Reuses the existing estimator runners where possible.
3. Runs settings x variants x seeds.
4. Aggregates performance and failure statistics.
5. Assigns a fragility label for each summary row.
6. Renders a short Markdown report highlighting robust and fragile findings.

### Stress Settings

Each scenario gets a small set of named settings with explicit stress levels.

Common intent:

- `baseline`: current setup.
- `mild_stress`: smaller sample, weaker signal, or moderate extra noise.
- `severe_stress`: stronger overlap problems, less data, weaker direction signal,
  or higher noise.

Scenario-specific focus:

- `PSM`: overlap, treatment prevalence imbalance, and sample-size stress.
- `DiD`: panel length and observational noise stress.
- `ERF`: sample size, exposure support, and outcome noise stress.
- `Granger`: series length and lag-signal strength stress.
- `GCCM`: grid size, local-gradient weakness, and noise stress.
- `CausalForest`: sample size, heterogeneity strength, and outcome noise stress.

### Variants

Retain existing meaningful variants:

- `PSM`: `standard`, `caliper`, `kernel`, `naive_difference`, `ols_adjusted`
- `GCCM`: `standard`, `knn_k2`, `queen`
- Other estimators remain `standard` unless a variant is already part of the
  current benchmark logic.

### Output Contract

Required files:

- `synthetic_benchmark_audit_summary.csv`
- `synthetic_benchmark_audit_details.json`
- `synthetic_benchmark_audit_manifest.json`
- `synthetic_benchmark_audit_report.md`
- `scenario_fragility_summary.csv`

Required summary columns:

- `scenario`
- `setting`
- `stress_level`
- `variant`
- `method`
- `metric_name`
- `n_seeds`
- `n_success`
- `failure_count`
- `true_value`
- `estimate_mean`
- `estimate_std`
- `bias`
- `rmse`
- `mae`
- `coverage_rate`
- `fragility`
- `fragility_reason`
- `score`

Required detail fields:

- existing seed-level benchmark fields
- `setting`
- `stress_level`

### Fragility Rules

The audit is intended to support honest experimental interpretation rather than
optimize for pretty numbers.

Continuous-effect methods:

- `robust`: low normalized bias/RMSE, low failure count, and acceptable coverage
  when coverage is defined.
- `bounded`: some degradation but still directionally or quantitatively usable.
- `fragile`: large bias, large failure rate, or severe coverage breakdown.

Direction-recovery methods:

- `robust`: high direction accuracy.
- `bounded`: mixed recovery.
- `fragile`: low recovery or inconsistent direction.

The report should explain which threshold triggered the label.

### Markdown Report

The report should be short and factual:

- one-line purpose
- scenario-level summary
- most fragile scenario/setting/variant combinations
- strongest scenario/setting/variant combinations
- specific notes for PSM and GCCM because they are currently the main weak points

## Testing Strategy

Use TDD.

Minimum tests:

- Audit runner writes all required output files.
- Audit summary includes `setting`, `stress_level`, and `fragility`.
- Scenario fragility summary is produced and counts scenarios correctly.
- Markdown report includes both a robust and a fragile section.
- Existing `synthetic_multiseed` tests still pass.

## Acceptance Criteria

This task is complete when:

- The new audit files exist under the dedicated output directory.
- The audit can run from CLI without replacing the existing benchmark files.
- Tests for the new audit pass.
- Existing benchmark tests still pass.
- The full audit has been run once in this branch and produced committed result
  artifacts that can support later paper revisions.
