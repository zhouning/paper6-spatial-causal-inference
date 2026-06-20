# World Model Holdout Validation Design

Date: 2026-06-20

## Goal

Strengthen Paper 6 Angle C with a reproducible world-model validation that
separates held-out predictive evidence from scenario-simulation evidence.

## Scope

Included:

- A reusable experiment module that writes:
  - `world_model_holdout_metrics.csv`
  - `world_model_scenario_calibration.csv`
- One-step and multi-step transition evaluation in AlphaEarth-like embedding
  space.
- Baseline comparisons against:
  - persistence,
  - Markov decoded-class transitions,
  - ridge transition regression,
  - the repository world-model dynamics when weights are loadable.
- Optional real AlphaEarth temporal-panel sampling from Earth Engine.
- Deterministic offline fixture mode when real temporal panels are unavailable.
- Conservative claim guidance in a manifest and Markdown report.

Excluded:

- QGIS work.
- Notebook work.
- Manuscript edits.
- Claims that offline fixture or proxy results prove real held-out prediction.

## Current Evidence State

The repository already contains:

- `data_agent/world_model.py` with AlphaEarth constants, dynamics weights, and
  inference helpers.
- `data_agent/causal_world_model.py` with scenario and ATT-calibration tools.
- historical Phase 0 AlphaEarth feasibility metrics in
  `scripts/phase0_results/phase0_results.json`.
- prior 17-area and rollout summaries under `data_agent/experiments/output/`.

The local `data_agent/weights/raw_data/` cache is not sufficient by itself for
full offline real-panel validation. Therefore the experiment must report its
evidence mode explicitly:

- `real_alphaearth_panel`: sampled or loaded real multi-year embeddings.
- `offline_fixture_proxy`: deterministic synthetic AlphaEarth-like temporal
  panel used to verify the evaluation protocol and compare baselines.

## Design

### Analysis Module

Create `data_agent/experiments/world_model_holdout_validation.py`.

Responsibilities:

1. Represent a temporal embedding panel as a long table with:
   - `area`,
   - `split`,
   - `pixel_id`,
   - `year`,
   - `A00` to `A63`,
   - optional `lulc_label`.
2. Build transition pairs from the panel:
   - training pairs from earlier years and training/validation splits,
   - held-out pairs from test/OOD splits and later years,
   - one-step and multi-step rows.
3. Compare predictors:
   - `persistence`: `z_t`.
   - `mean_delta`: `z_t + mean(train_delta)`.
   - `ridge_transition`: multi-output ridge regression from `z_t` to
     `z_{t+1}`.
   - `markov_transition`: decoded-label transition probabilities plus class
     prototypes.
   - `world_model_baseline`: local latent-dynamics model under the baseline
     scenario, if loadable.
4. Report embedding metrics:
   - mean cosine similarity,
   - mean cosine distance,
   - RMSE,
   - MAE,
   - mean L2 distance,
   - row counts.
5. Report decoded land-cover accuracy when labels or a decoder are available.
6. Run scenario scaling calibration:
   - generate several scenario scale factors,
   - compute predicted embedding-delta magnitude,
   - compare it with observed holdout delta magnitude,
   - flag whether predicted deltas stay inside a conservative plausibility
     envelope derived from observed transitions.

### Real-Panel Sampling

Optional Earth Engine sampling should:

- build one stacked image containing the requested years,
- sample fixed locations once per area,
- keep only complete rows across all requested years,
- write metadata on attempted areas, years, sample counts, and failures.

When real sampling is not requested or fails, the default experiment should use
the deterministic offline fixture and mark outputs as `offline_fixture_proxy`.

### Output Behavior

The experiment always writes both IJGIS-required CSV files.

It also writes:

- `world_model_holdout_validation_manifest.json`
- `world_model_holdout_validation_report.md`

The report must include claim guidance:

- `predictive_validation_available`: real AlphaEarth panel was evaluated.
- `scenario_simulation_only`: no real panel was evaluated, so Angle C should be
  presented as calibrated scenario simulation rather than predictive evidence.

## Testing Strategy

Use TDD.

Minimum tests:

- deterministic fixture panel generation creates all expected embedding and
  label fields,
- transition-pair builder creates train and held-out rows,
- holdout runner writes both required CSV files and includes all required
  baselines,
- scenario calibration runner writes plausible scaling diagnostics,
- skipped world-model prediction does not break the baseline comparison.

## Acceptance Criteria

This task is complete when:

- focused tests for the new module pass,
- the experiment writes the two IJGIS-required output CSV files under
  `paper/ijgis_submission_20260605/07_results/`,
- output metadata clearly states whether the run used real AlphaEarth data or
  offline fixture/proxy data,
- Angle C claim guidance remains conservative unless real held-out validation
  was actually run.
