# ArcGIS GPS Balance Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit OLS/GBM GPS selection, ArcGIS-compatible balance fields, and a nonlinear GPS benchmark for Paper 6.

**Architecture:** Extend the existing ArcGIS-style matching module rather than adding a parallel estimator. Open GIS packaging consumes the selected method and writes stable GIS-facing aliases plus aggregate balance fields.

**Tech Stack:** Python, pandas, numpy, statsmodels, scikit-learn `GradientBoostingRegressor`, pytest.

---

## File Structure

- Modify `geocausal/arcgis_style_matching.py`: add GPS method enum behavior, GBM fit, method-aware grid search, and aggregate balance helpers.
- Modify `geocausal/open_gis.py`: add ArcGIS alias columns and aggregate balance fields to CSV/JSON outputs.
- Create `data_agent/experiments/arcgis_gps_balance_benchmark.py`: deterministic nonlinear OLS-vs-GBM benchmark writer.
- Modify `data_agent/experiments/arcgis_commercial_benchmark.py`: update parity matrix evidence for verified GBM GPS and balance fields.
- Modify `docs/arcgis_causal_inference_parity_matrix.md`: document the upgraded status.
- Add/modify tests in `data_agent/test_arcgis_style_matching.py`, `data_agent/test_geocausal_pipeline.py`, `data_agent/test_arcgis_gps_balance_benchmark.py`, and `data_agent/test_arcgis_commercial_benchmark.py`.

### Task 1: GPS Method Tests

**Files:**
- Modify: `data_agent/test_arcgis_style_matching.py`
- Modify: `geocausal/arcgis_style_matching.py`

- [ ] **Step 1: Write failing test for method-aware grid search**

Add a nonlinear fixture and assert GBM can be selected:

```python
def test_arcgis_style_matching_selects_gbm_for_nonlinear_gps_fixture():
    from geocausal.arcgis_style_matching import arcgis_style_matching_search

    frame = _nonlinear_gps_fixture()
    ols = arcgis_style_matching_search(
        frame,
        exposure="exposure",
        confounders=("confounder_a", "confounder_b"),
        num_bins=(4, 6, 8),
        scales=(0.0, 0.5, 1.0),
        gps_methods=("ols",),
    )
    gbm = arcgis_style_matching_search(
        frame,
        exposure="exposure",
        confounders=("confounder_a", "confounder_b"),
        num_bins=(4, 6, 8),
        scales=(0.0, 0.5, 1.0),
        gps_methods=("gbm",),
    )
    auto = arcgis_style_matching_search(
        frame,
        exposure="exposure",
        confounders=("confounder_a", "confounder_b"),
        num_bins=(4, 6, 8),
        scales=(0.0, 0.5, 1.0),
        gps_methods=("ols", "gbm"),
    )

    assert set(auto.grid["gps_method"]) == {"ols", "gbm"}
    assert auto.selected_gps_method == "gbm"
    assert gbm.selected_mean_abs_weighted_correlation < ols.selected_mean_abs_weighted_correlation
    assert auto.selected_mean_abs_weighted_correlation == gbm.selected_mean_abs_weighted_correlation
```

- [ ] **Step 2: Run red test**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_arcgis_style_matching.py::test_arcgis_style_matching_selects_gbm_for_nonlinear_gps_fixture -q
```

Expected: fail because `gps_methods` and `selected_gps_method` do not exist.

- [ ] **Step 3: Implement minimal method support**

Add `selected_gps_method` to `ArcGISStyleMatchingResult`, keep OLS as a method, add GBM fit with the same `_GPSFit` interface, add `gps_method` to grid rows, and select by mean absolute balance.

- [ ] **Step 4: Run green test**

Run the same pytest command. Expected: one test passes.

### Task 2: Open GIS ArcGIS Field Contract

**Files:**
- Modify: `data_agent/test_geocausal_pipeline.py`
- Modify: `data_agent/test_arcgis_style_matching.py`
- Modify: `geocausal/open_gis.py`

- [ ] **Step 1: Write failing tests**

Assert `analysis_joined.csv` includes:

```python
{
    "gc_arcgis_propensity_score",
    "gc_arcgis_matching_weight",
    "gc_arcgis_calibrated_weight",
    "gc_arcgis_gps_method",
}
```

Assert balance outputs and run summary include:

```python
{
    "arcgis_mean_abs_weighted_correlation",
    "arcgis_median_abs_weighted_correlation",
    "arcgis_max_abs_weighted_correlation",
    "arcgis_balanced_at_0_1",
}
```

- [ ] **Step 2: Run red tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_geocausal_pipeline.py::test_run_analysis_writes_open_gis_parity_package data_agent\test_arcgis_style_matching.py::test_open_gis_package_writes_arcgis_style_matching_outputs -q
```

Expected: fail on missing columns/summary keys.

- [ ] **Step 3: Implement aliases and aggregate fields**

Use selected ArcGIS-style matching outputs already returned from `write_open_gis_package`; write aliases to joined CSV and merge aggregate metrics into selected and calibrated balance CSVs plus `gis_run_summary.json`.

- [ ] **Step 4: Run green tests**

Run the same pytest command. Expected: both tests pass.

### Task 3: Synthetic GPS Balance Benchmark

**Files:**
- Create: `data_agent/experiments/arcgis_gps_balance_benchmark.py`
- Create: `data_agent/test_arcgis_gps_balance_benchmark.py`

- [ ] **Step 1: Write failing benchmark test**

Assert the writer creates `arcgis_gps_balance_benchmark.csv`, `arcgis_gps_balance_benchmark.json`, and records `gbm_beats_ols == True`.

- [ ] **Step 2: Run red test**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_arcgis_gps_balance_benchmark.py -q
```

Expected: import failure because the module does not exist.

- [ ] **Step 3: Implement benchmark writer**

Generate a deterministic nonlinear fixture, run OLS-only and GBM-only `arcgis_style_matching_search`, write a two-row CSV plus JSON manifest, and return the manifest.

- [ ] **Step 4: Run green test**

Run the same pytest command. Expected: benchmark test passes.

### Task 4: Parity Docs and Matrix

**Files:**
- Modify: `data_agent/test_arcgis_commercial_benchmark.py`
- Modify: `data_agent/experiments/arcgis_commercial_benchmark.py`
- Modify: `docs/arcgis_causal_inference_parity_matrix.md`

- [ ] **Step 1: Write failing parity test assertions**

Assert the GPS row status is no longer `partial` and the balance-threshold row references aggregate fields.

- [ ] **Step 2: Run red test**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_arcgis_commercial_benchmark.py -q
```

Expected: fail on old status/text.

- [ ] **Step 3: Update parity matrix and docs**

Update evidence artifact and next action text to point to verified OLS/GBM GPS selection and ArcGIS-compatible balance fields.

- [ ] **Step 4: Run green test**

Run the same pytest command. Expected: parity benchmark tests pass.

### Task 5: Full Verification, Commit, Push

**Files:**
- All changed files
- Progress log: `D:\adk\paper6_github_progress_20260627_open_gis_parity_pr.md`

- [ ] **Step 1: Run focused verification**

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_arcgis_style_matching.py data_agent\test_geocausal_pipeline.py data_agent\test_arcgis_gps_balance_benchmark.py data_agent\test_arcgis_commercial_benchmark.py -q
```

- [ ] **Step 2: Run broader PR verification**

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_qgis_provider_structure.py data_agent\test_geocausal_adapters.py data_agent\test_paper6_benchmark_matrix.py -q
```

- [ ] **Step 3: Check whitespace**

```powershell
git -C D:\adk\paper6-spatial-causal-inference\.worktrees\open-gis-parity-package diff --check
```

- [ ] **Step 4: Commit and push**

```powershell
git -C D:\adk\paper6-spatial-causal-inference\.worktrees\open-gis-parity-package add .
git -C D:\adk\paper6-spatial-causal-inference\.worktrees\open-gis-parity-package commit -m "Add ArcGIS GPS balance benchmark"
git -C D:\adk\paper6-spatial-causal-inference\.worktrees\open-gis-parity-package push origin open-gis-parity-package
```

- [ ] **Step 5: Verify PR state**

```powershell
gh api repos/zhouning/paper6-spatial-causal-inference/pulls/3 --jq "{number:.number,state:.state,mergeable:.mergeable,mergeable_state:.mergeable_state,head:.head.ref,head_sha:.head.sha,html_url:.html_url}"
```
