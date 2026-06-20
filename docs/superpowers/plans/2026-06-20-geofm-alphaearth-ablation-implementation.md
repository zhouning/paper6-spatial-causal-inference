# GeoFM AlphaEarth Ablation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable GeoFM/AlphaEarth availability and causal-ablation experiment for the Chongqing UHI case.

**Architecture:** Build a dedicated experiment module that reuses the Chongqing matching protocol, adds AlphaEarth column resolution and optional Earth Engine point sampling, and writes the IJGIS-required GeoFM outputs plus a conservative report/manifest.

**Tech Stack:** Python 3.11, pandas, numpy, scikit-learn, pytest, optional Earth Engine via existing project dependencies.

---

### Task 1: Lock the output contract with tests

**Files:**
- Create: `data_agent/test_geofm_alphaearth_ablation.py`
- Create later: `data_agent/experiments/geofm_alphaearth_ablation.py`

- [ ] **Step 1: Write the failing test**

Add deterministic fixtures with Chongqing-like geometry, Sentinel/DEM features,
and synthetic 64D AlphaEarth columns. Assert that:

- the resolver accepts `A00..A63` and `geofm_0..63`,
- the full runner writes the required JSON/CSV files,
- the five required variants appear in the ablation output,
- the RS-plus-PCA GeoFM variant appears in the ablation output,
- missing-GeoFM inputs produce skipped GeoFM rows without breaking observed-only
  rows.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_geofm_alphaearth_ablation.py -q
```

Expected: fail because the new module does not exist yet.

- [ ] **Step 3: Implement minimal module surface**

Implement:

- `resolve_geofm_columns`
- `run_geofm_causal_ablation`
- `build_geofm_availability_report`
- `write_geofm_outputs`
- `run_geofm_alphaearth_analysis`

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command and confirm it passes.

### Task 2: Add optional real AlphaEarth attachment

**Files:**
- Modify: `data_agent/experiments/geofm_alphaearth_ablation.py`

- [ ] **Step 1: Write the failing test**

Use a light unit test or injected callback path to ensure the module can accept
newly attached GeoFM columns and rerun the ablation without changing the output
contract.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_geofm_alphaearth_ablation.py -q
```

Expected: fail because the attachment path is not wired yet.

- [ ] **Step 3: Implement attachment path**

Add optional Earth Engine point sampling at centroid coordinates with batched
`sampleRegions` calls and explicit success/failure metadata.

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command and confirm it passes.

### Task 3: Generate outputs and verify

**Files:**
- Modify: `paper/ijgis_submission_20260605/07_results/geofm_*`

- [ ] **Step 1: Run focused tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_geofm_alphaearth_ablation.py data_agent\test_chongqing_uhi_analysis.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run the GeoFM experiment**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.geofm_alphaearth_ablation --input-csv paper\ijgis_submission_20260605\07_results\chongqing_uhi_analysis_sample.csv --output-dir paper\ijgis_submission_20260605\07_results --attempt-gee --probe-runtime
```

Expected:

- if Earth Engine works, real AlphaEarth rows are estimated;
- if Earth Engine does not work, availability is reported honestly and only
  observed-covariate rows are estimable.

- [ ] **Step 3: Run final verification**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_geofm_alphaearth_ablation.py data_agent\test_chongqing_uhi_analysis.py data_agent\test_synthetic_benchmark_audit.py data_agent\test_synthetic_multiseed_benchmark.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

Run:

```powershell
git add data_agent/test_geofm_alphaearth_ablation.py data_agent/experiments/geofm_alphaearth_ablation.py docs/superpowers/specs/2026-06-20-geofm-alphaearth-ablation-design.md docs/superpowers/plans/2026-06-20-geofm-alphaearth-ablation-implementation.md paper/ijgis_submission_20260605/07_results/geofm_*
git commit -m "Add GeoFM AlphaEarth ablation experiment"
```
