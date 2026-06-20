# SCCA Manuscript Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild Paper 6 from a three-angle concept paper into a SCCA method paper with a unified evidence synthesis experiment.

**Architecture:** Add one focused experiment module that reads existing result artifacts and emits a normalized evidence matrix, report, and manifest. Then rewrite the manuscript and README so the paper's claims follow that evidence matrix rather than the abandoned three-angle framework.

**Tech Stack:** Python 3.11, pandas, pytest, LaTeX, existing `data_agent.experiments` result layout.

---

### File Structure

- Create: `data_agent/test_scca_evidence_synthesis.py`
  - Tests the evidence synthesis contract, evidence grades, and negative GeoFM framing.
- Create: `data_agent/experiments/scca_evidence_synthesis.py`
  - Loads existing CSV/JSON result artifacts and writes synthesis CSV, Markdown report, and manifest.
- Modify: `paper/ijgis_submission_20260605/01_manuscript/01_manuscript_ijgis.tex`
  - Rewrites the main manuscript around SCCA.
- Modify: `README.md`
  - Updates repository framing and quick-start command list.
- Create: `docs/superpowers/specs/2026-06-20-scca-manuscript-rebuild-design.md`
  - Records the strategic decision and acceptance criteria.
- Create: `docs/superpowers/plans/2026-06-20-scca-manuscript-rebuild-implementation.md`
  - Records this plan.

### Task 1: Evidence Synthesis Test

**Files:**
- Create: `data_agent/test_scca_evidence_synthesis.py`

- [ ] **Step 1: Write the failing test**

```python
import json

import pandas as pd


def test_scca_evidence_synthesis_writes_contract_files(tmp_path):
    from data_agent.experiments.scca_evidence_synthesis import (
        run_scca_evidence_synthesis,
    )

    manifest = run_scca_evidence_synthesis(output_dir=tmp_path)

    expected = {
        "synthesis_csv": tmp_path / "scca_evidence_synthesis.csv",
        "report_md": tmp_path / "scca_evidence_synthesis_report.md",
        "manifest_json": tmp_path / "scca_evidence_synthesis_manifest.json",
    }
    for key, path in expected.items():
        assert manifest[key] == str(path)
        assert path.exists()

    synthesis = pd.read_csv(expected["synthesis_csv"])
    required_columns = {
        "case",
        "data_type",
        "exposure",
        "outcome",
        "context_source",
        "best_adjustment",
        "effect_estimate",
        "balance_status",
        "robustness_status",
        "evidence_grade",
        "limitation",
        "manuscript_use",
    }
    assert required_columns.issubset(synthesis.columns)
    assert {"chongqing_uhi", "geofm_alphaearth_ablation", "snow8", "soho", "county_social_capital"}.issubset(set(synthesis["case"]))
    assert "negative_ablation" in set(synthesis["evidence_grade"])
    assert synthesis.loc[synthesis["case"] == "geofm_alphaearth_ablation", "manuscript_use"].str.contains("no clear gain").any()

    payload = json.loads(expected["manifest_json"].read_text(encoding="utf-8"))
    assert payload["n_rows"] == len(synthesis)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_scca_evidence_synthesis.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'data_agent.experiments.scca_evidence_synthesis'`.

### Task 2: Evidence Synthesis Implementation

**Files:**
- Create: `data_agent/experiments/scca_evidence_synthesis.py`

- [ ] **Step 1: Implement the module**

Create functions:

```python
def build_scca_evidence_table(results_dir: str | Path = DEFAULT_RESULTS_DIR) -> pd.DataFrame:
    ...

def render_scca_evidence_report(table: pd.DataFrame) -> str:
    ...

def run_scca_evidence_synthesis(output_dir: str | Path = DEFAULT_RESULTS_DIR, results_dir: str | Path = DEFAULT_RESULTS_DIR) -> dict[str, object]:
    ...
```

The table must include rows for synthetic benchmark audit, Chongqing UHI, GeoFM AlphaEarth ablation, Snow8, Soho, county social capital, LLM DAG validation, and world-model holdout validation when their source files exist.

- [ ] **Step 2: Run test to verify it passes**

Run: `D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_scca_evidence_synthesis.py -q`

Expected: PASS.

- [ ] **Step 3: Generate the main output files**

Run: `D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.scca_evidence_synthesis --output-dir paper\ijgis_submission_20260605\07_results`

Expected files:

- `paper/ijgis_submission_20260605/07_results/scca_evidence_synthesis.csv`
- `paper/ijgis_submission_20260605/07_results/scca_evidence_synthesis_report.md`
- `paper/ijgis_submission_20260605/07_results/scca_evidence_synthesis_manifest.json`

### Task 3: Manuscript Rebuild

**Files:**
- Modify: `paper/ijgis_submission_20260605/01_manuscript/01_manuscript_ijgis.tex`

- [ ] **Step 1: Replace the old framing**

Replace the title, abstract, keywords, introduction, architecture section, angle sections, results, discussion, conclusion, and data/code availability with a SCCA-centered manuscript.

Required title:

```latex
\title{Spatial Context Causal Adjustment for Geographic Observational Studies}
```

Required contribution logic:

```latex
\begin{enumerate}
\item A formal SCCA workflow for representing, selecting, and diagnosing spatial-context adjustment sets.
\item A reproducible diagnostic protocol covering common support, balance, spatial robustness, placebo checks, and evidence grading.
\item Cross-case evidence from synthetic benchmarks, Chongqing UHI, Snow cholera, Soho pump, and county social-capital analyses.
\item A bounded GeoFM ablation showing that AlphaEarth embeddings are a candidate context source but did not improve balance in the current case.
\end{enumerate}
```

- [ ] **Step 2: Remove unsupported main claims**

Run: `rg -n "Three-Angle|three-angle|Angle~|Angle A|Angle B|Angle C|World Model|world-model|LLM" paper\ijgis_submission_20260605\01_manuscript\01_manuscript_ijgis.tex`

Expected: no "three-angle" or "Angle" main-framework claims; any LLM/world-model mention must be explicitly auxiliary or limitation-only.

### Task 4: README Update

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update top-level framing**

Replace the old three-angle repository description with:

```markdown
**Spatial Context Causal Adjustment (SCCA) for geographic observational studies: a reproducible workflow for constructing spatial-context adjustment sets, checking balance and common support, running spatial robustness diagnostics, and reporting bounded causal evidence.**
```

Add the evidence synthesis command:

```powershell
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.scca_evidence_synthesis --output-dir paper\ijgis_submission_20260605\07_results
```

### Task 5: Verification

**Files:**
- All changed files.

- [ ] **Step 1: Run focused test**

Run: `D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_scca_evidence_synthesis.py -q`

Expected: PASS.

- [ ] **Step 2: Run related regression tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_scca_robustness.py data_agent\test_scca_snow8.py data_agent\test_scca_soho.py data_agent\test_scca_county_social_capital.py data_agent\test_chongqing_uhi_analysis.py data_agent\test_geofm_alphaearth_ablation.py data_agent\test_synthetic_benchmark_audit.py data_agent\test_synthetic_multiseed_benchmark.py -q
```

Expected: PASS.

- [ ] **Step 3: Compile manuscript**

Run from `paper/ijgis_submission_20260605/01_manuscript`:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=..\06_build 01_manuscript_ijgis.tex
```

Expected: exit code 0 and updated PDF in `paper/ijgis_submission_20260605/06_build/`.

- [ ] **Step 4: Check claim hygiene**

Run:

```powershell
rg -n "Three-Angle|three-angle|Angle~|Angle A|Angle B|Angle C|revolutionary|unprecedented|definitive validation|GeoFM.*improve" paper\ijgis_submission_20260605\01_manuscript\01_manuscript_ijgis.tex README.md
```

Expected: no unsupported claims.
