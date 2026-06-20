# LLM DAG Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible DAG validation benchmark for Paper 6 Angle B.

**Architecture:** Build a focused experiment module with reference DAG cases, graph metrics, offline generators, optional live LLM generation, output writers, and a CLI.

**Tech Stack:** Python 3.11, pandas, numpy, pytest, optional Google GenAI for live runs.

---

### Task 1: Add failing tests for graph metrics and reference cases

**Files:**
- Create: `data_agent/test_llm_dag_validation.py`
- Create later: `data_agent/experiments/llm_dag_validation.py`

- [ ] **Step 1: Write the failing tests**

Test that:

- `score_dag_edges` reports exact precision, recall, F1, and SHD on a small
  graph with one true positive, one missing edge, one reversed edge, and one
  extra edge.
- `pairwise_jaccard_stability` returns the expected average over repeated
  predicted edge sets.
- `build_reference_cases()` returns at least 20 cases, and every case has an ID,
  prompt, exposure, outcome, and at least two reference edges.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_llm_dag_validation.py -q
```

Expected: fail because `data_agent.experiments.llm_dag_validation` does not
exist.

- [ ] **Step 3: Implement metrics and reference cases**

Implement:

- `DagCase`
- `build_reference_cases`
- `normalize_edge_set`
- `score_dag_edges`
- `pairwise_jaccard_stability`

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command.

### Task 2: Add failing tests for output contract

**Files:**
- Modify: `data_agent/test_llm_dag_validation.py`
- Modify: `data_agent/experiments/llm_dag_validation.py`

- [ ] **Step 1: Write the failing test**

Test `run_llm_dag_validation(output_dir=tmp_path, cases=first_three, n_repeats=2)`
and assert:

- required files exist,
- CSV contains `prompt_id`, `generator`, `run`, `edge_precision`,
  `edge_recall`, `edge_f1`, `structural_hamming_distance`, and
  `jaccard_stability`,
- Markdown examples include reference and generated DAG sections.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_llm_dag_validation.py -q
```

Expected: fail because runner/writer functions are missing.

- [ ] **Step 3: Implement runner and writers**

Implement:

- `minimal_template_baseline`
- `structured_prompt_proxy`
- `run_llm_dag_validation`
- `write_llm_dag_outputs`
- CLI `main`

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command.

### Task 3: Generate outputs and verify

**Files:**
- Create: `paper/ijgis_submission_20260605/07_results/llm_dag_validation.csv`
- Create: `paper/ijgis_submission_20260605/07_results/llm_dag_examples.md`
- Create: `paper/ijgis_submission_20260605/07_results/llm_dag_validation_manifest.json`
- Create: `paper/ijgis_submission_20260605/07_results/llm_dag_validation_details.json`

- [ ] **Step 1: Run focused tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_llm_dag_validation.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run offline validation**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.llm_dag_validation --output-dir paper\ijgis_submission_20260605\07_results --n-repeats 5
```

Expected: validation CSV and examples Markdown are written.

- [ ] **Step 3: Run regression tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_llm_dag_validation.py data_agent\test_llm_causal.py -q
```

Expected: all tests pass, with any existing asyncio warning noted.

- [ ] **Step 4: Commit**

Run:

```powershell
git add data_agent/experiments/llm_dag_validation.py data_agent/test_llm_dag_validation.py docs/superpowers/specs/2026-06-20-llm-dag-validation-design.md docs/superpowers/plans/2026-06-20-llm-dag-validation-implementation.md paper/ijgis_submission_20260605/07_results/llm_dag_*
git commit -m "Add LLM DAG validation benchmark"
```
