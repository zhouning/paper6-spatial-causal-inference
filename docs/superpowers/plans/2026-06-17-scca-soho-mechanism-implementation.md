# SCCA Soho Mechanism Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible SCCA mechanism experiment for the Soho Broad Street pump data.

**Architecture:** Reuse the existing SCCA modules and add a small Soho adapter that creates `bspump_proximity = -log1p(dis_bspump)`. Add a Soho study spec, runner, tests, README command, and generated results under `paper/ijgis_submission_20260605/07_results/scca_soho/`.

**Tech Stack:** Python 3.11+, pandas, numpy, statsmodels, scipy, scikit-learn, pytest.

---

## Task 1: Add Soho Study Spec and Preprocessor

**Files:**
- Modify: `data_agent/scca/specs.py`
- Create: `data_agent/experiments/run_scca_soho.py`
- Create: `data_agent/test_scca_soho.py`

- [ ] **Step 1: Write failing tests**

Create `data_agent/test_scca_soho.py`:

```python
from pathlib import Path

import pandas as pd

from data_agent.experiments.run_scca_soho import prepare_soho_table
from data_agent.scca.specs import StudySpec


def _soho_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ID": ["1", "2", "3", "4"],
            "deaths": [0, 1, 2, 0],
            "death_dum": [0, 1, 1, 0],
            "dis_bspump": [120.0, 80.0, 20.0, 200.0],
            "dis_pestf": [10.0, 15.0, 30.0, 80.0],
            "dis_sewers": [12.0, 14.0, 22.0, 90.0],
            "pestfield": [1, 1, 0, 0],
            "COORD_X": [529286.0, 529290.0, 529350.0, 529500.0],
            "COORD_Y": [181084.0, 181080.0, 181030.0, 180980.0],
        }
    )


def test_soho_study_spec_defaults():
    spec = StudySpec.soho_default()
    assert spec.name == "soho_broad_street_pump_mechanism"
    assert spec.unit_id == "ID"
    assert spec.exposure == "bspump_proximity"
    assert spec.outcome == "deaths"
    assert "dis_pestf" in spec.confounders
    assert "COORD_X" in spec.context_columns


def test_prepare_soho_table_creates_bspump_proximity():
    prepared = prepare_soho_table(_soho_fixture())
    assert "bspump_proximity" in prepared.columns
    assert prepared.loc[2, "bspump_proximity"] > prepared.loc[0, "bspump_proximity"]
    assert prepared["deaths"].dtype.kind in {"f", "i"}
```

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_soho.py -q
```

Expected: import failure because `run_scca_soho` and `StudySpec.soho_default` do not exist.

- [ ] **Step 2: Implement the minimal spec and preprocessor**

Add to `StudySpec` in `data_agent/scca/specs.py`:

```python
    @classmethod
    def soho_default(cls) -> "StudySpec":
        return cls(
            name="soho_broad_street_pump_mechanism",
            unit_id="ID",
            exposure="bspump_proximity",
            outcome="deaths",
            baseline_outcome=None,
            population=None,
            confounders=("dis_pestf", "dis_sewers", "pestfield"),
            context_columns=("COORD_X", "COORD_Y"),
            coordinate_columns=("COORD_X", "COORD_Y"),
            subgroup_column=None,
        )
```

Create the first part of `data_agent/experiments/run_scca_soho.py`:

```python
from __future__ import annotations

import numpy as np
import pandas as pd


NUMERIC_COLUMNS = (
    "deaths",
    "death_dum",
    "dis_bspump",
    "dis_pestf",
    "dis_sewers",
    "pestfield",
    "COORD_X",
    "COORD_Y",
)


def prepare_soho_table(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    for column in NUMERIC_COLUMNS:
        if column in prepared.columns:
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    prepared["bspump_proximity"] = -np.log1p(prepared["dis_bspump"])
    return prepared
```

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_soho.py -q
```

Expected: `2 passed`.

Commit:

```powershell
git add data_agent/scca/specs.py data_agent/experiments/run_scca_soho.py data_agent/test_scca_soho.py
git commit -m "Add SCCA Soho study preprocessing"
```

## Task 2: Add End-to-End Soho Runner

**Files:**
- Modify: `data_agent/experiments/run_scca_soho.py`
- Modify: `data_agent/test_scca_soho.py`

- [ ] **Step 1: Write failing runner tests**

Append:

```python
from data_agent.experiments.run_scca_soho import run_soho_scca


def test_run_soho_scca_end_to_end_on_fixture(tmp_path):
    csv_path = tmp_path / "soho_fixture.csv"
    _soho_fixture().to_csv(csv_path, index=False)
    output_dir = tmp_path / "outputs"
    manifest = run_soho_scca(csv_path=csv_path, output_dir=output_dir)
    assert manifest["decision"] in {"strong_support", "moderate_support", "weak_or_failed_support"}
    assert manifest["metadata"]["input_rows"] == 4
    assert manifest["metadata"]["source_sha256"]
    for file_name in manifest["files"].values():
        assert (output_dir / file_name).exists()
```

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_soho.py -q
```

Expected: import failure for `run_soho_scca`.

- [ ] **Step 2: Implement runner**

Extend `data_agent/experiments/run_scca_soho.py` with a runner mirroring `run_scca_snow8.py`, using `StudySpec.soho_default()`, `prepare_soho_table`, and output directory `paper/ijgis_submission_20260605/07_results/scca_soho`.

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_soho.py -q
```

Expected: `3 passed`.

Commit:

```powershell
git add data_agent/experiments/run_scca_soho.py data_agent/test_scca_soho.py
git commit -m "Add SCCA Soho experiment runner"
```

## Task 3: Run Real Soho Experiment and Document Command

**Files:**
- Modify: `README.md`
- Create outputs under `paper/ijgis_submission_20260605/07_results/scca_soho/`

- [ ] **Step 1: Run the real experiment**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.run_scca_soho --csv-path "D:\北大MEM\01-课程学习\02-技术核心课\数据可视化技术及应用\snow\snow1\deaths_nd_by_house.csv"
```

Expected: manifest JSON with allowed `decision`.

- [ ] **Step 2: Add README command**

Add after the snow8 SCCA command:

```markdown
Run the Soho Broad Street pump SCCA mechanism experiment:

```powershell
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.run_scca_soho --csv-path "D:\北大MEM\01-课程学习\02-技术核心课\数据可视化技术及应用\snow\snow1\deaths_nd_by_house.csv"
```

The outputs are written to `paper/ijgis_submission_20260605/07_results/scca_soho/`.
```

- [ ] **Step 3: Verify**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_soho.py data_agent/test_scca_snow8.py -q
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_causal_inference.py -q
```

Expected: all SCCA tests pass, existing causal tests pass with the known deprecation warning.

Commit:

```powershell
git add README.md paper/ijgis_submission_20260605/07_results/scca_soho
git commit -m "Add SCCA Soho experiment outputs"
```

## Acceptance Criteria

- `data_agent/test_scca_soho.py` passes.
- `data_agent/test_scca_snow8.py` still passes.
- `data_agent/test_causal_inference.py` still passes with the known deprecation warning.
- Real Soho output manifest exists and records the actual decision and provenance.
- Final response reports the actual Soho decision and key reasons without editing the manuscript.
