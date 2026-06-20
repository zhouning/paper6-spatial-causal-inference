# World Model Holdout Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible Experiment 6 module that compares world-model predictions with simple transition baselines and writes scenario-calibration diagnostics.

**Architecture:** Create one focused experiment module with deterministic fixture data, optional real AlphaEarth panel sampling, transition-pair builders, baseline predictors, output writers, and a small CLI. Keep existing world-model behavior unchanged.

**Tech Stack:** Python 3.11, pandas, numpy, scikit-learn, pytest, optional PyTorch and Earth Engine.

---

### Task 1: Lock the output contract with tests

**Files:**
- Create: `data_agent/test_world_model_holdout_validation.py`
- Create later: `data_agent/experiments/world_model_holdout_validation.py`

- [ ] **Step 1: Write the failing tests**

Add tests that import the new module and assert:

- `build_offline_fixture_panel()` returns rows with `area`, `split`,
  `pixel_id`, `year`, `lulc_label`, and `A00..A63`.
- `build_transition_pairs()` returns train and held-out pair tables.
- `run_world_model_holdout_validation()` writes:
  - `world_model_holdout_metrics.csv`
  - `world_model_scenario_calibration.csv`
  - `world_model_holdout_validation_manifest.json`
  - `world_model_holdout_validation_report.md`
- the metrics CSV includes `persistence`, `mean_delta`, `ridge_transition`,
  and `markov_transition`.
- the calibration CSV includes scenario scale factors and plausibility flags.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_world_model_holdout_validation.py -q
```

Expected: fail because the module does not exist yet.

### Task 2: Implement fixture panel and pair builders

**Files:**
- Modify: `data_agent/experiments/world_model_holdout_validation.py`
- Test: `data_agent/test_world_model_holdout_validation.py`

- [ ] **Step 1: Implement minimal fixture generation**

Create deterministic unit-normalized 64D embeddings over areas, pixels, and
years. Include class labels generated from class-specific prototypes.

- [ ] **Step 2: Implement transition-pair extraction**

Build train and holdout pair records with `z_t`, `z_tp1`, metadata, and labels.

- [ ] **Step 3: Run focused tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_world_model_holdout_validation.py -q
```

Expected: tests now advance to predictor/output failures.

### Task 3: Implement predictors and metrics

**Files:**
- Modify: `data_agent/experiments/world_model_holdout_validation.py`

- [ ] **Step 1: Add persistence and mean-delta predictors**

Use train-pair average deltas for `mean_delta` and normalize predicted vectors.

- [ ] **Step 2: Add ridge transition regression**

Fit `sklearn.linear_model.Ridge` on train `z_t -> z_tp1` and predict holdout
transitions.

- [ ] **Step 3: Add Markov decoded-class predictor**

Estimate train decoded-class transition probabilities and class prototypes; use
them to predict held-out next embeddings and labels.

- [ ] **Step 4: Add optional world-model predictor**

Call an injected predictor when supplied. Otherwise try the local world-model
weights and return an explicit skipped row if loading fails.

- [ ] **Step 5: Run focused tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_world_model_holdout_validation.py -q
```

Expected: all focused tests pass.

### Task 4: Implement scenario calibration and writers

**Files:**
- Modify: `data_agent/experiments/world_model_holdout_validation.py`

- [ ] **Step 1: Add scenario scaling diagnostics**

For scale values `0.25, 0.5, 1.0, 2.0, 4.0`, compute mean predicted embedding
delta and compare it to observed holdout transition deltas.

- [ ] **Step 2: Add output writer**

Write the required CSVs plus manifest and Markdown report. Include evidence
mode and claim guidance.

- [ ] **Step 3: Add CLI**

Support:

```powershell
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.world_model_holdout_validation --output-dir paper\ijgis_submission_20260605\07_results
```

Optional flags should allow `--attempt-gee`, `--n-points`, and `--years`.

- [ ] **Step 4: Run focused tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_world_model_holdout_validation.py -q
```

Expected: all focused tests pass.

### Task 5: Generate outputs and verify regressions

**Files:**
- Modify: `paper/ijgis_submission_20260605/07_results/world_model_*`

- [ ] **Step 1: Run the experiment**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.world_model_holdout_validation --output-dir paper\ijgis_submission_20260605\07_results
```

Expected: required world-model CSVs and report/manifest are written.

- [ ] **Step 2: Run focused regression tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_world_model_holdout_validation.py data_agent\test_world_model.py data_agent\test_causal_world_model.py -q
```

Expected: all tests pass except known pre-existing warnings.

- [ ] **Step 3: Run paper-experiment regression tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_world_model_holdout_validation.py data_agent\test_llm_dag_validation.py data_agent\test_geofm_alphaearth_ablation.py data_agent\test_chongqing_uhi_analysis.py data_agent\test_synthetic_benchmark_audit.py data_agent\test_synthetic_multiseed_benchmark.py -q
```

Expected: all tests pass except known pre-existing warnings.

- [ ] **Step 4: Commit**

Run:

```powershell
git add data_agent/test_world_model_holdout_validation.py data_agent/experiments/world_model_holdout_validation.py docs/superpowers/specs/2026-06-20-world-model-holdout-validation-design.md docs/superpowers/plans/2026-06-20-world-model-holdout-validation-implementation.md paper/ijgis_submission_20260605/07_results/world_model_*
git commit -m "Add world model holdout validation"
```
