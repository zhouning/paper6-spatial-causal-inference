# SCCA County Social-Capital Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible SCCA county social-capital validation experiment with tests, provenance, generated outputs, and README reproduction instructions.

**Architecture:** Reuse the existing `data_agent.scca` pipeline and add a small county-specific adapter. The adapter loads the `CountyData` Excel sheet, coerces configured numeric columns, preserves state/county identifiers, runs profile/context/design/estimation/audit/reporting, and writes outputs under `paper/ijgis_submission_20260605/07_results/scca_county_social_capital/`.

**Tech Stack:** Python 3.11+, pandas, numpy, statsmodels, scipy, scikit-learn, openpyxl, pytest, Git.

---

## File Structure

- Modify `data_agent/scca/specs.py`
  - Add `StudySpec.county_social_capital_default()` with explicit county variable roles.
- Create `data_agent/experiments/run_scca_county_social_capital.py`
  - County workbook loader/preprocessor.
  - End-to-end runner.
  - CLI entry point.
  - Git provenance helpers following the Soho runner pattern.
- Create `data_agent/test_scca_county_social_capital.py`
  - Spec defaults test.
  - Preprocessor behavior test.
  - End-to-end fixture test.
  - CLI JSON output test.
  - Git dirty ignore tests.
- Modify `README.md`
  - Add the county social-capital reproduction command after existing SCCA commands.
- Generate `paper/ijgis_submission_20260605/07_results/scca_county_social_capital/`
  - SCCA output contract files from the real workbook run.

## Baseline Commands

Run before implementation:

```powershell
git status -sb
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_soho.py data_agent/test_scca_snow8.py -q
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_causal_inference.py -q
```

Expected current results:

- Git status should show the local branch ahead only by planning/spec commits and no unstaged changes.
- SCCA tests should pass.
- Causal inference tests should pass with the known deprecation warning.

## Task 1: Add County Spec and Preprocessor

**Files:**
- Modify: `data_agent/scca/specs.py`
- Create: `data_agent/experiments/run_scca_county_social_capital.py`
- Create: `data_agent/test_scca_county_social_capital.py`

- [ ] **Step 1: Write the failing tests**

Create `data_agent/test_scca_county_social_capital.py`:

```python
import json
import subprocess

import pandas as pd

from data_agent.experiments.run_scca_county_social_capital import (
    DEFAULT_OUTPUT_DIR,
    PROJECT_ROOT,
    _git_dirty,
    _run_git,
    prepare_county_social_capital_table,
)
from data_agent.scca.specs import StudySpec


def _county_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "OBJECTID": [1, 2, 3, 4, 5, 6],
            "STATE_NAME": ["Alpha", "Alpha", "Beta", "Beta", "Gamma", "Gamma"],
            "CountyCode": [1001, 1003, 2001, 2003, 3001, 3003],
            "County": [
                "A County, AA",
                "B County, AA",
                "C County, BB",
                "D County, BB",
                "E County, CC",
                "F County, CC",
            ],
            "FIPS": [1001, 1003, 2001, 2003, 3001, 3003],
            "AveAgeDeath": [70.2, 72.7, 71.8, 73.1, 69.5, 74.0],
            "SocialAssoc": [12.6, 10.7, 8.5, 14.0, 7.2, 15.3],
            "UnemployRate": [3.8, 3.2, 7.9, 4.4, 6.1, 3.9],
            "pHHinPoverty": [13.25, 12.1, 25.78, 11.2, 18.4, 9.8],
            "pNoHealthInsur": [8.8, 10.9, 12.4, 7.3, 11.1, 6.9],
            "MentalHealth": [4.3, 4.2, 4.6, 4.0, 4.8, 3.9],
            "pAdultSmoking": [19.1, 16.8, 21.5, 15.0, 22.1, 14.2],
            "pAdultObesity": [37.5, 31.0, 44.3, 28.4, 39.1, 27.9],
            "FastFood": [3.47, 2.90, 2.71, 3.80, 2.50, 4.10],
            "pInsufficientSleep": [35.9, 33.3, 38.6, 31.0, 39.4, 30.5],
            "pAlcohol": [4.9, 8.8, 5.2, 9.0, 4.2, 10.1],
            "pSuicideDeaths": [16.8, 17.7, 10.8, 14.2, 12.4, 15.6],
            "AirPollution": [11.7, 10.3, 11.5, 8.8, 9.6, 7.9],
            "Shape_Length": [192945.1, 380525.4, 226532.8, 210000.0, 260000.0, 240000.0],
            "Shape_Area": [1.55e9, 4.31e9, 2.33e9, 1.80e9, 2.10e9, 1.70e9],
        }
    )


def test_county_social_capital_study_spec_defaults():
    spec = StudySpec.county_social_capital_default()
    assert spec.name == "county_social_capital_longevity_validation"
    assert spec.unit_id == "FIPS"
    assert spec.exposure == "SocialAssoc"
    assert spec.outcome == "AveAgeDeath"
    assert "pHHinPoverty" in spec.confounders
    assert "AirPollution" in spec.confounders
    assert spec.context_columns == ("Shape_Length", "Shape_Area")
    assert spec.subgroup_column == "STATE_NAME"


def test_prepare_county_social_capital_table_coerces_numeric_and_preserves_text():
    raw = _county_fixture()
    raw.loc[0, "SocialAssoc"] = "12.6"
    raw.loc[1, "FIPS"] = "1003"
    prepared = prepare_county_social_capital_table(raw)
    assert len(prepared) == len(raw)
    assert prepared["SocialAssoc"].dtype.kind in {"f", "i"}
    assert prepared["FIPS"].dtype.kind in {"f", "i"}
    assert prepared["STATE_NAME"].dtype == object
    assert prepared.loc[0, "STATE_NAME"] == "Alpha"
```

- [ ] **Step 2: Run tests and verify the expected RED failure**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_county_social_capital.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'data_agent.experiments.run_scca_county_social_capital'
```

- [ ] **Step 3: Implement the minimal county spec**

Add this classmethod to `StudySpec` in `data_agent/scca/specs.py`, after `soho_default()`:

```python
    @classmethod
    def county_social_capital_default(cls) -> "StudySpec":
        return cls(
            name="county_social_capital_longevity_validation",
            unit_id="FIPS",
            exposure="SocialAssoc",
            outcome="AveAgeDeath",
            baseline_outcome=None,
            population=None,
            confounders=(
                "UnemployRate",
                "pHHinPoverty",
                "pNoHealthInsur",
                "MentalHealth",
                "pAdultSmoking",
                "pAdultObesity",
                "FastFood",
                "pInsufficientSleep",
                "pAlcohol",
                "pSuicideDeaths",
                "AirPollution",
            ),
            context_columns=("Shape_Length", "Shape_Area"),
            coordinate_columns=None,
            subgroup_column="STATE_NAME",
        )
```

- [ ] **Step 4: Implement the minimal county preprocessor module**

Create `data_agent/experiments/run_scca_county_social_capital.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


NUMERIC_COLUMNS = (
    "OBJECTID",
    "CountyCode",
    "FIPS",
    "AveAgeDeath",
    "SocialAssoc",
    "UnemployRate",
    "pHHinPoverty",
    "pNoHealthInsur",
    "MentalHealth",
    "pAdultSmoking",
    "pAdultObesity",
    "FastFood",
    "pInsufficientSleep",
    "pAlcohol",
    "pSuicideDeaths",
    "AirPollution",
    "Shape_Length",
    "Shape_Area",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results" / "scca_county_social_capital"


def prepare_county_social_capital_table(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    for column in NUMERIC_COLUMNS:
        if column in prepared.columns:
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    for column in ("STATE_NAME", "County"):
        if column in prepared.columns:
            prepared[column] = prepared[column].astype(str)
    return prepared
```

- [ ] **Step 5: Run focused tests and verify GREEN**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_county_social_capital.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 6: Commit Task 1**

Run:

```powershell
git add data_agent/scca/specs.py data_agent/experiments/run_scca_county_social_capital.py data_agent/test_scca_county_social_capital.py
git commit -m "Add SCCA county social capital preprocessing"
```

## Task 2: Add End-to-End County Runner and CLI

**Files:**
- Modify: `data_agent/experiments/run_scca_county_social_capital.py`
- Modify: `data_agent/test_scca_county_social_capital.py`

- [ ] **Step 1: Add failing runner, CLI, and provenance tests**

Append to `data_agent/test_scca_county_social_capital.py`:

```python
from data_agent.experiments.run_scca_county_social_capital import run_county_social_capital_scca


def test_run_county_social_capital_scca_end_to_end_on_fixture(tmp_path):
    workbook_path = tmp_path / "county_fixture.xlsx"
    _county_fixture().to_excel(workbook_path, sheet_name="CountyData", index=False)
    output_dir = tmp_path / "outputs"
    manifest = run_county_social_capital_scca(workbook_path=workbook_path, output_dir=output_dir)
    assert manifest["study"] == "county_social_capital_longevity_validation"
    assert manifest["decision"] in {"strong_support", "moderate_support", "weak_or_failed_support"}
    assert manifest["metadata"]["sheet_name"] == "CountyData"
    assert manifest["metadata"]["input_rows"] == 6
    assert manifest["metadata"]["source_sha256"]
    for file_name in manifest["files"].values():
        assert (output_dir / file_name).exists()


def test_county_social_capital_cli_prints_manifest_json(tmp_path):
    workbook_path = tmp_path / "county_fixture.xlsx"
    _county_fixture().to_excel(workbook_path, sheet_name="CountyData", index=False)
    output_dir = tmp_path / "outputs"
    result = subprocess.run(
        [
            "D:\\adk\\.venv\\Scripts\\python.exe",
            "-m",
            "data_agent.experiments.run_scca_county_social_capital",
            "--workbook-path",
            str(workbook_path),
            "--output-dir",
            str(output_dir),
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads(result.stdout)
    assert manifest["study"] == "county_social_capital_longevity_validation"
    assert manifest["metadata"]["input_rows"] == 6


def test_county_git_runner_marks_worktree_safe(monkeypatch):
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

        class Result:
            stdout = "abc123\n"

        return Result()

    monkeypatch.setattr(
        "data_agent.experiments.run_scca_county_social_capital.subprocess.run",
        fake_run,
    )
    result = _run_git("rev-parse", "HEAD")
    assert result == "abc123"
    assert captured["args"] == [
        "git",
        "-c",
        f"safe.directory={PROJECT_ROOT.as_posix()}",
        "rev-parse",
        "HEAD",
    ]
    assert captured["kwargs"]["cwd"] == PROJECT_ROOT


def test_county_git_dirty_can_ignore_generated_output_dir(monkeypatch):
    monkeypatch.setattr(
        "data_agent.experiments.run_scca_county_social_capital._run_git",
        lambda *args: "\n".join(
            [
                "?? paper/ijgis_submission_20260605/07_results/scca_county_social_capital/manifest.json",
                "?? paper/ijgis_submission_20260605/07_results/scca_county_social_capital/effect_estimates.csv",
            ]
        ),
    )
    assert _git_dirty(ignored_paths=(DEFAULT_OUTPUT_DIR,)) is False


def test_county_git_dirty_reports_source_changes_outside_generated_output_dir(monkeypatch):
    monkeypatch.setattr(
        "data_agent.experiments.run_scca_county_social_capital._run_git",
        lambda *args: "\n".join(
            [
                " M data_agent/experiments/run_scca_county_social_capital.py",
                "?? paper/ijgis_submission_20260605/07_results/scca_county_social_capital/manifest.json",
            ]
        ),
    )
    assert _git_dirty(ignored_paths=(DEFAULT_OUTPUT_DIR,)) is True
```

- [ ] **Step 2: Run tests and verify the expected RED failure**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_county_social_capital.py -q
```

Expected:

```text
ImportError: cannot import name 'run_county_social_capital_scca'
```

- [ ] **Step 3: Implement the full runner**

Replace `data_agent/experiments/run_scca_county_social_capital.py` with:

```python
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from data_agent.scca.context import build_context_features
from data_agent.scca.design import select_design
from data_agent.scca.diagnostics import audit_effects
from data_agent.scca.estimators import estimate_effects
from data_agent.scca.profiling import profile_table
from data_agent.scca.reporting import write_report
from data_agent.scca.specs import SCCAPaths, StudySpec


NUMERIC_COLUMNS = (
    "OBJECTID",
    "CountyCode",
    "FIPS",
    "AveAgeDeath",
    "SocialAssoc",
    "UnemployRate",
    "pHHinPoverty",
    "pNoHealthInsur",
    "MentalHealth",
    "pAdultSmoking",
    "pAdultObesity",
    "FastFood",
    "pInsufficientSleep",
    "pAlcohol",
    "pSuicideDeaths",
    "AirPollution",
    "Shape_Length",
    "Shape_Area",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results" / "scca_county_social_capital"
DEFAULT_SHEET_NAME = "CountyData"


def prepare_county_social_capital_table(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    for column in NUMERIC_COLUMNS:
        if column in prepared.columns:
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    for column in ("STATE_NAME", "County"):
        if column in prepared.columns:
            prepared[column] = prepared[column].astype(str)
    return prepared


def load_county_social_capital_workbook(
    workbook_path: str | Path,
    sheet_name: str = DEFAULT_SHEET_NAME,
) -> pd.DataFrame:
    return pd.read_excel(workbook_path, sheet_name=sheet_name)


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={PROJECT_ROOT.as_posix()}", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _current_git_commit() -> str:
    try:
        commit = _run_git("rev-parse", "HEAD")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return commit or "unknown"


def _git_status_path(status_line: str) -> str:
    path = status_line[3:].strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1].strip()
    return path.replace("\\", "/")


def _relative_git_path(path: Path) -> str | None:
    try:
        relative = path.resolve().relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return None
    return relative.as_posix().rstrip("/") + "/"


def _git_dirty(ignored_paths: Iterable[Path] = ()) -> bool | None:
    try:
        status = _run_git("status", "--short")
    except (OSError, subprocess.CalledProcessError):
        return None
    ignored_prefixes = tuple(
        prefix for path in ignored_paths if (prefix := _relative_git_path(path)) is not None
    )
    for line in status.splitlines():
        git_path = _git_status_path(line)
        if ignored_prefixes and any(git_path.startswith(prefix) for prefix in ignored_prefixes):
            continue
        return True
    return False


def run_county_social_capital_scca(
    workbook_path: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    sheet_name: str = DEFAULT_SHEET_NAME,
) -> dict[str, object]:
    spec = StudySpec.county_social_capital_default()
    paths = SCCAPaths(output_dir=Path(output_dir))
    paths.ensure()
    source_path = Path(workbook_path)
    raw = load_county_social_capital_workbook(source_path, sheet_name=sheet_name)
    df = prepare_county_social_capital_table(raw)
    profile_table(df, spec, paths)
    features, _ = build_context_features(df, spec, paths)
    select_design(features, spec, paths)
    estimate_effects(features, spec, paths)
    credibility = audit_effects(features, spec, paths)
    metadata = {
        "source_workbook": str(source_path),
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "sheet_name": sheet_name,
        "command": (
            "run_county_social_capital_scca("
            f"workbook_path={source_path}, output_dir={paths.output_dir}, sheet_name={sheet_name})"
        ),
        "code_commit": _current_git_commit(),
        "code_commit_role": "source_commit_used_to_generate_outputs",
        "git_dirty": _git_dirty(ignored_paths=(paths.output_dir,)),
        "artifact_commit_note": (
            "The final artifact commit is represented by repository history and is not "
            "self-recorded in this manifest because doing so would be self-referential."
        ),
        "input_rows": int(raw.shape[0]),
        "input_columns": int(raw.shape[1]),
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    write_report(spec, paths, credibility, metadata=metadata)
    return json.loads(paths.manifest.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SCCA on the county social-capital dataset.")
    parser.add_argument("--workbook-path", required=True, help="Path to CountyData_TableToExcel.xlsx")
    parser.add_argument("--sheet-name", default=DEFAULT_SHEET_NAME, help="Workbook sheet name")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for SCCA outputs")
    args = parser.parse_args()
    manifest = run_county_social_capital_scca(args.workbook_path, args.output_dir, args.sheet_name)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_county_social_capital.py -q
```

Expected:

```text
7 passed
```

- [ ] **Step 5: Commit Task 2**

Run:

```powershell
git add data_agent/experiments/run_scca_county_social_capital.py data_agent/test_scca_county_social_capital.py
git commit -m "Add SCCA county social capital runner"
```

## Task 3: Run Real Workbook Experiment and Document Command

**Files:**
- Modify: `README.md`
- Create outputs under `paper/ijgis_submission_20260605/07_results/scca_county_social_capital/`

- [ ] **Step 1: Run the real workbook experiment**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.run_scca_county_social_capital --workbook-path "D:\北大MEM\01-课程学习\02-技术核心课\数据可视化技术及应用\CausalInferAnalysis\CausalInferAnalysis\CountyData_TableToExcel.xlsx"
```

Expected:

```text
Manifest JSON prints with "study": "county_social_capital_longevity_validation" and a decision in:
strong_support, moderate_support, weak_or_failed_support
```

- [ ] **Step 2: Inspect the real credibility report**

Run:

```powershell
Get-Content -Raw -LiteralPath "D:\adk\paper6-spatial-causal-inference\paper\ijgis_submission_20260605\07_results\scca_county_social_capital\credibility_report.json"
```

Expected:

```text
JSON containing "decision", "reasons", "max_balance_corr", and "estimator_statuses".
```

- [ ] **Step 3: Add README command**

Insert after the Soho SCCA command in `README.md`:

````markdown
Run the county social-capital SCCA external validation experiment:

```powershell
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.run_scca_county_social_capital --workbook-path "D:\北大MEM\01-课程学习\02-技术核心课\数据可视化技术及应用\CausalInferAnalysis\CausalInferAnalysis\CountyData_TableToExcel.xlsx"
```

The outputs are written to `paper/ijgis_submission_20260605/07_results/scca_county_social_capital/`. This case is an external continuous-exposure validation with state-level robustness, not a full county-adjacency spatial diagnostic.
````

- [ ] **Step 4: Run focused SCCA verification**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_county_social_capital.py data_agent/test_scca_soho.py data_agent/test_scca_snow8.py -q
```

Expected:

```text
All selected SCCA tests pass.
```

- [ ] **Step 5: Run existing causal verification**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_causal_inference.py -q
```

Expected:

```text
21 passed, 1 warning
```

- [ ] **Step 6: Commit Task 3**

Run:

```powershell
git add README.md paper/ijgis_submission_20260605/07_results/scca_county_social_capital
git commit -m "Add SCCA county social capital outputs"
```

## Final Verification

- [ ] **Step 1: Verify git status**

Run:

```powershell
git status -sb
```

Expected:

```text
## main...origin/main [ahead N]
```

No unstaged or untracked files should remain.

- [ ] **Step 2: Record final commit**

Run:

```powershell
git log -1 --oneline --decorate
```

Expected:

```text
Latest commit is the county output commit.
```

- [ ] **Step 3: Report final results**

Read and report:

```powershell
Get-Content -Raw -LiteralPath "D:\adk\paper6-spatial-causal-inference\paper\ijgis_submission_20260605\07_results\scca_county_social_capital\credibility_report.json"
Get-Content -Raw -LiteralPath "D:\adk\paper6-spatial-causal-inference\paper\ijgis_submission_20260605\07_results\scca_county_social_capital\manifest.json"
```

Final response must include:

- county decision,
- key reasons,
- verification commands and observed pass counts,
- final commit hash,
- reminder that this case is external validation with limited spatial diagnostics.

