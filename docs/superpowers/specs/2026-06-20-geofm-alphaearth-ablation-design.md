# GeoFM AlphaEarth Ablation Design

Date: 2026-06-20

## Goal

Strengthen Paper 6 with a direct GeoFM/AlphaEarth experiment that decides
whether the manuscript can keep bounded GeoFM-specific claims.

## Scope

Included:

- A reusable experiment module that writes:
  - `geofm_availability_report.json`
  - `geofm_causal_ablation.csv`
  - `geofm_balance_diagnostics.csv`
- Reuse of the Chongqing UHI matching and balance protocol.
- Support for existing Chongqing analysis samples that may or may not already
  contain AlphaEarth columns.
- Optional Earth Engine point sampling at building centroids to attach real
  AlphaEarth vectors when runtime access is available.
- Honest fallback behavior when GeoFM columns are unavailable.

Excluded:

- QGIS and notebook work.
- Manuscript edits.
- Synthetic or invented GeoFM values in production experiment outputs.

## Current Evidence State

The repository contains:

- a reusable Chongqing UHI matching pipeline,
- historical Phase 0 AlphaEarth validation outputs under
  `scripts/phase0_results/phase0_results.json`,
- local AlphaEarth encoder weights,
- no confirmed Chongqing building-centroid sample with attached real 64D
  AlphaEarth columns.

That means the next experiment must separate two questions:

1. Is AlphaEarth available in this environment and for this task?
2. If yes, does adding AlphaEarth improve balance or ATT stability beyond the
   existing Sentinel/DEM controls?

## Design

### Analysis Module

Create `data_agent/experiments/geofm_alphaearth_ablation.py`.

Responsibilities:

1. Detect AlphaEarth columns in multiple naming conventions:
   - `A00` to `A63`
   - `geofm_00` to `geofm_63`
   - `geofm_0` to `geofm_63`
   - optional `rs_A00` to `rs_A63`
2. Build five causal variants:
    - `geometry_only`
    - `geometry_rs_context`
    - `geometry_alphaearth_64d`
    - `geometry_rs_alphaearth_64d`
    - `geometry_alphaearth_pca`
    - `geometry_rs_alphaearth_pca`
3. Reuse the Chongqing preparation, standardization, propensity estimation,
   common-support trimming, nearest-neighbor caliper matching, bootstrap CI,
   and SMD reporting protocol.
4. Write a machine-readable availability report that records:
   - whether historical Phase 0 evidence exists,
   - whether local AlphaEarth weights exist,
   - whether cached embedding coverage is discoverable,
   - whether the input analysis sample already contains AlphaEarth columns,
   - whether runtime point sampling was attempted and succeeded.
5. Optionally sample real AlphaEarth vectors at centroid points through Earth
   Engine and attach them to the analysis frame.

### Output Behavior

The experiment should always write all three IJGIS-requested files.

If real AlphaEarth columns are unavailable:

- `geometry_only` and `geometry_rs_context` should still run.
- GeoFM-dependent variants should appear with explicit skipped status.
- The availability report should say GeoFM claims are not supported in the
  current run.

If real AlphaEarth columns are available:

- all five variants should run,
- balance diagnostics should be reported for every covariate,
- the report should compare the best GeoFM row against the best non-GeoFM row.

### Claim Guidance

The module should render a conservative guidance label:

- `bounded_geofm_claim_supported`: at least one GeoFM row is estimable, reaches
  max post-match SMD below `0.1`, and is no worse than the best non-GeoFM row.
- `geofm_no_clear_gain`: GeoFM rows run but do not improve balance or stability.
- `geofm_unavailable`: no real GeoFM row could be estimated.

## Testing Strategy

Use TDD.

Minimum tests:

- resolver accepts the supported AlphaEarth column naming schemes,
- full runner writes the required files and expected variant rows,
- missing-GeoFM inputs still produce valid observed-covariate rows and explicit
  skipped GeoFM rows.

## Acceptance Criteria

This task is complete when:

- the new GeoFM experiment module passes focused tests,
- required output files are written under
  `paper/ijgis_submission_20260605/07_results/`,
- the availability report clearly distinguishes historical Phase 0 evidence
  from current Chongqing-centroid causal evidence,
- the experiment never fabricates GeoFM evidence when real embeddings are not
  available.
