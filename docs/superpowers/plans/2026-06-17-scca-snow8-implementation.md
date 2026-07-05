# SCCA Snow8 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working Spatial Context Causal Adjustment (SCCA) pipeline on the South London cholera `snow8/subdistricts.csv` data, producing reproducible effect estimates, diagnostics, and a credibility decision.

**Architecture:** Add a focused `data_agent/scca/` package that is independent from the existing broad `causal_inference.py` tools. The first implementation loads the snow8 CSV, profiles fields, builds context features, runs baseline-adjusted continuous-exposure models, audits overlap/balance/robustness, and writes JSON/CSV/Markdown outputs. Existing Paper6 tools remain untouched except for adding a new experiment runner entry point.

**Tech Stack:** Python 3.11+, pandas, numpy, scipy, scikit-learn, statsmodels, matplotlib, pytest, openpyxl. Use `D:\adk\.venv\Scripts\python.exe` for tests and scripts in this environment.

---

## Scope

This plan implements only Checkpoint 1 from the approved redesign spec:

- South London water-supplier data from `snow8/subdistricts.csv`.
- Manual study specification.
- Data profile, context features, design plan, effect estimates, balance/overlap diagnostics, leave-one-district-out robustness, and credibility report.

This plan does not implement:

- Soho pump placebo analysis.
- US social-capital validation.
- LLM variable-role suggestions.
- GeoFM or world-model features.
- Manuscript rewrite.

Those should be separate follow-up plans after snow8 results are inspected.

## Baseline Verification

Baseline command already verified before writing this plan:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_causal_inference.py -q
```

Observed result:

```text
21 passed, 1 warning
```

## File Structure

Create these files:

- `data_agent/scca/__init__.py`  
  Exports the public SCCA dataclasses and snow8 runner helpers.

- `data_agent/scca/specs.py`  
  Dataclasses for study configuration and output paths.

- `data_agent/scca/profiling.py`  
  Loads tabular/geospatial data and writes data-profile artifacts.

- `data_agent/scca/context.py`  
  Builds spatial/context features from existing columns.

- `data_agent/scca/design.py`  
  Selects a continuous-exposure, baseline-adjusted design and records warnings.

- `data_agent/scca/estimators.py`  
  Fits baseline-adjusted OLS, difference-outcome OLS, and generalized-propensity weighted ERF.

- `data_agent/scca/diagnostics.py`  
  Computes overlap, exposure-balance, robustness, and credibility decisions.

- `data_agent/scca/reporting.py`  
  Writes Markdown report and output manifest.

- `data_agent/experiments/run_scca_snow8.py`  
  CLI runner for the snow8 case.

- `data_agent/test_scca_snow8.py`  
  Unit and integration tests using synthetic data and a small fixture copied from the observed snow8 schema.

Modify these files:

- `README.md`  
  Add one short command for running the SCCA snow8 experiment.

Generated outputs after implementation:

- `paper/ijgis_submission_20260605/07_results/scca_snow8/data_profile.json`
- `paper/ijgis_submission_20260605/07_results/scca_snow8/variable_candidates.csv`
- `paper/ijgis_submission_20260605/07_results/scca_snow8/context_features.csv`
- `paper/ijgis_submission_20260605/07_results/scca_snow8/context_feature_manifest.json`
- `paper/ijgis_submission_20260605/07_results/scca_snow8/design_plan.json`
- `paper/ijgis_submission_20260605/07_results/scca_snow8/effect_estimates.csv`
- `paper/ijgis_submission_20260605/07_results/scca_snow8/erf_curve.csv`
- `paper/ijgis_submission_20260605/07_results/scca_snow8/model_diagnostics.json`
- `paper/ijgis_submission_20260605/07_results/scca_snow8/balance_summary.csv`
- `paper/ijgis_submission_20260605/07_results/scca_snow8/overlap_summary.json`
- `paper/ijgis_submission_20260605/07_results/scca_snow8/spatial_robustness.csv`
- `paper/ijgis_submission_20260605/07_results/scca_snow8/credibility_report.json`
- `paper/ijgis_submission_20260605/07_results/scca_snow8/analysis_report.md`
- `paper/ijgis_submission_20260605/07_results/scca_snow8/manifest.json`

## Task 1: Add SCCA Configuration Dataclasses

**Files:**
- Create: `data_agent/scca/__init__.py`
- Create: `data_agent/scca/specs.py`
- Test: `data_agent/test_scca_snow8.py`

- [ ] **Step 1: Write failing tests for study spec defaults**

Create `data_agent/test_scca_snow8.py` with:

```python
from pathlib import Path

from data_agent.scca.specs import SCCAPaths, StudySpec


def test_study_spec_snow8_defaults():
    spec = StudySpec.snow8_default()
    assert spec.unit_id == "sub_ID"
    assert spec.exposure == "perc_sou"
    assert spec.outcome == "rate1854"
    assert spec.baseline_outcome == "rate1849"
    assert "pop_house" in spec.confounders
    assert "d_thames" in spec.context_columns


def test_scca_paths_create_expected_output_dir(tmp_path):
    paths = SCCAPaths(output_dir=tmp_path / "scca_snow8")
    paths.ensure()
    assert paths.output_dir.exists()
    assert paths.data_profile.name == "data_profile.json"
    assert paths.effect_estimates.name == "effect_estimates.csv"
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_snow8.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'data_agent.scca'
```

- [ ] **Step 3: Implement `data_agent/scca/specs.py`**

Create `data_agent/scca/specs.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class StudySpec:
    """Explicit causal study configuration for an SCCA run."""

    name: str
    unit_id: str
    exposure: str
    outcome: str
    baseline_outcome: str | None = None
    population: str | None = None
    confounders: tuple[str, ...] = field(default_factory=tuple)
    context_columns: tuple[str, ...] = field(default_factory=tuple)
    coordinate_columns: tuple[str, str] | None = None
    subgroup_column: str | None = None

    @classmethod
    def snow8_default(cls) -> "StudySpec":
        return cls(
            name="south_london_cholera_supplier",
            unit_id="sub_ID",
            exposure="perc_sou",
            outcome="rate1854",
            baseline_outcome="rate1849",
            population="pop1854",
            confounders=("rate1849", "pop_house", "pop1851"),
            context_columns=("d_sou", "d_lam", "d_pump", "d_thames", "d_unasc"),
            subgroup_column="district",
        )


@dataclass(frozen=True)
class SCCAPaths:
    """Output paths for one SCCA experiment run."""

    output_dir: Path

    def ensure(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def data_profile(self) -> Path:
        return self.output_dir / "data_profile.json"

    @property
    def variable_candidates(self) -> Path:
        return self.output_dir / "variable_candidates.csv"

    @property
    def context_features(self) -> Path:
        return self.output_dir / "context_features.csv"

    @property
    def context_manifest(self) -> Path:
        return self.output_dir / "context_feature_manifest.json"

    @property
    def design_plan(self) -> Path:
        return self.output_dir / "design_plan.json"

    @property
    def effect_estimates(self) -> Path:
        return self.output_dir / "effect_estimates.csv"

    @property
    def erf_curve(self) -> Path:
        return self.output_dir / "erf_curve.csv"

    @property
    def model_diagnostics(self) -> Path:
        return self.output_dir / "model_diagnostics.json"

    @property
    def balance_summary(self) -> Path:
        return self.output_dir / "balance_summary.csv"

    @property
    def overlap_summary(self) -> Path:
        return self.output_dir / "overlap_summary.json"

    @property
    def spatial_robustness(self) -> Path:
        return self.output_dir / "spatial_robustness.csv"

    @property
    def credibility_report(self) -> Path:
        return self.output_dir / "credibility_report.json"

    @property
    def analysis_report(self) -> Path:
        return self.output_dir / "analysis_report.md"

    @property
    def manifest(self) -> Path:
        return self.output_dir / "manifest.json"
```

- [ ] **Step 4: Implement `data_agent/scca/__init__.py`**

Create `data_agent/scca/__init__.py`:

```python
"""Spatial Context Causal Adjustment (SCCA) workflow."""

from .specs import SCCAPaths, StudySpec

__all__ = ["SCCAPaths", "StudySpec"]
```

- [ ] **Step 5: Run tests and verify they pass**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_snow8.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 6: Commit**

Run:

```powershell
git add data_agent/scca/__init__.py data_agent/scca/specs.py data_agent/test_scca_snow8.py
git commit -m "Add SCCA study configuration"
```

## Task 2: Implement Data Profiling

**Files:**
- Create: `data_agent/scca/profiling.py`
- Modify: `data_agent/test_scca_snow8.py`

- [ ] **Step 1: Add failing tests for data profiling**

Append to `data_agent/test_scca_snow8.py`:

```python
import json

import pandas as pd

from data_agent.scca.profiling import load_table, profile_table


def _snow8_like_frame():
    return pd.DataFrame(
        {
            "sub_ID": ["1", "2", "3"],
            "district": ["A", "A", "B"],
            "perc_sou": [1.0, 0.5, 0.0],
            "rate1854": [180.0, 120.0, 60.0],
            "rate1849": [130.0, 100.0, 70.0],
            "pop_house": [6.5, 7.1, 5.9],
            "pop1851": [10000, 8000, 7000],
            "d_thames": [20.0, 30.0, 10.0],
        }
    )


def test_load_table_reads_csv_with_utf8_sig(tmp_path):
    path = tmp_path / "snow8.csv"
    _snow8_like_frame().to_csv(path, index=False, encoding="utf-8-sig")
    loaded = load_table(path)
    assert loaded.shape == (3, 8)
    assert loaded["perc_sou"].dtype.kind in {"f", "i"}


def test_profile_table_writes_json_and_candidates(tmp_path):
    df = _snow8_like_frame()
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    profile = profile_table(df, StudySpec.snow8_default(), paths)
    assert profile["n_rows"] == 3
    assert profile["columns"]["perc_sou"]["role"] == "exposure"
    assert profile["columns"]["rate1854"]["role"] == "outcome"
    assert paths.data_profile.exists()
    assert paths.variable_candidates.exists()
    saved = json.loads(paths.data_profile.read_text(encoding="utf-8"))
    assert saved["n_columns"] == 8
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_snow8.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'data_agent.scca.profiling'
```

- [ ] **Step 3: Implement `data_agent/scca/profiling.py`**

Create `data_agent/scca/profiling.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .specs import SCCAPaths, StudySpec


def load_table(path: str | Path) -> pd.DataFrame:
    """Load a tabular file for SCCA profiling."""

    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(source, encoding="utf-8-sig")
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(source)
    raise ValueError(f"Unsupported SCCA table format: {source.suffix}")


def _role_for_column(column: str, spec: StudySpec) -> str:
    if column == spec.unit_id:
        return "unit_id"
    if column == spec.exposure:
        return "exposure"
    if column == spec.outcome:
        return "outcome"
    if column == spec.baseline_outcome:
        return "baseline_outcome"
    if column == spec.population:
        return "population"
    if column in spec.confounders:
        return "confounder"
    if column in spec.context_columns:
        return "context"
    if spec.subgroup_column and column == spec.subgroup_column:
        return "subgroup"
    if spec.coordinate_columns and column in spec.coordinate_columns:
        return "coordinate"
    return "available"


def _column_profile(series: pd.Series, role: str) -> dict[str, Any]:
    non_null = int(series.notna().sum())
    result: dict[str, Any] = {
        "role": role,
        "dtype": str(series.dtype),
        "missing": int(series.isna().sum()),
        "non_null": non_null,
        "unique": int(series.nunique(dropna=True)),
    }
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() > 0:
        result.update(
            {
                "min": float(numeric.min()),
                "max": float(numeric.max()),
                "mean": float(numeric.mean()),
            }
        )
    return result


def profile_table(df: pd.DataFrame, spec: StudySpec, paths: SCCAPaths) -> dict[str, Any]:
    """Write a data profile and variable candidate table."""

    paths.ensure()
    profile: dict[str, Any] = {
        "study": spec.name,
        "n_rows": int(len(df)),
        "n_columns": int(len(df.columns)),
        "columns": {},
    }
    rows = []
    for col in df.columns:
        role = _role_for_column(col, spec)
        col_profile = _column_profile(df[col], role)
        profile["columns"][col] = col_profile
        rows.append(
            {
                "column": col,
                "role": role,
                "dtype": col_profile["dtype"],
                "missing": col_profile["missing"],
                "unique": col_profile["unique"],
            }
        )

    paths.data_profile.write_text(
        json.dumps(profile, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    pd.DataFrame(rows).to_csv(paths.variable_candidates, index=False)
    return profile
```

- [ ] **Step 4: Run tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_snow8.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add data_agent/scca/profiling.py data_agent/test_scca_snow8.py
git commit -m "Add SCCA data profiling"
```

## Task 3: Implement Context Feature Builder

**Files:**
- Create: `data_agent/scca/context.py`
- Modify: `data_agent/test_scca_snow8.py`

- [ ] **Step 1: Add failing tests for context features**

Append to `data_agent/test_scca_snow8.py`:

```python
from data_agent.scca.context import build_context_features


def test_build_context_features_adds_baseline_difference_and_density(tmp_path):
    df = _snow8_like_frame()
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    features, manifest = build_context_features(df, StudySpec.snow8_default(), paths)
    assert "outcome_change" in features.columns
    assert "rate1849_centered" in features.columns
    assert "pop_house_centered" in features.columns
    assert "d_thames_centered" in features.columns
    assert features.loc[0, "outcome_change"] == 50.0
    assert manifest["n_features"] >= 4
    assert paths.context_features.exists()
    assert paths.context_manifest.exists()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_snow8.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'data_agent.scca.context'
```

- [ ] **Step 3: Implement `data_agent/scca/context.py`**

Create `data_agent/scca/context.py`:

```python
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .specs import SCCAPaths, StudySpec


def _numeric(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df[column], errors="coerce")


def _center(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values - values.mean()


def build_context_features(
    df: pd.DataFrame,
    spec: StudySpec,
    paths: SCCAPaths,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Build observed spatial/context features for a study."""

    paths.ensure()
    features = pd.DataFrame(index=df.index)
    features[spec.unit_id] = df[spec.unit_id].astype(str)
    features[spec.exposure] = _numeric(df, spec.exposure)
    features[spec.outcome] = _numeric(df, spec.outcome)

    used_columns: list[str] = [spec.exposure, spec.outcome]
    generated: list[str] = []

    if spec.baseline_outcome:
        features[spec.baseline_outcome] = _numeric(df, spec.baseline_outcome)
        features["outcome_change"] = features[spec.outcome] - features[spec.baseline_outcome]
        features[f"{spec.baseline_outcome}_centered"] = _center(df[spec.baseline_outcome])
        used_columns.append(spec.baseline_outcome)
        generated.extend(["outcome_change", f"{spec.baseline_outcome}_centered"])

    for col in spec.confounders:
        if col not in df.columns or col == spec.baseline_outcome:
            continue
        values = _numeric(df, col)
        features[col] = values
        features[f"{col}_centered"] = values - values.mean()
        used_columns.append(col)
        generated.append(f"{col}_centered")

    for col in spec.context_columns:
        if col not in df.columns:
            continue
        values = _numeric(df, col)
        features[col] = values
        features[f"{col}_centered"] = values - values.mean()
        used_columns.append(col)
        generated.append(f"{col}_centered")

    if spec.population and spec.population in df.columns:
        population = _numeric(df, spec.population).replace(0, np.nan)
        features[spec.population] = population
        features["log_population"] = np.log(population)
        used_columns.append(spec.population)
        generated.append("log_population")

    if spec.subgroup_column and spec.subgroup_column in df.columns:
        features[spec.subgroup_column] = df[spec.subgroup_column].astype(str)
        used_columns.append(spec.subgroup_column)

    numeric_cols = features.select_dtypes(include=[np.number]).columns
    features[numeric_cols] = features[numeric_cols].replace([np.inf, -np.inf], np.nan)
    features[numeric_cols] = features[numeric_cols].fillna(features[numeric_cols].median())

    manifest = {
        "study": spec.name,
        "n_rows": int(len(features)),
        "n_features": int(len(features.columns)),
        "source_columns": used_columns,
        "generated_columns": generated,
    }
    features.to_csv(paths.context_features, index=False)
    paths.context_manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return features, manifest
```

- [ ] **Step 4: Run tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_snow8.py -q
```

Expected:

```text
5 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add data_agent/scca/context.py data_agent/test_scca_snow8.py
git commit -m "Add SCCA context feature builder"
```

## Task 4: Implement Design Selector

**Files:**
- Create: `data_agent/scca/design.py`
- Modify: `data_agent/test_scca_snow8.py`

- [ ] **Step 1: Add failing tests for design selection**

Append to `data_agent/test_scca_snow8.py`:

```python
from data_agent.scca.design import select_design


def test_select_design_continuous_exposure_with_small_sample_warning(tmp_path):
    df = _snow8_like_frame()
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    plan = select_design(df, StudySpec.snow8_default(), paths)
    assert plan["design"] == "continuous_exposure_baseline_adjusted"
    assert "generalized_propensity_erf" in plan["estimators"]
    assert "baseline_adjusted_ols" in plan["estimators"]
    assert any("small sample" in warning.lower() for warning in plan["warnings"])
    assert paths.design_plan.exists()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_snow8.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'data_agent.scca.design'
```

- [ ] **Step 3: Implement `data_agent/scca/design.py`**

Create `data_agent/scca/design.py`:

```python
from __future__ import annotations

import json

import pandas as pd

from .specs import SCCAPaths, StudySpec


def select_design(df: pd.DataFrame, spec: StudySpec, paths: SCCAPaths) -> dict[str, object]:
    """Select the first SCCA design from explicit study metadata."""

    paths.ensure()
    exposure = pd.to_numeric(df[spec.exposure], errors="coerce")
    unique_exposure = int(exposure.nunique(dropna=True))
    warnings: list[str] = []

    if len(df) < 50:
        warnings.append(
            f"Small sample: n={len(df)}. Keep models low-dimensional and interpret uncertainty cautiously."
        )
    if unique_exposure <= 2:
        design = "binary_exposure_weighting"
        estimators = ["propensity_weighted_ols"]
    else:
        design = "continuous_exposure_baseline_adjusted"
        estimators = ["baseline_adjusted_ols", "difference_outcome_ols", "generalized_propensity_erf"]

    if spec.baseline_outcome is None:
        warnings.append("No baseline outcome configured; cannot run baseline-adjusted or difference-outcome checks.")
    if spec.subgroup_column is None:
        warnings.append("No subgroup column configured; leave-one-group-out robustness will be skipped.")

    plan = {
        "study": spec.name,
        "design": design,
        "n_rows": int(len(df)),
        "unique_exposure_values": unique_exposure,
        "exposure": spec.exposure,
        "outcome": spec.outcome,
        "baseline_outcome": spec.baseline_outcome,
        "estimators": estimators,
        "warnings": warnings,
    }
    paths.design_plan.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return plan
```

- [ ] **Step 4: Run tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_snow8.py -q
```

Expected:

```text
6 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add data_agent/scca/design.py data_agent/test_scca_snow8.py
git commit -m "Add SCCA design selector"
```

## Task 5: Implement Estimators

**Files:**
- Create: `data_agent/scca/estimators.py`
- Modify: `data_agent/test_scca_snow8.py`

- [ ] **Step 1: Add failing tests for estimators**

Append to `data_agent/test_scca_snow8.py`:

```python
from data_agent.scca.context import build_context_features
from data_agent.scca.estimators import estimate_effects


def test_estimate_effects_writes_effect_tables(tmp_path):
    df = _snow8_like_frame()
    spec = StudySpec.snow8_default()
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    features, _ = build_context_features(df, spec, paths)
    results = estimate_effects(features, spec, paths)
    assert "baseline_adjusted_ols" in results
    assert "difference_outcome_ols" in results
    assert "generalized_propensity_erf" in results
    assert paths.effect_estimates.exists()
    assert paths.erf_curve.exists()
    assert paths.model_diagnostics.exists()
    estimates = pd.read_csv(paths.effect_estimates)
    assert set(estimates["estimator"]) >= {"baseline_adjusted_ols", "difference_outcome_ols"}
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_snow8.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'data_agent.scca.estimators'
```

- [ ] **Step 3: Implement `data_agent/scca/estimators.py`**

Create `data_agent/scca/estimators.py`:

```python
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import gaussian_kde
from sklearn.ensemble import GradientBoostingRegressor

from .specs import SCCAPaths, StudySpec


def _ols_effect(y: pd.Series, x: pd.DataFrame, exposure_name: str) -> dict[str, float]:
    x_const = sm.add_constant(x, has_constant="add")
    model = sm.OLS(y.astype(float), x_const.astype(float), missing="drop").fit()
    return {
        "coef": float(model.params[exposure_name]),
        "se": float(model.bse[exposure_name]),
        "p_value": float(model.pvalues[exposure_name]),
        "ci_lower": float(model.conf_int().loc[exposure_name, 0]),
        "ci_upper": float(model.conf_int().loc[exposure_name, 1]),
        "r_squared": float(model.rsquared),
        "n": int(model.nobs),
    }


def _gps_weights(features: pd.DataFrame, spec: StudySpec, covariates: list[str]) -> np.ndarray:
    exposure = features[spec.exposure].astype(float).to_numpy()
    x = features[covariates].astype(float).to_numpy()
    model = GradientBoostingRegressor(n_estimators=50, max_depth=2, random_state=42)
    model.fit(x, exposure)
    residual = exposure - model.predict(x)
    sigma = max(float(np.std(residual)), 1e-8)
    gps = np.exp(-0.5 * (residual / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))
    try:
        marginal = gaussian_kde(exposure)(exposure)
    except Exception:
        marginal = np.ones_like(exposure)
    weights = marginal / np.maximum(gps, 1e-10)
    weights = np.clip(weights, 0, np.percentile(weights, 95))
    return weights / np.mean(weights)


def _erf_curve(features: pd.DataFrame, spec: StudySpec, weights: np.ndarray) -> pd.DataFrame:
    exposure = features[spec.exposure].astype(float).to_numpy()
    outcome = features[spec.outcome].astype(float).to_numpy()
    grid = np.linspace(float(np.min(exposure)), float(np.max(exposure)), 50)
    bandwidth = max(1.06 * np.std(exposure) * len(exposure) ** (-0.2), 1e-8)
    values = []
    for point in grid:
        kernel = np.exp(-0.5 * ((exposure - point) / bandwidth) ** 2)
        local_weights = kernel * weights
        if local_weights.sum() <= 1e-10:
            values.append(np.nan)
        else:
            values.append(float(np.average(outcome, weights=local_weights)))
    return pd.DataFrame({"exposure": grid, "response": values})


def estimate_effects(
    features: pd.DataFrame,
    spec: StudySpec,
    paths: SCCAPaths,
) -> dict[str, object]:
    """Estimate baseline-adjusted and continuous-exposure effects."""

    paths.ensure()
    covariates = [col for col in spec.confounders if col in features.columns]
    context = [col for col in spec.context_columns if col in features.columns]
    model_covariates = [spec.exposure] + covariates + context

    estimates: list[dict[str, object]] = []
    diagnostics: dict[str, object] = {"covariates": covariates, "context_columns": context}

    baseline = _ols_effect(features[spec.outcome], features[model_covariates], spec.exposure)
    estimates.append({"estimator": "baseline_adjusted_ols", **baseline})

    results: dict[str, object] = {"baseline_adjusted_ols": baseline}

    if "outcome_change" in features.columns:
        diff = _ols_effect(features["outcome_change"], features[model_covariates], spec.exposure)
        estimates.append({"estimator": "difference_outcome_ols", **diff})
        results["difference_outcome_ols"] = diff

    gps_covariates = covariates + context
    if gps_covariates:
        weights = _gps_weights(features, spec, gps_covariates)
    else:
        weights = np.ones(len(features))
    erf = _erf_curve(features, spec, weights)
    erf.to_csv(paths.erf_curve, index=False)
    erf_effect = float(erf["response"].iloc[-1] - erf["response"].iloc[0])
    results["generalized_propensity_erf"] = {
        "response_min_exposure": float(erf["response"].iloc[0]),
        "response_max_exposure": float(erf["response"].iloc[-1]),
        "range_effect": erf_effect,
        "n_grid": int(len(erf)),
    }
    estimates.append(
        {
            "estimator": "generalized_propensity_erf",
            "coef": erf_effect,
            "se": np.nan,
            "p_value": np.nan,
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "r_squared": np.nan,
            "n": len(features),
        }
    )

    diagnostics["gps_weight_min"] = float(np.min(weights))
    diagnostics["gps_weight_max"] = float(np.max(weights))
    diagnostics["gps_weight_mean"] = float(np.mean(weights))

    pd.DataFrame(estimates).to_csv(paths.effect_estimates, index=False)
    paths.model_diagnostics.write_text(
        json.dumps(diagnostics, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return results
```

- [ ] **Step 4: Run tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_snow8.py -q
```

Expected:

```text
7 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add data_agent/scca/estimators.py data_agent/test_scca_snow8.py
git commit -m "Add SCCA effect estimators"
```

## Task 6: Implement Diagnostics and Credibility Decision

**Files:**
- Create: `data_agent/scca/diagnostics.py`
- Modify: `data_agent/test_scca_snow8.py`

- [ ] **Step 1: Add failing tests for diagnostics**

Append to `data_agent/test_scca_snow8.py`:

```python
from data_agent.scca.diagnostics import audit_effects


def test_audit_effects_writes_balance_overlap_and_credibility(tmp_path):
    df = _snow8_like_frame()
    spec = StudySpec.snow8_default()
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    features, _ = build_context_features(df, spec, paths)
    estimate_effects(features, spec, paths)
    report = audit_effects(features, spec, paths)
    assert report["decision"] in {"strong_support", "moderate_support", "weak_or_failed_support"}
    assert "reasons" in report
    assert paths.balance_summary.exists()
    assert paths.overlap_summary.exists()
    assert paths.spatial_robustness.exists()
    assert paths.credibility_report.exists()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_snow8.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'data_agent.scca.diagnostics'
```

- [ ] **Step 3: Implement `data_agent/scca/diagnostics.py`**

Create `data_agent/scca/diagnostics.py`:

```python
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .specs import SCCAPaths, StudySpec


def _corr_abs(a: pd.Series, b: pd.Series) -> float:
    a_num = pd.to_numeric(a, errors="coerce")
    b_num = pd.to_numeric(b, errors="coerce")
    valid = a_num.notna() & b_num.notna()
    if valid.sum() < 3:
        return 0.0
    return float(abs(np.corrcoef(a_num[valid], b_num[valid])[0, 1]))


def _leave_group_out(features: pd.DataFrame, spec: StudySpec) -> pd.DataFrame:
    if spec.subgroup_column is None or spec.subgroup_column not in features.columns:
        return pd.DataFrame(columns=["group", "coef", "n"])
    rows = []
    covariates = [col for col in spec.confounders if col in features.columns]
    context = [col for col in spec.context_columns if col in features.columns]
    x_cols = [spec.exposure] + covariates + context
    for group in sorted(features[spec.subgroup_column].dropna().unique()):
        subset = features[features[spec.subgroup_column] != group]
        if len(subset) < len(x_cols) + 2:
            rows.append({"group": group, "coef": np.nan, "n": len(subset)})
            continue
        x = sm.add_constant(subset[x_cols].astype(float), has_constant="add")
        y = subset[spec.outcome].astype(float)
        model = sm.OLS(y, x, missing="drop").fit()
        rows.append({"group": group, "coef": float(model.params[spec.exposure]), "n": int(model.nobs)})
    return pd.DataFrame(rows)


def audit_effects(
    features: pd.DataFrame,
    spec: StudySpec,
    paths: SCCAPaths,
) -> dict[str, object]:
    """Write balance, overlap, robustness, and credibility diagnostics."""

    paths.ensure()
    exposure = features[spec.exposure].astype(float)
    balance_rows = []
    for col in list(spec.confounders) + list(spec.context_columns):
        if col in features.columns:
            balance_rows.append(
                {
                    "variable": col,
                    "abs_corr_with_exposure": _corr_abs(exposure, features[col]),
                }
            )
    balance = pd.DataFrame(balance_rows)
    balance.to_csv(paths.balance_summary, index=False)

    overlap = {
        "n": int(len(features)),
        "exposure_min": float(exposure.min()),
        "exposure_max": float(exposure.max()),
        "exposure_unique": int(exposure.nunique()),
        "share_at_min": float((exposure == exposure.min()).mean()),
        "share_at_max": float((exposure == exposure.max()).mean()),
    }
    paths.overlap_summary.write_text(
        json.dumps(overlap, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    robustness = _leave_group_out(features, spec)
    robustness.to_csv(paths.spatial_robustness, index=False)

    max_balance_corr = float(balance["abs_corr_with_exposure"].max()) if len(balance) else 0.0
    robust_coefs = robustness["coef"].dropna() if "coef" in robustness else pd.Series(dtype=float)
    sign_stable = bool((robust_coefs > 0).all() or (robust_coefs < 0).all()) if len(robust_coefs) else False

    reasons = []
    decision = "strong_support"
    if overlap["share_at_min"] > 0.25 or overlap["share_at_max"] > 0.25:
        decision = "moderate_support"
        reasons.append("Exposure has mass at boundary values; continuous ERF support is limited.")
    if max_balance_corr > 0.5:
        decision = "moderate_support"
        reasons.append(f"Some covariates remain strongly associated with exposure (max |corr|={max_balance_corr:.3f}).")
    if len(robust_coefs) and not sign_stable:
        decision = "weak_or_failed_support"
        reasons.append("Leave-one-group-out estimates are not sign-stable.")
    if not reasons:
        reasons.append("Overlap, balance, and leave-group-out checks did not trigger configured warnings.")

    report = {
        "study": spec.name,
        "decision": decision,
        "reasons": reasons,
        "max_abs_exposure_balance_corr": max_balance_corr,
        "leave_group_out_sign_stable": sign_stable,
    }
    paths.credibility_report.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report
```

- [ ] **Step 4: Run tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_snow8.py -q
```

Expected:

```text
8 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add data_agent/scca/diagnostics.py data_agent/test_scca_snow8.py
git commit -m "Add SCCA diagnostics and credibility audit"
```

## Task 7: Implement Reporting

**Files:**
- Create: `data_agent/scca/reporting.py`
- Modify: `data_agent/test_scca_snow8.py`

- [ ] **Step 1: Add failing tests for reporting**

Append to `data_agent/test_scca_snow8.py`:

```python
from data_agent.scca.reporting import write_report


def test_write_report_creates_markdown_and_manifest(tmp_path):
    spec = StudySpec.snow8_default()
    paths = SCCAPaths(output_dir=tmp_path)
    paths.ensure()
    credibility = {"decision": "moderate_support", "reasons": ["diagnostic warning"]}
    write_report(spec, paths, credibility)
    text = paths.analysis_report.read_text(encoding="utf-8")
    assert "# SCCA Analysis Report" in text
    assert "moderate_support" in text
    assert paths.manifest.exists()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_snow8.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'data_agent.scca.reporting'
```

- [ ] **Step 3: Implement `data_agent/scca/reporting.py`**

Create `data_agent/scca/reporting.py`:

```python
from __future__ import annotations

import json

from .specs import SCCAPaths, StudySpec


def write_report(spec: StudySpec, paths: SCCAPaths, credibility: dict[str, object]) -> None:
    """Write a compact human-readable report and output manifest."""

    paths.ensure()
    reasons = credibility.get("reasons", [])
    reason_lines = "\n".join(f"- {reason}" for reason in reasons)
    report = f"""# SCCA Analysis Report

## Study

- Name: `{spec.name}`
- Exposure: `{spec.exposure}`
- Outcome: `{spec.outcome}`
- Baseline outcome: `{spec.baseline_outcome}`

## Credibility Decision

`{credibility.get("decision")}`

## Reasons

{reason_lines}

## Output Files

- Data profile: `{paths.data_profile.name}`
- Context features: `{paths.context_features.name}`
- Design plan: `{paths.design_plan.name}`
- Effect estimates: `{paths.effect_estimates.name}`
- ERF curve: `{paths.erf_curve.name}`
- Balance summary: `{paths.balance_summary.name}`
- Overlap summary: `{paths.overlap_summary.name}`
- Spatial robustness: `{paths.spatial_robustness.name}`
- Credibility report: `{paths.credibility_report.name}`
"""
    paths.analysis_report.write_text(report, encoding="utf-8")
    manifest = {
        "study": spec.name,
        "decision": credibility.get("decision"),
        "files": {
            "data_profile": paths.data_profile.name,
            "variable_candidates": paths.variable_candidates.name,
            "context_features": paths.context_features.name,
            "context_manifest": paths.context_manifest.name,
            "design_plan": paths.design_plan.name,
            "effect_estimates": paths.effect_estimates.name,
            "erf_curve": paths.erf_curve.name,
            "model_diagnostics": paths.model_diagnostics.name,
            "balance_summary": paths.balance_summary.name,
            "overlap_summary": paths.overlap_summary.name,
            "spatial_robustness": paths.spatial_robustness.name,
            "credibility_report": paths.credibility_report.name,
            "analysis_report": paths.analysis_report.name,
        },
    }
    paths.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
```

- [ ] **Step 4: Run tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_snow8.py -q
```

Expected:

```text
9 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add data_agent/scca/reporting.py data_agent/test_scca_snow8.py
git commit -m "Add SCCA reporting"
```

## Task 8: Implement End-to-End Snow8 Runner

**Files:**
- Create: `data_agent/experiments/run_scca_snow8.py`
- Modify: `data_agent/test_scca_snow8.py`

- [ ] **Step 1: Add failing integration test for runner**

Append to `data_agent/test_scca_snow8.py`:

```python
from data_agent.experiments.run_scca_snow8 import run_snow8_scca


def test_run_snow8_scca_end_to_end_on_fixture(tmp_path):
    csv_path = tmp_path / "snow8_fixture.csv"
    _snow8_like_frame().to_csv(csv_path, index=False)
    output_dir = tmp_path / "outputs"
    manifest = run_snow8_scca(csv_path=csv_path, output_dir=output_dir)
    assert manifest["decision"] in {"strong_support", "moderate_support", "weak_or_failed_support"}
    assert (output_dir / "analysis_report.md").exists()
    assert (output_dir / "effect_estimates.csv").exists()
    assert (output_dir / "credibility_report.json").exists()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_snow8.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'data_agent.experiments.run_scca_snow8'
```

- [ ] **Step 3: Implement `data_agent/experiments/run_scca_snow8.py`**

Create `data_agent/experiments/run_scca_snow8.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from data_agent.scca.context import build_context_features
from data_agent.scca.design import select_design
from data_agent.scca.diagnostics import audit_effects
from data_agent.scca.estimators import estimate_effects
from data_agent.scca.profiling import load_table, profile_table
from data_agent.scca.reporting import write_report
from data_agent.scca.specs import SCCAPaths, StudySpec


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results" / "scca_snow8"


def run_snow8_scca(csv_path: str | Path, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    """Run the SCCA snow8 workflow and return the output manifest."""

    spec = StudySpec.snow8_default()
    paths = SCCAPaths(output_dir=Path(output_dir))
    paths.ensure()
    df = load_table(csv_path)
    profile_table(df, spec, paths)
    features, _ = build_context_features(df, spec, paths)
    select_design(features, spec, paths)
    estimate_effects(features, spec, paths)
    credibility = audit_effects(features, spec, paths)
    write_report(spec, paths, credibility)
    return json.loads(paths.manifest.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SCCA on South London snow8 data.")
    parser.add_argument("--csv-path", required=True, help="Path to snow8/subdistricts.csv")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for SCCA outputs")
    args = parser.parse_args()
    manifest = run_snow8_scca(args.csv_path, args.output_dir)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_snow8.py -q
```

Expected:

```text
10 passed
```

- [ ] **Step 5: Run the real snow8 experiment**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.run_scca_snow8 --csv-path "<restricted local source>"
```

Expected:

```text
{
  "study": "south_london_cholera_supplier",
  "decision": "moderate_support",
  "files": {
    "adjustment_table": "paper\\ijgis_submission_20260605\\07_results\\scca_snow8\\adjustment_table.csv",
    "effect_table": "paper\\ijgis_submission_20260605\\07_results\\scca_snow8\\effect_table.csv",
    "diagnostics": "paper\\ijgis_submission_20260605\\07_results\\scca_snow8\\diagnostics.json",
    "credibility_report": "paper\\ijgis_submission_20260605\\07_results\\scca_snow8\\credibility_report.json",
    "analysis_report": "paper\\ijgis_submission_20260605\\07_results\\scca_snow8\\analysis_report.md"
  }
}
```

Also verify:

```powershell
Test-Path -LiteralPath "paper\ijgis_submission_20260605\07_results\scca_snow8\analysis_report.md"
```

Expected:

```text
True
```

- [ ] **Step 6: Commit**

Run:

```powershell
git add data_agent/experiments/run_scca_snow8.py data_agent/test_scca_snow8.py paper/ijgis_submission_20260605/07_results/scca_snow8
git commit -m "Add SCCA snow8 experiment runner"
```

## Task 9: Add README Command and Full Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add README instructions**

In `README.md`, under "Quick Start", add:

````markdown
Run the first Spatial Context Causal Adjustment (SCCA) redesign experiment on the South London Snow cholera data:

```powershell
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.run_scca_snow8 --csv-path "<restricted local source>"
```

The outputs are written to `paper/ijgis_submission_20260605/07_results/scca_snow8/`.
````

- [ ] **Step 2: Run focused SCCA tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_snow8.py -q
```

Expected:

```text
10 passed
```

- [ ] **Step 3: Run existing causal tests**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_causal_inference.py -q
```

Expected:

```text
21 passed, 1 warning
```

- [ ] **Step 4: Run the real SCCA snow8 experiment again**

Run:

```powershell
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.run_scca_snow8 --csv-path "<restricted local source>"
```

Expected:

```text
Manifest JSON prints with a decision in:
strong_support, moderate_support, weak_or_failed_support
```

- [ ] **Step 5: Inspect generated decision**

Run:

```powershell
Get-Content -Raw -LiteralPath "paper\ijgis_submission_20260605\07_results\scca_snow8\credibility_report.json"
```

Expected:

```text
JSON containing "decision" and "reasons".
```

Do not rewrite the manuscript in this task. Report the decision and key reasons to the user.

- [ ] **Step 6: Commit README and final verification state**

Run:

```powershell
git add README.md
git commit -m "Document SCCA snow8 experiment"
```

## Final Acceptance Criteria

The implementation is complete when all of the following are true:

- `data_agent/test_scca_snow8.py` passes.
- Existing `data_agent/test_causal_inference.py` still passes.
- The real snow8 run creates all expected files under `paper/ijgis_submission_20260605/07_results/scca_snow8/`.
- `credibility_report.json` contains a neutral decision: `strong_support`, `moderate_support`, or `weak_or_failed_support`.
- The final response reports the actual decision and does not claim the paper is improved until the generated diagnostics have been reviewed.
