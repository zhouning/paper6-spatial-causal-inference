# Chongqing UHI Ablation and Robustness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible Chongqing UHI ablation and spatial robustness suite that writes the IJGIS-required real-case experiment outputs.

**Architecture:** Create a focused `data_agent.experiments.chongqing_uhi_analysis` module for all matching, balance, bootstrap, placebo, residual-diagnostic, and output-writing logic. Keep `scripts/causal_case_study.py` as the data extraction wrapper and make it call the module after assembling the analysis frame.

**Tech Stack:** Python 3.11, pandas, numpy, scipy, scikit-learn, pytest, optional geopandas/GEE only in the wrapper script.

---

### Task 1: Add failing tests for feature specs and output contract

**Files:**
- Create: `data_agent/test_chongqing_uhi_analysis.py`
- Create later: `data_agent/experiments/chongqing_uhi_analysis.py`

- [ ] **Step 1: Write the failing test**

Add tests using a deterministic fixture with columns:

```python
floor, treatment, LST, centroid_x, centroid_y, area_m2,
elevation, slope, B2, B3, B4, B8, B11, B12, NDVI, NDBI, MNDWI, BSI
```

Assert that:

- all eight required variants are present,
- `rs_` prefixed remote-sensing columns are accepted,
- output writer creates the six IJGIS-required CSV files plus manifest/report.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_chongqing_uhi_analysis.py -q
```

Expected: fail because `data_agent.experiments.chongqing_uhi_analysis` does not
exist yet.

- [ ] **Step 3: Implement minimal module**

Implement:

- `DEFAULT_OUTPUT_DIR`
- `FEATURE_SPECS`
- `resolve_feature_columns(frame, names)`
- `write_chongqing_outputs(...)`

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command and confirm it passes.

### Task 2: Add failing tests for matching and balance

**Files:**
- Modify: `data_agent/test_chongqing_uhi_analysis.py`
- Modify: `data_agent/experiments/chongqing_uhi_analysis.py`

- [ ] **Step 1: Write the failing test**

Test `run_psm_ablation(frame, threshold=10, caliper=0.2, n_bootstrap=50)` and assert:

- `raw`, `coordinates_only`, and `full_rs_context` rows are present,
- non-raw rows report `common_support_n`, `matched_treated_n`,
  `matched_control_n`, `caliper_abs`, and `max_post_smd`,
- balance rows include `pre_smd`, `post_smd`, and `balance_pass_0_1`,
- matched count rows include `drop_rate`,
- at least one substantive fixture row reaches max post-match SMD below `0.1`.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_chongqing_uhi_analysis.py -q
```

Expected: fail because matching is not implemented.

- [ ] **Step 3: Implement matching**

Implement:

- numeric frame preparation,
- PCA context construction,
- logistic propensity estimation on standardized covariates,
- common-support filtering,
- nearest-neighbor caliper matching,
- ATT and matched-pair bootstrap CI,
- pre/post SMD diagnostics.

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command and confirm it passes.

### Task 3: Add failing tests for spatial robustness

**Files:**
- Modify: `data_agent/test_chongqing_uhi_analysis.py`
- Modify: `data_agent/experiments/chongqing_uhi_analysis.py`

- [ ] **Step 1: Write the failing test**

Test:

- `run_threshold_placebos(...)` returns thresholds `8`, `10`, `12`.
- `run_spatial_block_bootstrap(...)` returns requested replicate rows with
  `block_count`, `att`, `status`.
- `run_residual_spatial_diagnostics(...)` returns `moran_i`,
  `permutation_p_value`, `n`, and `distance_band`.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_chongqing_uhi_analysis.py -q
```

Expected: fail because robustness helpers are missing.

- [ ] **Step 3: Implement robustness helpers**

Implement:

- coordinate grid block assignment,
- block bootstrap over grid IDs,
- threshold-placebo loop,
- OLS residualization and distance-band Moran-like permutation statistic.

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command and confirm it passes.

### Task 4: Wire the script wrapper

**Files:**
- Modify: `scripts/causal_case_study.py`
- Modify if needed: `README.md`, `REPRODUCIBILITY.md`

- [ ] **Step 1: Write the failing test**

Add a light test that imports `scripts.causal_case_study` and confirms it exposes
`run_chongqing_uhi_case_study` or another explicit wrapper that calls
`run_chongqing_uhi_analysis`.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_chongqing_uhi_analysis.py -q
```

Expected: fail because the wrapper has not been changed.

- [ ] **Step 3: Update the script**

Keep the existing loading and GEE extraction functions, but replace ad hoc
`step4_psm_analysis`, `step5_pca_ablation`, and direct output writing with a
call to `run_chongqing_uhi_analysis(...)`.

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command and confirm it passes.

### Task 5: Generate outputs and verify

**Files:**
- Modify: `paper/ijgis_submission_20260605/07_results/chongqing_*`
- Modify: `README.md`
- Modify: `REPRODUCIBILITY.md`

- [ ] **Step 1: Run focused tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_chongqing_uhi_analysis.py data_agent\test_synthetic_benchmark_audit.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run the case-study script**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe scripts\causal_case_study.py
```

Expected: required Chongqing CSV/JSON/Markdown outputs are written. If GEE is
unavailable, manifest/report clearly mark the run as fallback smoke data.

- [ ] **Step 3: Run final verification**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_chongqing_uhi_analysis.py data_agent\test_synthetic_multiseed_benchmark.py data_agent\test_synthetic_benchmark_audit.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

Run:

```powershell
git add data_agent/experiments/chongqing_uhi_analysis.py data_agent/test_chongqing_uhi_analysis.py scripts/causal_case_study.py README.md REPRODUCIBILITY.md paper/ijgis_submission_20260605/07_results/chongqing_* docs/superpowers/specs/2026-06-20-chongqing-uhi-ablation-robustness-design.md docs/superpowers/plans/2026-06-20-chongqing-uhi-ablation-robustness-implementation.md
git commit -m "Add Chongqing UHI ablation and robustness suite"
```
