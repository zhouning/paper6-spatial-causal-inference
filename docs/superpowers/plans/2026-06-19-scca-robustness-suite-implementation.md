# SCCA Robustness Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a reproducible robustness suite for the existing Snow8, Soho, and county SCCA case studies, producing ablation, placebo, bootstrap, ERF-stability, case-report, and cross-case summary artifacts.

**Architecture:** Add one reusable robustness module under `data_agent/scca/robustness.py`, then add thin case-specific robustness runners that load the same data and study specs as the original SCCA runners. The original SCCA outputs remain intact; robustness outputs are additive and written beside each case's existing result files, with a separate consolidated summary directory.

**Tech Stack:** Python 3.11+, pandas, numpy, statsmodels, pytest, existing SCCA modules and runners.

---

## Files

- Create `data_agent/scca/robustness.py`
  - Generic OLS fit helper, context ablation, placebo tests, grouped/grid bootstrap, ERF stability summary, robustness report/manifest, and cross-case summary helpers.
- Create `data_agent/test_scca_robustness.py`
  - Unit tests for all generic robustness helpers and fixture-level report writing.
- Create `data_agent/experiments/run_scca_snow8_robustness.py`
  - Load Snow8 CSV, build features, run Snow8 robustness suite.
- Create `data_agent/experiments/run_scca_soho_robustness.py`
  - Load Soho CSV, create proximity columns, build features, run Soho robustness suite.
- Create `data_agent/experiments/run_scca_county_social_capital_robustness.py`
  - Load county workbook, build features, run county robustness suite.
- Create `data_agent/experiments/run_scca_robustness_summary.py`
  - Read the three case manifests and write cross-case CSV/Markdown summary.
- Modify `README.md`
  - Add robustness reproduction commands.
- Generate robustness outputs under:
  - `paper/ijgis_submission_20260605/07_results/scca_snow8/`
  - `paper/ijgis_submission_20260605/07_results/scca_soho/`
  - `paper/ijgis_submission_20260605/07_results/scca_county_social_capital/`
  - `paper/ijgis_submission_20260605/07_results/scca_robustness_summary/`

## Baseline Verification

- [ ] Run:

```powershell
git status -sb
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_county_social_capital.py data_agent/test_scca_soho.py data_agent/test_scca_snow8.py -q
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_causal_inference.py -q
```

Expected:

- Worktree is clean except plan commit state.
- Existing SCCA tests pass.
- Existing causal tests pass with the known event-loop warning.

## Task 1: Core Robustness Helpers

**Files:**
- Create `data_agent/test_scca_robustness.py`
- Create `data_agent/scca/robustness.py`

- [ ] Write failing tests for:
  - `run_context_ablation`
  - `run_placebo_tests`
  - `summarize_bootstrap`
  - `summarize_erf_stability`
  - `write_robustness_outputs`

The fixture should use a small continuous-exposure frame with columns:

- `unit_id`
- `group`
- `x`
- `y`
- `baseline`
- `confounder`
- `context`
- `placebo`
- `outcome`

Assertions:

- Context ablation includes `exposure_only`, `confounders_only`, `context_only`, and `confounders_plus_context`.
- Placebo tests include the configured placebo exposure and leave the input frame unchanged.
- Bootstrap summary reports requested/valid counts and sign stability.
- ERF summary detects an increasing curve as `increasing`.
- Report writer creates `context_ablation.csv`, `placebo_tests.csv`, `bootstrap_robustness.csv`, `bootstrap_summary.json`, `erf_stability.json`, `robustness_report.md`, and `robustness_manifest.json`.

- [ ] Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_robustness.py -q
```

Expected RED:

```text
ModuleNotFoundError: No module named 'data_agent.scca.robustness'
```

- [ ] Implement `data_agent/scca/robustness.py` with:
  - `fit_ols_effect(frame, outcome, exposure, columns) -> dict[str, object]`
  - `run_context_ablation(features, spec, case_name) -> pd.DataFrame`
  - `run_placebo_tests(features, spec, case_name, tests) -> pd.DataFrame`
  - `make_quantile_grid_groups(features, x_col, y_col, bins=4) -> pd.Series`
  - `run_group_bootstrap(features, spec, case_name, group_column, n_replicates=200, random_state=0) -> tuple[pd.DataFrame, dict[str, object]]`
  - `summarize_bootstrap(rows, case_name, bootstrap_type, n_replicates_requested) -> dict[str, object]`
  - `summarize_erf_stability(erf_curve, case_name) -> dict[str, object]`
  - `classify_robustness(original_decision, ablation, placebo, bootstrap_summary, erf_summary, main_limitation) -> dict[str, object]`
  - `write_robustness_outputs(output_dir, case_name, original_decision, main_coef, main_limitation, ablation, placebo, bootstrap_rows, bootstrap_summary, erf_summary) -> dict[str, object]`
  - `write_cross_case_summary(case_manifests, output_dir) -> dict[str, object]`

- [ ] Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_robustness.py -q
```

Expected GREEN:

```text
all tests in data_agent/test_scca_robustness.py pass
```

- [ ] Commit:

```powershell
git add data_agent/scca/robustness.py data_agent/test_scca_robustness.py
git commit -m "Add SCCA robustness helpers"
```

## Task 2: Case Robustness Runners

**Files:**
- Create `data_agent/experiments/run_scca_snow8_robustness.py`
- Create `data_agent/experiments/run_scca_soho_robustness.py`
- Create `data_agent/experiments/run_scca_county_social_capital_robustness.py`
- Modify `data_agent/test_scca_robustness.py`

- [ ] Add failing tests for fixture-level case runners:
  - Snow8 fixture run writes `robustness_manifest.json`.
  - Soho fixture run writes `robustness_manifest.json`.
  - County fixture run writes `robustness_manifest.json`.

- [ ] Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_robustness.py -q
```

Expected RED:

```text
ModuleNotFoundError or ImportError for the new runner functions
```

- [ ] Implement runners:
  - `run_snow8_robustness(csv_path, output_dir=...)`
  - `run_soho_robustness(csv_path, output_dir=...)`
  - `run_county_social_capital_robustness(workbook_path, output_dir=..., sheet_name="CountyData")`

Each runner should:

1. Load and preprocess the case data.
2. Build context features with the existing study spec.
3. Read original `credibility_report.json` and `effect_estimates.csv` when present.
4. Run context ablation.
5. Run case-specific placebo tests.
6. Run case-specific bootstrap:
   - Snow8: `district`
   - Soho: generated coordinate-grid block column
   - County: `STATE_NAME`
7. Read existing `erf_curve.csv` and summarize ERF stability.
8. Write robustness outputs and return the parsed manifest.

- [ ] Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_robustness.py -q
```

Expected GREEN:

```text
all robustness tests pass
```

- [ ] Commit:

```powershell
git add data_agent/experiments/run_scca_snow8_robustness.py data_agent/experiments/run_scca_soho_robustness.py data_agent/experiments/run_scca_county_social_capital_robustness.py data_agent/test_scca_robustness.py
git commit -m "Add SCCA case robustness runners"
```

## Task 3: Cross-Case Summary Runner

**Files:**
- Create `data_agent/experiments/run_scca_robustness_summary.py`
- Modify `data_agent/test_scca_robustness.py`

- [ ] Add a failing test that writes three small robustness manifests into temp directories and verifies `run_robustness_summary` creates:
  - `case_robustness_summary.csv`
  - `case_robustness_report.md`

- [ ] Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_robustness.py -q
```

Expected RED:

```text
ImportError for run_robustness_summary
```

- [ ] Implement `run_robustness_summary(output_dir=...)`:
  - default input manifests from the three case output directories,
  - write consolidated summary directory,
  - print JSON manifest from CLI.

- [ ] Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_robustness.py -q
```

Expected GREEN:

```text
all robustness tests pass
```

- [ ] Commit:

```powershell
git add data_agent/experiments/run_scca_robustness_summary.py data_agent/test_scca_robustness.py
git commit -m "Add SCCA robustness summary runner"
```

## Task 4: Generate Real Robustness Outputs and Document Commands

**Files:**
- Modify `README.md`
- Generate outputs in the three case directories and summary directory.

- [ ] Run real robustness commands:

```powershell
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.run_scca_snow8_robustness --csv-path "D:\北大MEM\01-课程学习\02-技术核心课\数据可视化技术及应用\snow\snow8\subdistricts.csv"
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.run_scca_soho_robustness --csv-path "D:\北大MEM\01-课程学习\02-技术核心课\数据可视化技术及应用\snow\snow1\deaths_nd_by_house.csv"
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.run_scca_county_social_capital_robustness --workbook-path "D:\北大MEM\01-课程学习\02-技术核心课\数据可视化技术及应用\CausalInferAnalysis\CausalInferAnalysis\CountyData_TableToExcel.xlsx"
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.run_scca_robustness_summary
```

- [ ] Inspect:

```powershell
Get-Content -Raw paper\ijgis_submission_20260605\07_results\scca_snow8\robustness_manifest.json
Get-Content -Raw paper\ijgis_submission_20260605\07_results\scca_soho\robustness_manifest.json
Get-Content -Raw paper\ijgis_submission_20260605\07_results\scca_county_social_capital\robustness_manifest.json
Get-Content -Raw paper\ijgis_submission_20260605\07_results\scca_robustness_summary\case_robustness_report.md
```

- [ ] Update README with the four robustness commands.

- [ ] Verify:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_robustness.py data_agent/test_scca_county_social_capital.py data_agent/test_scca_soho.py data_agent/test_scca_snow8.py -q
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_causal_inference.py -q
```

- [ ] Commit:

```powershell
git add README.md paper/ijgis_submission_20260605/07_results/scca_snow8 paper/ijgis_submission_20260605/07_results/scca_soho paper/ijgis_submission_20260605/07_results/scca_county_social_capital paper/ijgis_submission_20260605/07_results/scca_robustness_summary
git commit -m "Add SCCA robustness outputs"
```

## Final Step

- [ ] Run:

```powershell
git status -sb
git log -1 --oneline --decorate
git push origin main
git status -sb
```

- [ ] Final response must report:
  - final commit,
  - pushed sync status,
  - test commands and pass counts,
  - Snow8/Soho/County second-layer robustness interpretations,
  - key robustness numbers from `bootstrap_summary.json`, `placebo_tests.csv`, and `erf_stability.json`.

