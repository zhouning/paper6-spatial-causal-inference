# Required Experiments Before IJGIS Submission

This file translates the IJGIS-style review into concrete experiments. The manuscript should not be submitted with strong GeoFM or causal-effect claims until the high-priority experiments below are completed.

## One-Sentence Revised Argument

In geographic observational studies, we show that spatial-context representations can make causal adjustment more explicit and testable by linking statistical effect estimation, mechanism reasoning, and scenario simulation, supported by controlled estimator checks and real-world spatial ablations, with GeoFM-specific claims limited to regions where embeddings are directly evaluated.

## Current Evidence Audit

Existing files show that the current draft evidence is incomplete:

- `data_agent/experiments/output/synthetic_results.json` contains stale or failed synthetic results:
  - PSM does not recover the stated true ATE in the saved run.
  - GCCM previously reported an API error.
  - Granger output includes a reverse significant pair.
- `scripts/causal_case_study_results.json` supports the Chongqing UHI narrative but reports high max SMD values after matching, so balance quality must be fixed or honestly reported.
- The manuscript's central GeoFM framing is not directly supported by the Chongqing case, which uses Sentinel-2 plus DEM features rather than AlphaEarth embeddings.

## Experiment 1: Repair and Rerun the Synthetic Benchmark

**Purpose:** Replace single-run illustrative claims with a reproducible multi-seed benchmark.

**Files to start from:**

- `data_agent/experiments/run_causal.py`
- `data_agent/experiments/output/synthetic_results.json`

**What to do:**

1. Fix each synthetic scenario so the generator, true effect, estimator input, and reported metric are aligned.
2. Run each scenario over at least 30 random seeds.
3. Report bias, RMSE, mean absolute error, 95% CI coverage, and failure count.
4. Add variants for each relevant estimator:
   - observed covariates only
   - observed covariates plus synthetic spatial-context features
   - PCA-reduced spatial-context features
   - no-context baseline where meaningful
5. Save a table to:
   - `paper/ijgis_submission_20260605/07_results/synthetic_multiseed_summary.csv`
   - `paper/ijgis_submission_20260605/07_results/synthetic_multiseed_details.json`

**Command after the script is updated:**

```powershell
.\.venv\Scripts\python.exe -m data_agent.experiments.run_causal --synthetic-only
```

**Acceptance criteria:**

- No scenario errors.
- Each estimator reports the target effect metric that matches the generator's true effect.
- Mean relative error is reported over seeds, not from a single run.
- If a method fails or produces biased estimates, the manuscript reports the failure mode instead of claiming universal recovery.

## Experiment 2: Chongqing UHI Ablation for Spatial-Context Adjustment

**Purpose:** Show whether spatial-context features improve causal adjustment in the real-world case.

**Files to start from:**

- `scripts/causal_case_study.py`
- `scripts/causal_case_study_results.json`

**Preconditions:**

- Google Earth Engine is authenticated: `earthengine authenticate`
- Building footprint shapefile exists at the configured `BUILDING_PATH`, or the script uses the repository-relative sample under `data/raw/01数据样例/04重庆市中心城区建筑物轮廓数据2021年/中心城区建筑数据带层高.shp`.

**Required variants:**

| Variant | Confounders |
| --- | --- |
| Raw | none |
| Coordinates only | centroid_x, centroid_y |
| Geometry | centroid_x, centroid_y, area_m2 |
| Terrain | centroid_x, centroid_y, area_m2, elevation, slope |
| Sentinel indices | geometry + NDVI, NDBI, MNDWI, BSI |
| Sentinel bands | geometry + B2, B3, B4, B8, B11, B12 |
| Full RS context | geometry + all Sentinel and DEM features |
| PCA context | geometry + top PCs explaining 95% variance |

**Method requirements:**

1. Standardize all continuous confounders before propensity-score estimation.
2. Enforce common support by removing samples outside overlapping propensity ranges.
3. Use nearest-neighbor matching with caliper and report the caliper.
4. Report matched sample counts and unmatched/drop rates.
5. Report pre- and post-matching SMD for every covariate.
6. Treat max post-match SMD >= 0.1 as failed balance unless justified.

**Output files:**

- `paper/ijgis_submission_20260605/07_results/chongqing_uhi_ablation.csv`
- `paper/ijgis_submission_20260605/07_results/chongqing_uhi_balance.csv`
- `paper/ijgis_submission_20260605/07_results/chongqing_uhi_matched_counts.csv`

**Command after adding the ablation mode:**

```powershell
.\.venv\Scripts\python.exe scripts\causal_case_study.py
```

**Acceptance criteria:**

- At least one credible specification reaches max post-match SMD < 0.1.
- ATT, CI, sample size, and balance are reported for every variant.
- The manuscript does not present the sign reversal as causal unless balance and sensitivity checks support it.

## Experiment 3: Spatial Robustness and Sensitivity Analysis

**Purpose:** Address spatial dependence, interference, and hidden confounding.

**What to add to the Chongqing case:**

1. Spatial block bootstrap:
   - Divide the study area into grid blocks, for example 1 km or 2 km cells.
   - Resample blocks rather than individual buildings.
   - Recompute ATT for 500 to 1000 bootstrap draws.
2. Clustered uncertainty:
   - Cluster by district or grid block.
   - Report cluster-robust CI where possible.
3. Placebo thresholds:
   - Repeat treatment definition with high-rise thresholds of 8, 10, and 12 floors.
   - Check whether conclusions depend on the arbitrary threshold.
4. Placebo outcome or season:
   - Repeat LST extraction for non-summer months or another less plausible outcome window.
5. Residual spatial autocorrelation:
   - Compute Moran's I on matched residuals or outcome residuals if spatial weights are available.

**Output files:**

- `paper/ijgis_submission_20260605/07_results/chongqing_spatial_bootstrap.csv`
- `paper/ijgis_submission_20260605/07_results/chongqing_placebo_thresholds.csv`
- `paper/ijgis_submission_20260605/07_results/chongqing_residual_spatial_diagnostics.csv`

**Acceptance criteria:**

- Main ATT sign and magnitude are not driven by one threshold, one area, or individual-level bootstrap assumptions.
- If robustness fails, revise the manuscript to report a spatial association analysis rather than a strong causal claim.

## Experiment 4: Direct GeoFM / AlphaEarth Ablation

**Purpose:** Decide whether the manuscript can make GeoFM-specific claims.

**Files to start from:**

- `scripts/phase0_alphaearth_validation.py`
- `docs/background/multimodal-semantic-fusion-plus-alphaearth-strategy.md`

**Step A: Verify availability.**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\phase0_alphaearth_validation.py
```

This script already samples `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL` in three Chinese study areas. Use its output to verify that AlphaEarth embeddings can be accessed through GEE.

**Step B: Add GeoFM features to a causal case.**

Preferred route:

1. Sample AlphaEarth 64D vectors at the same building centroids used in the Chongqing UHI case.
2. Add variants:
   - geometry only
   - geometry + Sentinel/DEM
   - geometry + AlphaEarth 64D
   - geometry + Sentinel/DEM + AlphaEarth 64D
   - geometry + AlphaEarth PCA
3. Use the same matching and balance protocol as Experiment 2.

Fallback route if AlphaEarth is not available for Chongqing:

1. Select one of the Phase 0 regions where AlphaEarth extraction works.
2. Build a smaller causal case using available LST, land cover, terrain, and a policy-relevant treatment proxy.
3. Present this as a GeoFM ablation case, separate from the Chongqing UHI case.

**Output files:**

- `paper/ijgis_submission_20260605/07_results/geofm_availability_report.json`
- `paper/ijgis_submission_20260605/07_results/geofm_causal_ablation.csv`
- `paper/ijgis_submission_20260605/07_results/geofm_balance_diagnostics.csv`

**Acceptance criteria:**

- If GeoFM variants improve balance, reduce sensitivity to observed confounders, or stabilize ATT compared with conventional covariates, the manuscript can retain bounded GeoFM claims.
- If GeoFM is unavailable or does not improve diagnostics, keep the manuscript framed as spatial-context augmentation, not GeoFM validation.

## Experiment 5: LLM DAG Validation

**Purpose:** Show that Angle B is more than illustrative text generation.

**What to do:**

1. Create 20 to 30 causal prompts from:
   - the six synthetic scenarios
   - the Chongqing UHI case
   - published spatial causal examples from the related work
2. Define reference DAGs manually from the generator equations or domain literature.
3. Run each LLM prompt five times at the stated low temperature.
4. Compute:
   - edge precision
   - edge recall
   - F1
   - structural Hamming distance
   - Jaccard stability across runs
5. Compare against a simple template baseline, for example a prompt without domain templates.

**Output files:**

- `paper/ijgis_submission_20260605/07_results/llm_dag_validation.csv`
- `paper/ijgis_submission_20260605/07_results/llm_dag_examples.md`

**Acceptance criteria:**

- Report accuracy against reference DAGs, not only self-consistency.
- If accuracy is weak, present Angle B as interpretive support rather than evidence.

## Experiment 6: World Model Scenario Validation

**Purpose:** Clarify whether Angle C is predictive simulation, calibrated scenario analysis, or causal inference.

**Files to start from:**

- `data_agent/experiments/run_world_model.py`
- `data_agent/world_model.py`
- `data_agent/causal_world_model.py`

**What to do:**

1. Use held-out years for one-step and multi-step prediction.
2. Compare against:
   - persistence baseline
   - Markov transition baseline
   - simple regression or random forest transition model
3. Report embedding-space error and decoded land-cover accuracy if decoding is available.
4. For scenario calibration, show how ATT scaling changes predictions and whether the calibrated predictions remain plausible.

**Output files:**

- `paper/ijgis_submission_20260605/07_results/world_model_holdout_metrics.csv`
- `paper/ijgis_submission_20260605/07_results/world_model_scenario_calibration.csv`

**Acceptance criteria:**

- Angle C should be described as scenario simulation unless there is held-out predictive validation plus a clear causal identification argument.

## Manuscript Changes After Experiments

After these experiments are complete:

1. Replace the current synthetic summary table with the multi-seed benchmark table.
2. Replace the Chongqing results paragraph with the ablation and robustness table.
3. Add one main-table row for GeoFM ablation only if Experiment 4 succeeds.
4. Move weak or illustrative LLM/world-model examples to supplementary material unless Experiments 5 and 6 support stronger claims.
5. Keep the title and abstract bounded around spatial-context-augmented causal inference.
