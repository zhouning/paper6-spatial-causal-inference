# SCCA Soho Mechanism Experiment Design

## Goal

Build a second SCCA experiment that uses the Soho cholera data as a mechanism check for the Paper6 spatial causal workflow. The experiment should test whether proximity to the Broad Street pump is associated with higher cholera mortality after adjusting for observed local spatial context.

## Scope

This spec implements one new reproducible experiment, not a manuscript rewrite.

Included:

- Main input: `snow1/deaths_nd_by_house.csv`.
- Primary unit: household or address-level record from `snow1`.
- Primary outcome: `deaths`.
- Auxiliary binary outcome retained for diagnostics: `death_dum`.
- Primary exposure: `bspump_proximity = -log1p(dis_bspump)`, so larger values mean closer to the Broad Street pump.
- Context/confounding variables: `dis_pestf`, `dis_sewers`, `pestfield`, `COORD_X`, `COORD_Y`.
- Output directory: `paper/ijgis_submission_20260605/07_results/scca_soho/`.
- Outputs should mirror the snow8 experiment: profile, candidate variables, context features, design plan, effect estimates, ERF curve, model diagnostics, balance summary, overlap summary, spatial robustness, credibility report, analysis report, and manifest.

Excluded for this checkpoint:

- Manuscript editing.
- Full multi-pump network modeling.
- Geopackage/shapefile visualization.
- snow2 building-level replication.
- formal spatial count models such as Poisson CAR/SAR.

## Causal Interpretation

The experiment is a mechanism check, not a standalone proof of random assignment. A result is useful if it shows that the SCCA workflow can recover the expected Broad Street pump signal while explicitly reporting overlap, balance, and robustness limits.

Expected direction:

- Higher `bspump_proximity` should be associated with higher `deaths`.

Decision interpretation:

- `strong_support`: expected direction, acceptable overlap/balance, stable robustness.
- `moderate_support`: expected direction but meaningful balance/overlap/robustness warnings.
- `weak_or_failed_support`: missing support, unstable estimates, skipped estimators, or direction inconsistent with mechanism.

## Architecture

Add a small Soho-specific adapter rather than changing the general SCCA internals heavily.

Files:

- `data_agent/scca/specs.py`: add `StudySpec.soho_default()`.
- `data_agent/experiments/run_scca_soho.py`: load the snow1 CSV, create `bspump_proximity`, run the existing SCCA modules, and write provenance metadata.
- `data_agent/test_scca_soho.py`: focused tests for preprocessing, end-to-end fixture run, and output contract.
- `README.md`: add a command for the Soho mechanism experiment after implementation.

The existing snow8 runner remains unchanged except for shared helper reuse if a small private helper can reduce exact duplication without broad refactoring.

## Data Flow

1. Load `deaths_nd_by_house.csv`.
2. Coerce numeric fields: `deaths`, `death_dum`, `dis_bspump`, `dis_pestf`, `dis_sewers`, `pestfield`, `COORD_X`, `COORD_Y`.
3. Create `bspump_proximity = -log1p(dis_bspump)`.
4. Run existing SCCA modules:
   - `profile_table`
   - `build_context_features`
   - `select_design`
   - `estimate_effects`
   - `audit_effects`
   - `write_report`
5. Return parsed manifest.

## Testing

Use TDD. Minimum tests:

- `StudySpec.soho_default()` exposes the expected columns.
- Soho preprocessing creates `bspump_proximity` and preserves expected row count.
- Fixture end-to-end run writes all manifest-listed files.
- CLI prints parseable manifest JSON.
- Existing snow8 tests still pass.
- Existing causal inference tests still pass before completion.

## Acceptance Criteria

- `data_agent/test_scca_soho.py` passes.
- `data_agent/test_scca_snow8.py` still passes.
- `data_agent/test_causal_inference.py` still passes with only the known event-loop deprecation warning.
- Real snow1 run produces `paper/ijgis_submission_20260605/07_results/scca_soho/manifest.json`.
- The final response reports the actual Soho decision and key reasons without overstating causal proof.
