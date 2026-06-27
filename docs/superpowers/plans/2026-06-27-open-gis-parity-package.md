# Open GIS Parity Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an ArcGIS-free Open GIS output package from the shared GeoCausal core so CLI, notebooks, QGIS, and optional ArcGIS adapters all receive the same product-grade result contract.

**Architecture:** Add row-level generalized propensity outputs in `data_agent.scca.estimators`, then add a focused `geocausal.open_gis` package writer that consumes existing pipeline artifacts and writes joined analysis, balance, ERF-200, JSON summary, and Markdown summary files. Register those files in the normal GeoCausal manifest from `geocausal.pipeline`.

**Tech Stack:** Python, pandas, NumPy, statsmodels, pytest, existing GeoCausal/SCCA modules.

---

### Task 1: Add Failing Open GIS Package Pipeline Test

**Files:**
- Modify: `data_agent/test_geocausal_pipeline.py`

- [ ] **Step 1: Add the failing test**

Add this test after `test_run_analysis_supports_arcgis_style_trimming_and_targets`:

```python
def test_run_analysis_writes_open_gis_parity_package(tmp_path):
    _fixture_frame().to_csv(tmp_path / "fixture.csv", index=False)
    config = load_config(_write_fixture_config(tmp_path))

    manifest = run_analysis(config)

    output_dir = config.resolve_output_dir()
    package_dir = output_dir / "open_gis_analysis_package"
    expected_files = {
        "analysis_joined.csv",
        "gis_balance_summary.csv",
        "gis_erf_curve_200.csv",
        "gis_run_summary.json",
        "gis_run_summary.md",
    }
    assert expected_files.issubset({path.name for path in package_dir.iterdir()})
    assert manifest["files"]["open_gis_analysis_package"] == "open_gis_analysis_package"
    assert manifest["open_gis_package"]["package_dir"] == "open_gis_analysis_package"

    joined = pd.read_csv(package_dir / "analysis_joined.csv")
    assert {
        "gc_unit_id",
        "gc_exposure",
        "gc_outcome",
        "gc_propensity_score",
        "gc_balancing_weight",
        "gc_included",
        "gc_trim_status",
    }.issubset(joined.columns)
    assert len(joined) == manifest["row_count"]
    assert joined["gc_included"].all()
    assert joined["gc_balancing_weight"].notna().all()

    balance = pd.read_csv(package_dir / "gis_balance_summary.csv")
    assert {"baseline", "confounder", "context"}.issubset(set(balance["variable"]))
    assert {
        "raw_correlation",
        "weighted_correlation",
        "absolute_weighted_correlation",
        "balanced_at_0_1",
    }.issubset(balance.columns)

    erf_200 = pd.read_csv(package_dir / "gis_erf_curve_200.csv")
    assert len(erf_200) == 200
    assert {"exposure", "response", "source"}.issubset(erf_200.columns)
    assert set(erf_200["source"]) == {"interpolated_from_erf_curve"}

    summary = json.loads((package_dir / "gis_run_summary.json").read_text(encoding="utf-8"))
    assert summary["case_name"] == "geocausal_fixture"
    assert summary["generated_files"]["analysis_joined"] == "analysis_joined.csv"
    assert summary["evidence_grade"] in {"core_support", "bounded_support", "fragile_support"}
    assert "Open GIS" in (package_dir / "gis_run_summary.md").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_geocausal_pipeline.py::test_run_analysis_writes_open_gis_parity_package -q
```

Expected: FAIL because `open_gis_analysis_package` does not exist.

- [ ] **Step 3: Commit the failing test only if the project convention permits red commits**

Do not commit yet if using a green-only history. This project has mostly green commits, so keep the red test uncommitted and continue to Task 2.

### Task 2: Write Row-Level Generalized Propensity Output

**Files:**
- Modify: `data_agent/scca/specs.py`
- Modify: `data_agent/scca/estimators.py`

- [ ] **Step 1: Add a path property**

In `SCCAPaths`, add:

```python
    @property
    def generalized_propensity_scores(self) -> Path:
        return self.output_dir / "generalized_propensity_scores.csv"
```

- [ ] **Step 2: Write row-level scores and weights in `estimate_effects`**

After `_gps_weights(features, spec, covariates)` returns `weights, gps_diagnostics`, create a DataFrame:

```python
    gps_output = pd.DataFrame(
        {
            "unit_id": features[spec.unit_id].astype(str)
            if spec.unit_id in features.columns
            else pd.Series([str(index) for index in features.index], index=features.index),
            "gc_propensity_score": gps_diagnostics.get("density", pd.Series(np.nan, index=features.index)),
            "gc_balancing_weight": weights.reindex(features.index).astype(float),
        },
        index=features.index,
    )
    gps_output.to_csv(paths.generalized_propensity_scores, index=False)
```

If `gps_diagnostics` does not yet expose `density`, update `_gps_weights` to add a full-index density series under `diagnostics["density"]`. The fallback density should be all `NaN`; fallback weights remain `1.0`.

- [ ] **Step 3: Run the focused test again**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_geocausal_pipeline.py::test_run_analysis_writes_open_gis_parity_package -q
```

Expected: still FAIL because the package writer does not exist yet, but `generalized_propensity_scores.csv` should now be created during the run.

### Task 3: Add Open GIS Package Writer

**Files:**
- Create: `geocausal/open_gis.py`

- [ ] **Step 1: Create `geocausal/open_gis.py` with package constants and helpers**

Create the file with imports and constants:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from data_agent.scca.specs import SCCAPaths, StudySpec

from .config import GeoCausalConfig


PACKAGE_DIR_NAME = "open_gis_analysis_package"
BALANCE_THRESHOLD = 0.1


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        return numeric if np.isfinite(numeric) else None
    return value
```

- [ ] **Step 2: Add weighted correlation helper**

Add:

```python
def _weighted_correlation(x: pd.Series, y: pd.Series, weights: pd.Series | None = None) -> float:
    frame = pd.DataFrame({"x": x, "y": y})
    if weights is not None:
        frame["w"] = weights
    frame = frame.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 3 or frame["x"].nunique() < 2 or frame["y"].nunique() < 2:
        return np.nan
    if weights is None:
        return float(frame["x"].corr(frame["y"]))
    w = frame["w"].clip(lower=0)
    if float(w.sum()) <= 0:
        return np.nan
    x_centered = frame["x"] - float(np.average(frame["x"], weights=w))
    y_centered = frame["y"] - float(np.average(frame["y"], weights=w))
    cov = float(np.average(x_centered * y_centered, weights=w))
    x_var = float(np.average(x_centered * x_centered, weights=w))
    y_var = float(np.average(y_centered * y_centered, weights=w))
    denom = float(np.sqrt(x_var * y_var))
    return cov / denom if denom > 0 else np.nan
```

- [ ] **Step 3: Add joined table writer**

Add:

```python
def _write_joined_table(
    *,
    package_dir: Path,
    features: pd.DataFrame,
    spec: StudySpec,
    paths: SCCAPaths,
) -> tuple[Path, list[str]]:
    warnings: list[str] = []
    joined = features.copy()
    joined["gc_unit_id"] = (
        joined[spec.unit_id].astype(str)
        if spec.unit_id in joined.columns
        else pd.Series([str(index) for index in joined.index], index=joined.index)
    )
    joined["gc_exposure"] = pd.to_numeric(joined.get(spec.exposure), errors="coerce")
    joined["gc_outcome"] = pd.to_numeric(joined.get(spec.outcome), errors="coerce")
    joined["gc_included"] = True
    joined["gc_trim_status"] = "included"

    gps_path = paths.generalized_propensity_scores
    if gps_path.exists():
        gps = pd.read_csv(gps_path, dtype={"unit_id": "string"})
        joined = joined.merge(
            gps,
            how="left",
            left_on="gc_unit_id",
            right_on="unit_id",
        )
        if "unit_id" in joined.columns and "unit_id" != spec.unit_id:
            joined = joined.drop(columns=["unit_id"])
    else:
        warnings.append("Generalized propensity score file is missing; using NaN scores and unit weights.")
        joined["gc_propensity_score"] = np.nan
        joined["gc_balancing_weight"] = 1.0

    if "gc_propensity_score" not in joined.columns:
        joined["gc_propensity_score"] = np.nan
    if "gc_balancing_weight" not in joined.columns:
        joined["gc_balancing_weight"] = 1.0
    joined["gc_balancing_weight"] = pd.to_numeric(
        joined["gc_balancing_weight"], errors="coerce"
    ).fillna(1.0)

    output_path = package_dir / "analysis_joined.csv"
    joined.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path, warnings
```

- [ ] **Step 4: Add balance summary writer**

Add:

```python
def _write_balance_summary(
    *,
    package_dir: Path,
    features: pd.DataFrame,
    spec: StudySpec,
    weights: pd.Series,
) -> Path:
    rows: list[dict[str, Any]] = []
    variables = [
        *[(column, "confounder") for column in spec.confounders],
        *[(column, "context") for column in spec.context_columns],
    ]
    exposure = pd.to_numeric(features.get(spec.exposure), errors="coerce")
    for variable, role in variables:
        values = pd.to_numeric(features.get(variable), errors="coerce")
        raw = _weighted_correlation(exposure, values)
        weighted = _weighted_correlation(exposure, values, weights)
        abs_weighted = abs(weighted) if np.isfinite(weighted) else np.nan
        rows.append(
            {
                "variable": variable,
                "role": role,
                "raw_correlation": raw,
                "weighted_correlation": weighted,
                "absolute_weighted_correlation": abs_weighted,
                "balanced_at_0_1": bool(np.isfinite(abs_weighted) and abs_weighted <= BALANCE_THRESHOLD),
                "n_complete": int(pd.DataFrame({"x": exposure, "v": values}).dropna().shape[0]),
            }
        )
    output_path = package_dir / "gis_balance_summary.csv"
    pd.DataFrame(rows).to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path
```

- [ ] **Step 5: Add ERF-200 writer**

Add:

```python
def _write_erf_200(package_dir: Path, paths: SCCAPaths) -> tuple[Path, list[str]]:
    warnings: list[str] = []
    output_path = package_dir / "gis_erf_curve_200.csv"
    columns = ["exposure", "response", "source"]
    erf = pd.read_csv(paths.erf_curve) if paths.erf_curve.exists() else pd.DataFrame()
    if erf.empty or not {"exposure", "response"}.issubset(erf.columns):
        pd.DataFrame(columns=columns).to_csv(output_path, index=False, encoding="utf-8-sig")
        return output_path, ["ERF curve is missing or empty; Open GIS ERF-200 output is empty."]
    valid = erf.copy()
    valid["exposure"] = pd.to_numeric(valid["exposure"], errors="coerce")
    valid["response"] = pd.to_numeric(valid["response"], errors="coerce")
    valid = valid.replace([np.inf, -np.inf], np.nan).dropna(subset=["exposure", "response"])
    if len(valid) < 2:
        pd.DataFrame(columns=columns).to_csv(output_path, index=False, encoding="utf-8-sig")
        return output_path, ["ERF curve has fewer than two valid points; Open GIS ERF-200 output is empty."]
    valid = valid.sort_values("exposure")
    grid = np.linspace(float(valid["exposure"].min()), float(valid["exposure"].max()), 200)
    output = pd.DataFrame(
        {
            "exposure": grid,
            "response": np.interp(grid, valid["exposure"], valid["response"]),
            "source": "interpolated_from_erf_curve",
        }
    )
    for optional in ("ci_lower", "ci_upper"):
        if optional in valid.columns:
            output[optional] = np.interp(
                grid,
                valid["exposure"],
                pd.to_numeric(valid[optional], errors="coerce").interpolate().bfill().ffill(),
            )
    output.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path, warnings
```

- [ ] **Step 6: Add public package writer**

Add:

```python
def write_open_gis_package(
    *,
    config: GeoCausalConfig,
    features: pd.DataFrame,
    spec: StudySpec,
    paths: SCCAPaths,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    package_dir = paths.output_dir / PACKAGE_DIR_NAME
    package_dir.mkdir(parents=True, exist_ok=True)

    joined_path, joined_warnings = _write_joined_table(
        package_dir=package_dir,
        features=features,
        spec=spec,
        paths=paths,
    )
    joined = pd.read_csv(joined_path)
    weights = pd.to_numeric(joined["gc_balancing_weight"], errors="coerce").fillna(1.0)
    balance_path = _write_balance_summary(
        package_dir=package_dir,
        features=features,
        spec=spec,
        weights=weights,
    )
    erf_path, erf_warnings = _write_erf_200(package_dir, paths)

    generated_files = {
        "analysis_joined": joined_path.name,
        "gis_balance_summary": balance_path.name,
        "gis_erf_curve_200": erf_path.name,
        "gis_run_summary_json": "gis_run_summary.json",
        "gis_run_summary_markdown": "gis_run_summary.md",
    }
    warnings = [*joined_warnings, *erf_warnings]
    summary = {
        "package_name": "Open GIS Analysis Package",
        "package_dir": PACKAGE_DIR_NAME,
        "case_name": config.case_name,
        "row_count": manifest.get("row_count"),
        "retained_row_count": int(len(features)),
        "exposure": config.variables.exposure,
        "outcome": config.variables.outcome,
        "confounders": list(config.variables.confounders),
        "context_columns": list(config.context.columns),
        "evidence_grade": manifest.get("evidence_grade"),
        "evidence_grade_reasons": manifest.get("evidence_grade_reasons", []),
        "result_summary": manifest.get("result_summary", {}),
        "generated_files": generated_files,
        "warnings": warnings,
    }
    (package_dir / "gis_run_summary.json").write_text(
        json.dumps(_json_ready(summary), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    markdown = "# Open GIS Analysis Package\n\n"
    markdown += f"- Case: `{config.case_name}`\n"
    markdown += f"- Exposure: `{config.variables.exposure}`\n"
    markdown += f"- Outcome: `{config.variables.outcome}`\n"
    markdown += f"- Evidence grade: `{summary['evidence_grade']}`\n"
    markdown += "\n## Files\n\n"
    markdown += "\n".join(f"- {key}: `{value}`" for key, value in generated_files.items())
    markdown += "\n"
    if warnings:
        markdown += "\n## Warnings\n\n"
        markdown += "\n".join(f"- {warning}" for warning in warnings)
        markdown += "\n"
    (package_dir / "gis_run_summary.md").write_text(markdown, encoding="utf-8")
    return summary
```

### Task 4: Wire Package Into Pipeline Manifest

**Files:**
- Modify: `geocausal/pipeline.py`

- [ ] **Step 1: Import the writer**

At the top of `geocausal/pipeline.py`, add:

```python
from .open_gis import PACKAGE_DIR_NAME, write_open_gis_package
```

- [ ] **Step 2: Extend `_write_geocausal_manifest` signature**

Change:

```python
def _write_geocausal_manifest(
    config: GeoCausalConfig,
    loaded: LoadedDataset,
    paths: SCCAPaths,
    credibility: dict[str, Any],
    robustness_manifest: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
```

to:

```python
def _write_geocausal_manifest(
    config: GeoCausalConfig,
    loaded: LoadedDataset,
    features: pd.DataFrame,
    spec: Any,
    paths: SCCAPaths,
    credibility: dict[str, Any],
    robustness_manifest: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
```

- [ ] **Step 3: Call the package writer before writing manifest JSON**

Inside `_write_geocausal_manifest`, after `manifest` is assembled and before `write_result_summary_markdown(...)`, add:

```python
    open_gis_package = write_open_gis_package(
        config=config,
        features=features,
        spec=spec,
        paths=paths,
        manifest=manifest,
    )
    files["open_gis_analysis_package"] = PACKAGE_DIR_NAME
    manifest["open_gis_package"] = open_gis_package
    if open_gis_package.get("warnings"):
        manifest["warnings"] = list(
            dict.fromkeys([*manifest.get("warnings", []), *open_gis_package["warnings"]])
        )
```

- [ ] **Step 4: Pass `features` and `spec` from `run_analysis`**

Change the final return in `run_analysis` from:

```python
        return _write_geocausal_manifest(config, loaded, paths, credibility, robustness_manifest, warnings)
```

to:

```python
        return _write_geocausal_manifest(
            config,
            loaded,
            features,
            spec,
            paths,
            credibility,
            robustness_manifest,
            warnings,
        )
```

- [ ] **Step 5: Run the focused test**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_geocausal_pipeline.py::test_run_analysis_writes_open_gis_parity_package -q
```

Expected: PASS.

### Task 5: Register New Files In Manifest File Collection

**Files:**
- Modify: `data_agent/scca/reporting.py`

- [ ] **Step 1: Ensure report file collection tolerates new GPS output**

If `collect_report_files(paths)` currently uses a fixed set of path properties, add:

```python
    if paths.generalized_propensity_scores.exists():
        files["generalized_propensity_scores"] = paths.generalized_propensity_scores.name
```

- [ ] **Step 2: Run the complete GeoCausal pipeline tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_geocausal_pipeline.py -q
```

Expected: all tests in the file pass.

### Task 6: Update User-Facing Docs

**Files:**
- Modify: `README.md`
- Modify: `docs/geocausal_integration_surfaces.md`

- [ ] **Step 1: Update README GeoCausal section**

In the `GeoCausal SCCA MVP` section, add:

```markdown
Every successful `geocausal run` also writes an Open GIS analysis package under
the run output directory:

- `open_gis_analysis_package/analysis_joined.csv`
- `open_gis_analysis_package/gis_balance_summary.csv`
- `open_gis_analysis_package/gis_erf_curve_200.csv`
- `open_gis_analysis_package/gis_run_summary.json`
- `open_gis_analysis_package/gis_run_summary.md`

This package is designed for ArcGIS-free use in Python, QGIS, notebooks, Excel,
or BI tools while preserving the ArcGIS-style concepts GIS users expect:
retained analysis rows, generalized propensity scores, balancing weights,
balance diagnostics, an exposure-response curve, target-outcome outputs, spatial
diagnostics, and evidence grading.
```

- [ ] **Step 2: Update integration surfaces docs**

In `docs/geocausal_integration_surfaces.md`, under `Core Boundary`, add a paragraph explaining that all interfaces receive the Open GIS package and that ArcGIS Pro is optional.

- [ ] **Step 3: Run docs-neutral focused tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent\test_geocausal_pipeline.py data_agent\test_qgis_provider_structure.py data_agent\test_geocausal_adapters.py -q
```

Expected: all selected tests pass.

### Task 7: Final Verification And Commit

**Files:**
- All modified files from previous tasks.

- [ ] **Step 1: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected: no output and exit code 0.

- [ ] **Step 2: Inspect status**

Run:

```powershell
git status --short --branch
```

Expected: only intended files are modified or added.

- [ ] **Step 3: Commit the implementation**

Run:

```powershell
git add data_agent/test_geocausal_pipeline.py data_agent/scca/specs.py data_agent/scca/estimators.py data_agent/scca/reporting.py geocausal/open_gis.py geocausal/pipeline.py README.md docs/geocausal_integration_surfaces.md docs/superpowers/specs/2026-06-27-open-gis-parity-package-design.md docs/superpowers/plans/2026-06-27-open-gis-parity-package.md
git commit -m "Add Open GIS parity output package"
```

- [ ] **Step 4: Preserve worktree for PR iteration**

Do not remove `.worktrees/open-gis-parity-package`. It should remain available for follow-up fixes and PR creation.
