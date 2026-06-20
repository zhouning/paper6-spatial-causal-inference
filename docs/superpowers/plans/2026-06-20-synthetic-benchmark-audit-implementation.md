# Synthetic Benchmark Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a second-layer synthetic benchmark audit for all six Paper 6 estimators, run it end to end, and write reproducible audit artifacts without replacing the existing multi-seed benchmark outputs.

**Architecture:** Add a new `data_agent.experiments.synthetic_benchmark_audit` module that defines stress settings, reuses current synthetic estimators where practical, aggregates seed-level outputs into fragility summaries, and renders a Markdown audit report. Keep `synthetic_multiseed.py` as the baseline contract and wire the new audit through `run_causal.py`.

**Tech Stack:** Python 3.11, pandas, numpy, statsmodels, existing Paper 6 estimator functions, pytest.

---

### Task 1: Add failing tests for the audit output contract

**Files:**
- Create: `data_agent/test_synthetic_benchmark_audit.py`
- Test: `data_agent/test_synthetic_benchmark_audit.py`

- [ ] **Step 1: Write the failing test**

Add tests that call a new `run_synthetic_benchmark_audit()` function with small
seed lists and assert that it writes:

- `synthetic_benchmark_audit_summary.csv`
- `synthetic_benchmark_audit_details.json`
- `synthetic_benchmark_audit_manifest.json`
- `synthetic_benchmark_audit_report.md`
- `scenario_fragility_summary.csv`

Also assert that the summary contains `setting`, `stress_level`, `fragility`,
and `fragility_reason`.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_synthetic_benchmark_audit.py -q
```

Expected: fail because the module and runner do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create a placeholder audit module and minimal manifest-writing code.

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command and confirm the output is green.

- [ ] **Step 5: Commit**

```powershell
git add data_agent/test_synthetic_benchmark_audit.py data_agent/experiments/synthetic_benchmark_audit.py
git commit -m "Add synthetic benchmark audit output contract"
```

### Task 2: Implement stress settings and audit aggregation

**Files:**
- Modify: `data_agent/experiments/synthetic_benchmark_audit.py`
- Test: `data_agent/test_synthetic_benchmark_audit.py`

- [ ] **Step 1: Write the failing test**

Add tests that assert:

- the audit writes multiple settings per scenario,
- `PSM` and `GCCM` include multiple variants,
- `scenario_fragility_summary.csv` contains per-scenario aggregate counts.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_synthetic_benchmark_audit.py -q
```

Expected: fail because settings and aggregation are incomplete.

- [ ] **Step 3: Write minimal implementation**

Implement:

- setting definitions,
- seed-level execution,
- summary aggregation,
- fragility classification,
- scenario-level aggregate summary.

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command and confirm it passes.

- [ ] **Step 5: Commit**

```powershell
git add data_agent/test_synthetic_benchmark_audit.py data_agent/experiments/synthetic_benchmark_audit.py
git commit -m "Add synthetic benchmark audit aggregation"
```

### Task 3: Wire the audit into the experiment CLI

**Files:**
- Modify: `data_agent/experiments/run_causal.py`
- Test: `data_agent/test_synthetic_benchmark_audit.py`

- [ ] **Step 1: Write the failing test**

Add a test that exercises the audit module entry point directly or validates the
manifest paths expected by the CLI-facing defaults.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_synthetic_benchmark_audit.py -q
```

Expected: fail because the CLI path/default wiring is missing.

- [ ] **Step 3: Write minimal implementation**

Update `run_causal.py` with a `--synthetic-audit-only` entry that runs the new
audit without changing the existing synthetic benchmark commands.

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command and confirm it passes.

- [ ] **Step 5: Commit**

```powershell
git add data_agent/experiments/run_causal.py data_agent/test_synthetic_benchmark_audit.py
git commit -m "Add CLI entry for synthetic benchmark audit"
```

### Task 4: Run regression tests and generate full audit artifacts

**Files:**
- Modify: `paper/ijgis_submission_20260605/07_results/synthetic_benchmark_audit/*`

- [ ] **Step 1: Run focused regression tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_synthetic_multiseed_benchmark.py data_agent\test_synthetic_benchmark_audit.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run the full audit**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.run_causal --synthetic-audit-only --n-seeds 20
```

Expected: the audit output directory contains the required CSV/JSON/Markdown files.

- [ ] **Step 3: Run final verification**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_synthetic_multiseed_benchmark.py data_agent\test_synthetic_benchmark_audit.py -q
```

Expected: all tests pass after the full audit run.

- [ ] **Step 4: Commit**

```powershell
git add data_agent/experiments/synthetic_benchmark_audit.py data_agent/experiments/run_causal.py data_agent/test_synthetic_benchmark_audit.py paper/ijgis_submission_20260605/07_results/synthetic_benchmark_audit docs/superpowers/specs/2026-06-20-synthetic-benchmark-audit-design.md docs/superpowers/plans/2026-06-20-synthetic-benchmark-audit-implementation.md
git commit -m "Add synthetic benchmark audit suite"
```
