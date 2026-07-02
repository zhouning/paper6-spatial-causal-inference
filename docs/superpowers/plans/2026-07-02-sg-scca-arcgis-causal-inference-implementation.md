# SG-SCCA ArcGIS Causal Inference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the SG-SCCA core upgrade that exceeds ArcGIS-style Causal Inference outputs with scale-aware estimands, graph-orthogonal adjustment, and residual spatial bias-bound reporting.

**Architecture:** Add focused SCCA modules for scale support, graph orthogonalization, orthogonal estimation, and bias bounds. Integrate them through a new SG-SCCA runner that writes JSON/CSV artifacts without disrupting existing SCCA outputs.

**Tech Stack:** Python, pandas, numpy, statsmodels, sklearn, pytest, existing `data_agent.scca` modules.

---

## Scope Check

This plan implements the first complete SG-SCCA software and manuscript slice:

- Core library modules.
- Tests for each new mathematical component.
- A runner that produces SG-SCCA artifacts.
- An ArcGIS-compatible comparison script.
- A manuscript-ready theory section fragment.

It does not attempt to reverse-engineer Esri internals. The baseline is the local ArcGIS comparison report already stored in the repository.

## File Structure

- Modify: `data_agent/scca/specs.py`
  - Add optional support metadata to `StudySpec`.
  - Add output paths for SG-SCCA artifacts.
- Create: `data_agent/scca/scale.py`
  - Build same-support and change-of-support summaries.
  - Aggregate fine treatment/context rows to outcome support.
- Create: `data_agent/scca/graph_orthogonal.py`
  - Convert `SpatialGraph` neighbors to a dense adjacency matrix.
  - Build graph Laplacian and low-frequency basis.
  - Remove low-frequency graph projection from treatment residuals.
- Create: `data_agent/scca/orthogonal_estimators.py`
  - Fit cross-fitted nuisance residuals.
  - Estimate the graph-orthogonal causal slope.
- Create: `data_agent/scca/bias_bounds.py`
  - Compute residual spatial bias-bound diagnostics.
- Create: `data_agent/scca/sg_scca.py`
  - Orchestrate SG-SCCA graph, scale, estimator, bias-bound, and output writing.
- Create: `data_agent/experiments/run_sg_scca_arcgis_comparison.py`
  - Run an ArcGIS-compatible county comparison with SG-SCCA outputs.
- Create tests:
  - `data_agent/test_sg_scca_paths.py`
  - `data_agent/test_sg_scca_scale.py`
  - `data_agent/test_sg_scca_graph_orthogonal.py`
  - `data_agent/test_sg_scca_orthogonal_estimators.py`
  - `data_agent/test_sg_scca_bias_bounds.py`
  - `data_agent/test_sg_scca_runner.py`
  - `data_agent/test_sg_scca_arcgis_comparison.py`
- Create: `paper/ijgis_submission_20260605/04_theory/sg_scca_theory_section.tex`
  - Manuscript-ready theory section to splice into the main paper after review.

---

### Task 1: Extend StudySpec and SCCAPaths for SG-SCCA

**Files:**
- Modify: `data_agent/scca/specs.py`
- Test: `data_agent/test_sg_scca_paths.py`

- [ ] **Step 1: Write the failing test**

Create `data_agent/test_sg_scca_paths.py`:

```python
from pathlib import Path

from data_agent.scca.specs import SCCAPaths, StudySpec


def test_study_spec_accepts_scale_support_metadata():
    spec = StudySpec(
        name="scale_fixture",
        unit_id="building_id",
        exposure="high_rise",
        outcome="lst",
        treatment_support="building",
        outcome_support="modis_pixel",
        aggregation_group="pixel_id",
    )

    assert spec.treatment_support == "building"
    assert spec.outcome_support == "modis_pixel"
    assert spec.aggregation_group == "pixel_id"


def test_scca_paths_include_sg_scca_outputs(tmp_path):
    paths = SCCAPaths(output_dir=Path(tmp_path))

    assert paths.scale_summary.name == "scale_summary.json"
    assert paths.sg_scca_diagnostics.name == "sg_scca_diagnostics.json"
    assert paths.sg_scca_effect_estimates.name == "sg_scca_effect_estimates.csv"
    assert paths.sg_scca_bias_bound.name == "sg_scca_bias_bound.json"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python -m pytest data_agent/test_sg_scca_paths.py -q
```

Expected: FAIL because `StudySpec` has no support fields and `SCCAPaths` has no SG-SCCA properties.

- [ ] **Step 3: Add the minimal model and path fields**

Modify `data_agent/scca/specs.py`:

```python
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
    treatment_support: str | None = None
    outcome_support: str | None = None
    aggregation_group: str | None = None
```

Add these properties to `SCCAPaths`:

```python
    @property
    def scale_summary(self) -> Path:
        return self.output_dir / "scale_summary.json"

    @property
    def sg_scca_diagnostics(self) -> Path:
        return self.output_dir / "sg_scca_diagnostics.json"

    @property
    def sg_scca_effect_estimates(self) -> Path:
        return self.output_dir / "sg_scca_effect_estimates.csv"

    @property
    def sg_scca_bias_bound(self) -> Path:
        return self.output_dir / "sg_scca_bias_bound.json"
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
python -m pytest data_agent/test_sg_scca_paths.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add data_agent/scca/specs.py data_agent/test_sg_scca_paths.py
git commit -m "feat: add SG-SCCA spec paths"
```

---

### Task 2: Add Scale-Aware Aggregation

**Files:**
- Create: `data_agent/scca/scale.py`
- Test: `data_agent/test_sg_scca_scale.py`

- [ ] **Step 1: Write the failing tests**

Create `data_agent/test_sg_scca_scale.py`:

```python
import json

import pandas as pd

from data_agent.scca.scale import build_scale_summary, aggregate_to_outcome_support
from data_agent.scca.specs import SCCAPaths, StudySpec


def test_build_scale_summary_marks_same_support(tmp_path):
    spec = StudySpec(name="same", unit_id="id", exposure="t", outcome="y")
    paths = SCCAPaths(output_dir=tmp_path)

    summary = build_scale_summary(pd.DataFrame({"id": [1, 2], "t": [0, 1], "y": [3, 4]}), spec, paths)

    assert summary["scale_status"] == "same_support"
    assert summary["aggregation_group"] is None
    assert json.loads(paths.scale_summary.read_text(encoding="utf-8")) == summary


def test_aggregate_to_outcome_support_uses_group_means():
    frame = pd.DataFrame(
        {
            "building_id": ["a", "b", "c", "d"],
            "pixel_id": ["p1", "p1", "p2", "p2"],
            "high_rise": [1.0, 0.0, 1.0, 1.0],
            "lst": [30.0, 30.0, 32.0, 32.0],
            "elevation": [100.0, 120.0, 200.0, 220.0],
            "ndvi": [0.20, 0.30, 0.40, 0.50],
        }
    )
    spec = StudySpec(
        name="change_support",
        unit_id="building_id",
        exposure="high_rise",
        outcome="lst",
        context_columns=("ndvi",),
        confounders=("elevation",),
        treatment_support="building",
        outcome_support="modis_pixel",
        aggregation_group="pixel_id",
    )

    aggregated, summary = aggregate_to_outcome_support(frame, spec)

    assert list(aggregated["pixel_id"]) == ["p1", "p2"]
    assert list(aggregated["n_fine_units"]) == [2, 2]
    assert aggregated.loc[aggregated["pixel_id"] == "p1", "high_rise"].iloc[0] == 0.5
    assert aggregated.loc[aggregated["pixel_id"] == "p2", "elevation"].iloc[0] == 210.0
    assert summary["scale_status"] == "change_of_support"
    assert summary["fine_units"] == 4
    assert summary["outcome_units"] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest data_agent/test_sg_scca_scale.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'data_agent.scca.scale'`.

- [ ] **Step 3: Implement scale utilities**

Create `data_agent/scca/scale.py`:

```python
from __future__ import annotations

import json
from typing import Iterable

import numpy as np
import pandas as pd

from .specs import SCCAPaths, StudySpec


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        return numeric if np.isfinite(numeric) else None
    return value


def _available(columns: Iterable[str], frame: pd.DataFrame) -> list[str]:
    return [column for column in columns if column in frame.columns]


def aggregate_to_outcome_support(
    frame: pd.DataFrame,
    spec: StudySpec,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Aggregate fine-support rows to the configured outcome support."""

    if not spec.aggregation_group:
        summary = {
            "scale_status": "same_support",
            "treatment_support": spec.treatment_support,
            "outcome_support": spec.outcome_support,
            "aggregation_group": None,
            "fine_units": int(len(frame)),
            "outcome_units": int(len(frame)),
            "warnings": [],
        }
        return frame.copy(), summary

    if spec.aggregation_group not in frame.columns:
        raise KeyError(f"Aggregation group column is missing: {spec.aggregation_group}")
    required = [spec.exposure, spec.outcome]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise KeyError(f"Required column(s) missing for scale aggregation: {', '.join(missing)}")

    numeric_columns = _available((spec.exposure, spec.outcome, *spec.confounders, *spec.context_columns), frame)
    working = frame[[spec.aggregation_group, *numeric_columns]].copy()
    for column in numeric_columns:
        working[column] = pd.to_numeric(working[column], errors="coerce")

    grouped = working.groupby(spec.aggregation_group, dropna=False)
    aggregated = grouped[numeric_columns].mean().reset_index()
    counts = grouped.size().rename("n_fine_units").reset_index()
    aggregated = aggregated.merge(counts, on=spec.aggregation_group, how="left")
    summary = {
        "scale_status": "change_of_support",
        "treatment_support": spec.treatment_support,
        "outcome_support": spec.outcome_support,
        "aggregation_group": spec.aggregation_group,
        "fine_units": int(len(frame)),
        "outcome_units": int(len(aggregated)),
        "mean_fine_units_per_outcome": float(aggregated["n_fine_units"].mean()),
        "warnings": [],
    }
    return aggregated, summary


def build_scale_summary(
    frame: pd.DataFrame,
    spec: StudySpec,
    paths: SCCAPaths,
) -> dict[str, object]:
    """Write and return a compact scale-support summary for one run."""

    _, summary = aggregate_to_outcome_support(frame, spec)
    paths.ensure()
    paths.scale_summary.write_text(
        json.dumps(_json_ready(summary), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return summary
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest data_agent/test_sg_scca_scale.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add data_agent/scca/scale.py data_agent/test_sg_scca_scale.py
git commit -m "feat: add scale-aware SCCA aggregation"
```

---

### Task 3: Add Graph Orthogonalization

**Files:**
- Create: `data_agent/scca/graph_orthogonal.py`
- Test: `data_agent/test_sg_scca_graph_orthogonal.py`

- [ ] **Step 1: Write the failing tests**

Create `data_agent/test_sg_scca_graph_orthogonal.py`:

```python
import numpy as np

from data_agent.scca.graph_orthogonal import (
    adjacency_matrix_from_neighbors,
    graph_laplacian,
    low_frequency_basis,
    graph_orthogonalize,
)
from data_agent.scca.spatial_diagnostics import SpatialGraph


def test_adjacency_matrix_from_neighbors_is_symmetric():
    graph = SpatialGraph(method="fixture", neighbors=((1,), (0, 2), (1,)))

    adjacency = adjacency_matrix_from_neighbors(graph)

    assert adjacency.shape == (3, 3)
    assert np.allclose(adjacency, adjacency.T)
    assert adjacency[0, 1] == 1.0
    assert adjacency[0, 2] == 0.0


def test_low_frequency_basis_has_requested_components_without_constant():
    graph = SpatialGraph(method="line", neighbors=((1,), (0, 2), (1, 3), (2,)))
    laplacian = graph_laplacian(adjacency_matrix_from_neighbors(graph))

    basis = low_frequency_basis(laplacian, n_components=2)

    assert basis.shape == (4, 2)
    assert np.allclose(basis.mean(axis=0), 0.0, atol=1e-10)
    assert np.allclose(basis.T @ basis, np.eye(2), atol=1e-10)


def test_graph_orthogonalize_removes_basis_projection():
    graph = SpatialGraph(method="line", neighbors=((1,), (0, 2), (1, 3), (2,)))
    basis = low_frequency_basis(graph_laplacian(adjacency_matrix_from_neighbors(graph)), n_components=1)
    residual = basis[:, 0] * 3.0 + np.array([0.2, -0.1, 0.1, -0.2])

    result = graph_orthogonalize(residual, basis)

    assert result.projection_norm_before > result.projection_norm_after
    assert result.projection_norm_after < 1e-10
    assert np.allclose(basis.T @ result.orthogonal_residual, 0.0, atol=1e-10)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest data_agent/test_sg_scca_graph_orthogonal.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'data_agent.scca.graph_orthogonal'`.

- [ ] **Step 3: Implement graph orthogonalization**

Create `data_agent/scca/graph_orthogonal.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .spatial_diagnostics import SpatialGraph


@dataclass(frozen=True)
class GraphOrthogonalizationResult:
    original_residual: np.ndarray
    orthogonal_residual: np.ndarray
    projection: np.ndarray
    projection_norm_before: float
    projection_norm_after: float
    n_components: int


def adjacency_matrix_from_neighbors(graph: SpatialGraph) -> np.ndarray:
    n = len(graph.neighbors)
    adjacency = np.zeros((n, n), dtype=float)
    for i, neighbors in enumerate(graph.neighbors):
        for j in neighbors:
            if 0 <= int(j) < n and int(j) != i:
                adjacency[i, int(j)] = 1.0
                adjacency[int(j), i] = 1.0
    return adjacency


def graph_laplacian(adjacency: np.ndarray) -> np.ndarray:
    matrix = np.asarray(adjacency, dtype=float)
    degrees = np.diag(matrix.sum(axis=1))
    return degrees - matrix


def low_frequency_basis(laplacian: np.ndarray, n_components: int) -> np.ndarray:
    matrix = np.asarray(laplacian, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("Graph Laplacian must be a square matrix.")
    if matrix.shape[0] == 0 or n_components <= 0:
        return np.zeros((matrix.shape[0], 0), dtype=float)

    eigenvalues, eigenvectors = np.linalg.eigh(matrix)
    order = np.argsort(eigenvalues)
    vectors = eigenvectors[:, order]
    start = 1 if vectors.shape[1] > 1 else 0
    stop = min(vectors.shape[1], start + int(n_components))
    basis = vectors[:, start:stop].astype(float)
    if basis.size == 0:
        return np.zeros((matrix.shape[0], 0), dtype=float)

    basis = basis - basis.mean(axis=0, keepdims=True)
    q, _ = np.linalg.qr(basis)
    return q[:, : basis.shape[1]]


def graph_orthogonalize(residual: np.ndarray, basis: np.ndarray) -> GraphOrthogonalizationResult:
    vector = np.asarray(residual, dtype=float).reshape(-1)
    design = np.asarray(basis, dtype=float)
    if design.ndim != 2:
        raise ValueError("Basis must be a two-dimensional matrix.")
    if design.shape[0] != vector.shape[0]:
        raise ValueError("Residual and basis row counts must match.")
    if design.shape[1] == 0:
        projection = np.zeros_like(vector)
        return GraphOrthogonalizationResult(
            original_residual=vector,
            orthogonal_residual=vector.copy(),
            projection=projection,
            projection_norm_before=0.0,
            projection_norm_after=0.0,
            n_components=0,
        )

    coefficients = np.linalg.pinv(design) @ vector
    projection = design @ coefficients
    orthogonal = vector - projection
    after = float(np.linalg.norm(design.T @ orthogonal))
    before = float(np.linalg.norm(design.T @ vector))
    return GraphOrthogonalizationResult(
        original_residual=vector,
        orthogonal_residual=orthogonal,
        projection=projection,
        projection_norm_before=before,
        projection_norm_after=after,
        n_components=int(design.shape[1]),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest data_agent/test_sg_scca_graph_orthogonal.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add data_agent/scca/graph_orthogonal.py data_agent/test_sg_scca_graph_orthogonal.py
git commit -m "feat: add graph orthogonalization"
```

---

### Task 4: Add Graph-Orthogonal Estimator With Spatial Block Cross-Fitting

**Files:**
- Create: `data_agent/scca/orthogonal_estimators.py`
- Test: `data_agent/test_sg_scca_orthogonal_estimators.py`

- [ ] **Step 1: Write the failing tests**

Create `data_agent/test_sg_scca_orthogonal_estimators.py`:

```python
import numpy as np
import pandas as pd

from data_agent.scca.orthogonal_estimators import fit_graph_orthogonal_effect
from data_agent.scca.spatial_diagnostics import build_spatial_graph
from data_agent.scca.specs import StudySpec


def _fixture():
    rows = []
    for i in range(30):
        x = float(i)
        latent = np.sin(i / 5.0)
        confounder = 0.2 * i
        exposure = 0.7 * confounder + latent + (i % 3) * 0.05
        outcome = 1.5 * exposure + 0.4 * confounder + latent
        rows.append(
            {
                "unit_id": f"u{i}",
                "x": x,
                "y": 0.0,
                "block": f"b{i // 5}",
                "exposure": exposure,
                "outcome": outcome,
                "confounder": confounder,
            }
        )
    frame = pd.DataFrame(rows)
    spec = StudySpec(
        name="orthogonal_fixture",
        unit_id="unit_id",
        exposure="exposure",
        outcome="outcome",
        confounders=("confounder",),
        coordinate_columns=("x", "y"),
        subgroup_column="block",
    )
    return frame, spec


def test_fit_graph_orthogonal_effect_returns_finite_estimate():
    frame, spec = _fixture()
    graph = build_spatial_graph(frame, spec)

    result = fit_graph_orthogonal_effect(frame, spec, graph, n_components=3)

    assert result["status"] == "ok"
    assert np.isfinite(result["coef"])
    assert np.isfinite(result["se"])
    assert result["projection_norm_after"] < result["projection_norm_before"]
    assert result["cross_fit_mode"] == "group"


def test_fit_graph_orthogonal_effect_falls_back_without_groups():
    frame, spec = _fixture()
    spec = StudySpec(
        name=spec.name,
        unit_id=spec.unit_id,
        exposure=spec.exposure,
        outcome=spec.outcome,
        confounders=spec.confounders,
        coordinate_columns=spec.coordinate_columns,
    )
    graph = build_spatial_graph(frame, spec)

    result = fit_graph_orthogonal_effect(frame, spec, graph, n_components=2)

    assert result["status"] == "ok"
    assert result["cross_fit_mode"] == "in_sample"
    assert any("No subgroup column" in warning for warning in result["warnings"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest data_agent/test_sg_scca_orthogonal_estimators.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'data_agent.scca.orthogonal_estimators'`.

- [ ] **Step 3: Implement the estimator**

Create `data_agent/scca/orthogonal_estimators.py`:

```python
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .graph_orthogonal import (
    adjacency_matrix_from_neighbors,
    graph_laplacian,
    graph_orthogonalize,
    low_frequency_basis,
)
from .spatial_diagnostics import SpatialGraph
from .specs import StudySpec


def _finite_or_nan(value: object) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return numeric if np.isfinite(numeric) else float("nan")


def _numeric_frame(features: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    frame = features[columns].apply(pd.to_numeric, errors="coerce")
    return frame.replace([np.inf, -np.inf], np.nan).dropna()


def _design_matrix(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if not columns:
        return pd.DataFrame({"__intercept__": np.ones(len(frame), dtype=float)}, index=frame.index)
    return sm.add_constant(frame[columns].astype(float), has_constant="add")


def _fit_predict(train_x: pd.DataFrame, train_y: pd.Series, test_x: pd.DataFrame) -> np.ndarray:
    model = sm.OLS(train_y.astype(float), train_x.astype(float), missing="drop").fit()
    return np.asarray(model.predict(test_x.astype(float)), dtype=float)


def _in_sample_residuals(frame: pd.DataFrame, target: str, covariates: list[str]) -> np.ndarray:
    x = _design_matrix(frame, covariates)
    y = frame[target].astype(float)
    prediction = _fit_predict(x, y, x)
    return np.asarray(y, dtype=float) - prediction


def _group_cross_fitted_residuals(
    frame: pd.DataFrame,
    target: str,
    covariates: list[str],
    groups: pd.Series,
) -> tuple[np.ndarray, list[str], str]:
    unique_groups = [group for group in pd.unique(groups.dropna())]
    warnings: list[str] = []
    if len(unique_groups) < 2:
        warnings.append("Fewer than two spatial groups; using in-sample nuisance residuals.")
        return _in_sample_residuals(frame, target, covariates), warnings, "in_sample"

    residuals = pd.Series(np.nan, index=frame.index, dtype=float)
    x_all = _design_matrix(frame, covariates)
    y_all = frame[target].astype(float)
    for group in unique_groups:
        test_mask = groups == group
        train_mask = ~test_mask
        if int(train_mask.sum()) <= len(covariates) + 1:
            warnings.append(f"Group {group} has insufficient complement for nuisance fitting.")
            continue
        try:
            residuals.loc[test_mask] = y_all.loc[test_mask] - _fit_predict(
                x_all.loc[train_mask],
                y_all.loc[train_mask],
                x_all.loc[test_mask],
            )
        except Exception as exc:
            warnings.append(f"Cross-fit failed for group {group}: {exc}")

    if residuals.isna().any():
        fallback = _in_sample_residuals(frame, target, covariates)
        residuals = residuals.fillna(pd.Series(fallback, index=frame.index))
    return residuals.to_numpy(dtype=float), warnings, "group"


def _nuisance_residuals(
    frame: pd.DataFrame,
    spec: StudySpec,
    target: str,
    covariates: list[str],
) -> tuple[np.ndarray, list[str], str]:
    if spec.subgroup_column and spec.subgroup_column in frame.columns:
        return _group_cross_fitted_residuals(frame, target, covariates, frame[spec.subgroup_column])
    return (
        _in_sample_residuals(frame, target, covariates),
        ["No subgroup column available; using in-sample nuisance residuals."],
        "in_sample",
    )


def fit_graph_orthogonal_effect(
    features: pd.DataFrame,
    spec: StudySpec,
    graph: SpatialGraph,
    *,
    n_components: int = 4,
) -> dict[str, object]:
    """Estimate a graph-orthogonal causal slope using residualized treatment."""

    covariates = [column for column in (*spec.confounders, *spec.context_columns) if column in features.columns]
    columns = [spec.exposure, spec.outcome, *covariates]
    if spec.subgroup_column and spec.subgroup_column in features.columns:
        columns.append(spec.subgroup_column)
    frame = _numeric_frame(features, [column for column in columns if column != spec.subgroup_column])
    if spec.subgroup_column and spec.subgroup_column in features.columns:
        frame[spec.subgroup_column] = features.loc[frame.index, spec.subgroup_column]

    if len(frame) < max(8, len(covariates) + 4):
        return {
            "status": "skipped",
            "coef": np.nan,
            "se": np.nan,
            "p_value": np.nan,
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "n": int(len(frame)),
            "n_components": 0,
            "projection_norm_before": np.nan,
            "projection_norm_after": np.nan,
            "cross_fit_mode": "skipped",
            "warnings": ["Too few complete rows for SG-SCCA graph-orthogonal estimation."],
        }

    warnings: list[str] = []
    r_t, warn_t, mode_t = _nuisance_residuals(frame, spec, spec.exposure, covariates)
    r_y, warn_y, mode_y = _nuisance_residuals(frame, spec, spec.outcome, covariates)
    warnings.extend(warn_t)
    warnings.extend(warn_y)
    adjacency = adjacency_matrix_from_neighbors(graph)
    adjacency = adjacency[np.ix_(frame.index.to_numpy(dtype=int), frame.index.to_numpy(dtype=int))]
    basis = low_frequency_basis(graph_laplacian(adjacency), n_components=n_components)
    orthogonal = graph_orthogonalize(r_t, basis)

    try:
        x = sm.add_constant(pd.Series(orthogonal.orthogonal_residual, name="r_t_orth"), has_constant="add")
        model = sm.OLS(pd.Series(r_y, name="r_y"), x).fit(cov_type="HC3")
        conf_int = model.conf_int()
        coef = _finite_or_nan(model.params.get("r_t_orth", np.nan))
        se = _finite_or_nan(model.bse.get("r_t_orth", np.nan))
        p_value = _finite_or_nan(model.pvalues.get("r_t_orth", np.nan))
        ci_lower = _finite_or_nan(conf_int.loc["r_t_orth", 0])
        ci_upper = _finite_or_nan(conf_int.loc["r_t_orth", 1])
        status = "ok" if np.isfinite(coef) and np.isfinite(se) else "unstable"
    except Exception as exc:
        warnings.append(f"Graph-orthogonal score fit failed: {exc}")
        coef = se = p_value = ci_lower = ci_upper = np.nan
        status = "unstable"

    return {
        "status": status,
        "coef": coef,
        "se": se,
        "p_value": p_value,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "n": int(len(frame)),
        "n_components": int(orthogonal.n_components),
        "projection_norm_before": float(orthogonal.projection_norm_before),
        "projection_norm_after": float(orthogonal.projection_norm_after),
        "cross_fit_mode": "group" if mode_t == "group" and mode_y == "group" else "in_sample",
        "warnings": warnings,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest data_agent/test_sg_scca_orthogonal_estimators.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add data_agent/scca/orthogonal_estimators.py data_agent/test_sg_scca_orthogonal_estimators.py
git commit -m "feat: add SG-SCCA graph-orthogonal estimator"
```

---

### Task 5: Add Residual Spatial Bias Bounds

**Files:**
- Create: `data_agent/scca/bias_bounds.py`
- Test: `data_agent/test_sg_scca_bias_bounds.py`

- [ ] **Step 1: Write the failing tests**

Create `data_agent/test_sg_scca_bias_bounds.py`:

```python
import numpy as np

from data_agent.scca.bias_bounds import compute_residual_spatial_bias_bound


def test_bias_bound_increases_with_projection_norm():
    low = compute_residual_spatial_bias_bound(
        projection_norm_after=0.1,
        treatment_residual_norm=2.0,
        outcome_residual_sd=1.5,
        latent_smoothness_scale=1.0,
    )
    high = compute_residual_spatial_bias_bound(
        projection_norm_after=0.6,
        treatment_residual_norm=2.0,
        outcome_residual_sd=1.5,
        latent_smoothness_scale=1.0,
    )

    assert low["status"] == "ok"
    assert high["bias_bound"] > low["bias_bound"]
    assert high["bias_bound_ratio"] > low["bias_bound_ratio"]


def test_bias_bound_skips_nonpositive_treatment_norm():
    result = compute_residual_spatial_bias_bound(
        projection_norm_after=0.1,
        treatment_residual_norm=0.0,
        outcome_residual_sd=1.5,
    )

    assert result["status"] == "skipped"
    assert np.isnan(result["bias_bound"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest data_agent/test_sg_scca_bias_bounds.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'data_agent.scca.bias_bounds'`.

- [ ] **Step 3: Implement the bias-bound helper**

Create `data_agent/scca/bias_bounds.py`:

```python
from __future__ import annotations

import numpy as np


def _finite(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if np.isfinite(numeric) else None


def compute_residual_spatial_bias_bound(
    *,
    projection_norm_after: float,
    treatment_residual_norm: float,
    outcome_residual_sd: float,
    latent_smoothness_scale: float = 1.0,
) -> dict[str, object]:
    """Compute a conservative residual spatial bias-bound diagnostic."""

    projection = _finite(projection_norm_after)
    treatment_norm = _finite(treatment_residual_norm)
    outcome_sd = _finite(outcome_residual_sd)
    smoothness = _finite(latent_smoothness_scale)
    if (
        projection is None
        or treatment_norm is None
        or outcome_sd is None
        or smoothness is None
        or treatment_norm <= 0
        or outcome_sd < 0
        or smoothness < 0
    ):
        return {
            "status": "skipped",
            "bias_bound": np.nan,
            "bias_bound_ratio": np.nan,
            "projection_norm_after": projection,
            "treatment_residual_norm": treatment_norm,
            "outcome_residual_sd": outcome_sd,
            "latent_smoothness_scale": smoothness,
            "warnings": ["Bias bound requires finite positive treatment residual norm and nonnegative scales."],
        }

    ratio = projection / treatment_norm
    bound = ratio * outcome_sd * smoothness
    return {
        "status": "ok",
        "bias_bound": float(bound),
        "bias_bound_ratio": float(ratio),
        "projection_norm_after": float(projection),
        "treatment_residual_norm": float(treatment_norm),
        "outcome_residual_sd": float(outcome_sd),
        "latent_smoothness_scale": float(smoothness),
        "warnings": [],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest data_agent/test_sg_scca_bias_bounds.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add data_agent/scca/bias_bounds.py data_agent/test_sg_scca_bias_bounds.py
git commit -m "feat: add residual spatial bias bounds"
```

---

### Task 6: Add SG-SCCA Runner and Output Artifacts

**Files:**
- Create: `data_agent/scca/sg_scca.py`
- Test: `data_agent/test_sg_scca_runner.py`

- [ ] **Step 1: Write the failing runner test**

Create `data_agent/test_sg_scca_runner.py`:

```python
import json

import pandas as pd

from data_agent.scca.sg_scca import run_sg_scca
from data_agent.scca.specs import SCCAPaths, StudySpec


def test_run_sg_scca_writes_diagnostics_and_estimate(tmp_path):
    rows = []
    for i in range(30):
        rows.append(
            {
                "unit_id": f"u{i}",
                "x": float(i),
                "y": 0.0,
                "block": f"b{i // 5}",
                "exposure": float(i % 7) + 0.1 * i,
                "outcome": 2.0 + 1.2 * float(i % 7) + 0.2 * i,
                "confounder": 0.2 * i,
            }
        )
    frame = pd.DataFrame(rows)
    spec = StudySpec(
        name="sg_scca_fixture",
        unit_id="unit_id",
        exposure="exposure",
        outcome="outcome",
        confounders=("confounder",),
        coordinate_columns=("x", "y"),
        subgroup_column="block",
    )
    paths = SCCAPaths(output_dir=tmp_path)

    result = run_sg_scca(frame, spec, paths, n_components=3)

    assert result["estimator"]["status"] == "ok"
    assert paths.sg_scca_diagnostics.exists()
    assert paths.sg_scca_effect_estimates.exists()
    assert paths.sg_scca_bias_bound.exists()
    saved = json.loads(paths.sg_scca_diagnostics.read_text(encoding="utf-8"))
    assert saved["graph"]["method"] == "coordinate_knn"
    assert "bias_bound" in saved
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest data_agent/test_sg_scca_runner.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'data_agent.scca.sg_scca'`.

- [ ] **Step 3: Implement the SG-SCCA runner**

Create `data_agent/scca/sg_scca.py`:

```python
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .bias_bounds import compute_residual_spatial_bias_bound
from .orthogonal_estimators import fit_graph_orthogonal_effect
from .scale import build_scale_summary
from .spatial_diagnostics import SpatialGraph, build_spatial_graph
from .specs import SCCAPaths, StudySpec


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        return numeric if np.isfinite(numeric) else None
    return value


def _graph_summary(graph: SpatialGraph) -> dict[str, object]:
    edge_count = int(sum(len(neighbors) for neighbors in graph.neighbors) // 2)
    return {
        "method": graph.method,
        "node_count": int(len(graph.neighbors)),
        "edge_count": edge_count,
        "warnings": list(graph.warnings),
    }


def _effect_row(estimator: dict[str, object]) -> dict[str, object]:
    keys = ["status", "coef", "se", "p_value", "ci_lower", "ci_upper", "n"]
    row = {"estimator": "sg_scca_graph_orthogonal"}
    row.update({key: estimator.get(key) for key in keys})
    return row


def run_sg_scca(
    features: pd.DataFrame,
    spec: StudySpec,
    paths: SCCAPaths,
    *,
    source_frame: object | None = None,
    n_components: int = 4,
) -> dict[str, object]:
    """Run SG-SCCA and write standalone artifacts."""

    paths.ensure()
    scale_summary = build_scale_summary(features, spec, paths)
    graph = build_spatial_graph(features, spec, source_frame=source_frame)
    estimator = fit_graph_orthogonal_effect(features, spec, graph, n_components=n_components)
    treatment_norm = float(np.nan)
    outcome_sd = float(np.nan)
    if estimator.get("status") == "ok":
        treatment_norm = float(max(estimator.get("projection_norm_before", np.nan), 0.0))
        outcome_sd = float(abs(estimator.get("se", np.nan))) if np.isfinite(float(estimator.get("se", np.nan))) else np.nan
    bias_bound = compute_residual_spatial_bias_bound(
        projection_norm_after=float(estimator.get("projection_norm_after", np.nan)),
        treatment_residual_norm=treatment_norm,
        outcome_residual_sd=outcome_sd,
    )
    result = {
        "study": spec.name,
        "scale": scale_summary,
        "graph": _graph_summary(graph),
        "estimator": estimator,
        "bias_bound": bias_bound,
    }

    paths.sg_scca_diagnostics.write_text(
        json.dumps(_json_ready(result), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    paths.sg_scca_bias_bound.write_text(
        json.dumps(_json_ready(bias_bound), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    pd.DataFrame([_effect_row(estimator)]).to_csv(paths.sg_scca_effect_estimates, index=False)
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest data_agent/test_sg_scca_runner.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add data_agent/scca/sg_scca.py data_agent/test_sg_scca_runner.py
git commit -m "feat: add SG-SCCA runner"
```

---

### Task 7: Add ArcGIS-Compatible SG-SCCA Comparison Script

**Files:**
- Create: `data_agent/experiments/run_sg_scca_arcgis_comparison.py`
- Test: `data_agent/test_sg_scca_arcgis_comparison.py`

- [ ] **Step 1: Write the failing comparison test**

Create `data_agent/test_sg_scca_arcgis_comparison.py`:

```python
import json

import pandas as pd

from data_agent.experiments.run_sg_scca_arcgis_comparison import run_sg_scca_arcgis_comparison


def _county_fixture():
    rows = []
    for i in range(40):
        rows.append(
            {
                "FIPS": 1000 + i,
                "STATE_NAME": f"S{i // 8}",
                "AveAgeDeath": 70.0 + 0.2 * i,
                "SocialAssoc": 5.0 + i * 0.8,
                "UnemployRate": 4.0 + (i % 5),
                "pHHinPoverty": 10.0 + (i % 7),
                "pNoHealthInsur": 8.0 + (i % 4),
                "MentalHealth": 4.0 + (i % 3),
                "pAdultSmoking": 15.0 + (i % 6),
                "pAdultObesity": 30.0 + (i % 5),
                "FastFood": 2.0 + (i % 4),
                "pInsufficientSleep": 31.0 + (i % 4),
                "pAlcohol": 4.0 + (i % 6),
                "pSuicideDeaths": 10.0 + (i % 5),
                "AirPollution": 7.0 + (i % 4),
                "Shape_Length": 100000.0 + i * 1000.0,
                "Shape_Area": 1.0e9 + i * 10000.0,
            }
        )
    return pd.DataFrame(rows)


def test_run_sg_scca_arcgis_comparison_writes_manifest(tmp_path):
    workbook = tmp_path / "county.xlsx"
    _county_fixture().to_excel(workbook, sheet_name="CountyData", index=False)
    output_dir = tmp_path / "out"

    manifest = run_sg_scca_arcgis_comparison(workbook, output_dir=output_dir)

    assert manifest["study"] == "county_social_capital_longevity_validation"
    assert manifest["arcgis_compatible"]["trimmed_rows"] < manifest["arcgis_compatible"]["input_rows"]
    assert (output_dir / "sg_scca_diagnostics.json").exists()
    saved = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert saved["sg_scca"]["diagnostics"] == "sg_scca_diagnostics.json"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest data_agent/test_sg_scca_arcgis_comparison.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'data_agent.experiments.run_sg_scca_arcgis_comparison'`.

- [ ] **Step 3: Implement the comparison script**

Create `data_agent/experiments/run_sg_scca_arcgis_comparison.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from data_agent.experiments.run_scca_county_social_capital import (
    DEFAULT_SHEET_NAME,
    prepare_county_social_capital_table,
    load_county_social_capital_workbook,
)
from data_agent.scca.context import build_context_features
from data_agent.scca.design import select_design
from data_agent.scca.estimators import estimate_effects
from data_agent.scca.sg_scca import run_sg_scca
from data_agent.scca.specs import SCCAPaths, StudySpec


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "paper"
    / "ijgis_submission_20260605"
    / "07_results"
    / "sg_scca_arcgis_comparison"
)


def _trim_arcgis_compatible(df: pd.DataFrame, exposure: str) -> tuple[pd.DataFrame, dict[str, object]]:
    lower = float(df[exposure].quantile(0.01))
    upper = float(df[exposure].quantile(0.99))
    trimmed = df[(df[exposure] >= lower) & (df[exposure] <= upper)].copy()
    return trimmed, {
        "input_rows": int(len(df)),
        "trimmed_rows": int(len(trimmed)),
        "removed_rows": int(len(df) - len(trimmed)),
        "lower_quantile": lower,
        "upper_quantile": upper,
    }


def run_sg_scca_arcgis_comparison(
    workbook_path: str | Path,
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    sheet_name: str = DEFAULT_SHEET_NAME,
) -> dict[str, object]:
    spec = StudySpec.county_social_capital_default()
    paths = SCCAPaths(output_dir=Path(output_dir))
    paths.ensure()
    raw = load_county_social_capital_workbook(workbook_path, sheet_name=sheet_name)
    prepared = prepare_county_social_capital_table(raw)
    trimmed, trim_summary = _trim_arcgis_compatible(prepared, spec.exposure)
    features, _ = build_context_features(trimmed, spec, paths)
    select_design(features, spec, paths)
    estimate_effects(features, spec, paths)
    sg_scca = run_sg_scca(features, spec, paths, n_components=4)
    manifest = {
        "study": spec.name,
        "source_workbook": str(workbook_path),
        "arcgis_compatible": trim_summary,
        "files": {
            "effect_estimates": paths.effect_estimates.name,
            "erf_curve": paths.erf_curve.name,
            "model_diagnostics": paths.model_diagnostics.name,
            "scale_summary": paths.scale_summary.name,
        },
        "sg_scca": {
            "diagnostics": paths.sg_scca_diagnostics.name,
            "effect_estimates": paths.sg_scca_effect_estimates.name,
            "bias_bound": paths.sg_scca_bias_bound.name,
            "estimator_status": sg_scca["estimator"]["status"],
        },
    }
    paths.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SG-SCCA ArcGIS-compatible comparison.")
    parser.add_argument("--workbook-path", required=True)
    parser.add_argument("--sheet-name", default=DEFAULT_SHEET_NAME)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    manifest = run_sg_scca_arcgis_comparison(
        args.workbook_path,
        output_dir=args.output_dir,
        sheet_name=args.sheet_name,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest data_agent/test_sg_scca_arcgis_comparison.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add data_agent/experiments/run_sg_scca_arcgis_comparison.py data_agent/test_sg_scca_arcgis_comparison.py
git commit -m "feat: add SG-SCCA ArcGIS comparison run"
```

---

### Task 8: Add Manuscript Theory Section Fragment

**Files:**
- Create: `paper/ijgis_submission_20260605/04_theory/sg_scca_theory_section.tex`
- Test: `paper/ijgis_submission_20260605/04_theory/sg_scca_theory_section.tex`

- [ ] **Step 1: Create the theory section fragment**

Create `paper/ijgis_submission_20260605/04_theory/sg_scca_theory_section.tex`:

```tex
\section{Scale-aware graph-orthogonal spatial causal adjustment}
\label{sec:sg_scca_theory}

ArcGIS-style causal-inference tools are useful for estimating exposure-response
relationships after trimming and balancing observed confounders. They do not,
however, distinguish three geographic risks that affect causal interpretation:
residual graph-smooth spatial confounding, treatment-outcome scale mismatch, and
post-treatment spatial context. SG-SCCA extends this class of tools by defining
a scale-aware estimand and a graph-orthogonal adjustment score.

\subsection{Scale-aware estimand}

Let $T_f$ denote treatment measured on fine units such as buildings and let
$Y_s$ denote an outcome measured on a coarser spatial support such as a remote
sensing pixel. Let $A$ be an aggregation operator from fine units to the outcome
support. When treatment and outcome supports differ, SG-SCCA reports the
outcome-support estimand
\[
\beta_s =
\frac{\partial E[Y_s \mid A(T_f), A(X_f), A(C_f)]}{\partial A(T_f)}.
\]
This estimand is not a building-level ATT. The building-level contrast can be
reported as a diagnostic approximation, but the outcome-support slope is the
primary estimand when the measured outcome is coarse.

\subsection{Graph-orthogonal adjustment}

Let $G=(V,E)$ be a spatial graph with Laplacian $L$, and let $\Phi_k$ contain
the first $k$ non-constant low-frequency eigenvectors of $L$. After residualizing
treatment on observed covariates and admissible spatial context, SG-SCCA removes
the graph-smooth projection:
\[
R_T^{\perp} = R_T - \Phi_k(\Phi_k^\top \Phi_k)^{-1}\Phi_k^\top R_T.
\]
The causal slope is then estimated with an orthogonal score using
$R_T^{\perp}$ and a separately residualized outcome. Spatial block cross-fitting
is used when group labels are available, so nuisance fitting does not train and
predict on the same spatial block.

\subsection{Residual spatial bias-bound}

The graph-orthogonal step does not identify effects under arbitrary unmeasured
spatial confounding. It provides a measurable warning boundary. If the latent
spatial confounder is graph-smooth, the remaining bias is bounded by the
remaining low-frequency treatment projection, the scale of outcome residual
variation, and a latent smoothness scale:
\[
|\mathrm{Bias}(\hat{\beta}_{SG})|
\leq
\left(
\frac{\|\Phi_k^\top R_T^{\perp}\|_2}{\|R_T\|_2}
\right)
\sigma_{Y \mid X,C}\kappa_U.
\]
This bound is conservative. It is intended to report when ArcGIS-style
exposure-response conclusions remain vulnerable to spatially structured
confounding, not to certify causal identification.
```

- [ ] **Step 2: Verify the fragment contains required claims**

Run:

```bash
rg -n "ArcGIS-style|Scale-aware estimand|Graph-orthogonal|Residual spatial bias-bound|not a building-level ATT" paper/ijgis_submission_20260605/04_theory/sg_scca_theory_section.tex
```

Expected: five or more matching lines covering the claims.

- [ ] **Step 3: Commit**

```bash
git add paper/ijgis_submission_20260605/04_theory/sg_scca_theory_section.tex
git commit -m "docs: draft SG-SCCA theory section"
```

---

### Task 9: Final Verification

**Files:**
- Verify all SG-SCCA modules and tests.

- [ ] **Step 1: Run focused SG-SCCA tests**

Run:

```bash
python -m pytest data_agent/test_sg_scca_paths.py data_agent/test_sg_scca_scale.py data_agent/test_sg_scca_graph_orthogonal.py data_agent/test_sg_scca_orthogonal_estimators.py data_agent/test_sg_scca_bias_bounds.py data_agent/test_sg_scca_runner.py data_agent/test_sg_scca_arcgis_comparison.py -q
```

Expected: PASS.

- [ ] **Step 2: Run related existing tests**

Run:

```bash
python -m pytest data_agent/test_scca_spatial_diagnostics.py data_agent/test_scca_county_social_capital.py data_agent/test_scca_evidence_rules.py -q
```

Expected: PASS.

- [ ] **Step 3: Check repository status**

Run:

```bash
git status --short --branch
```

Expected: clean working tree on the implementation branch after commits.

- [ ] **Step 4: Summarize the implementation**

Write a concise implementation summary containing:

- New SG-SCCA modules.
- Tests run.
- Any numerical or theoretical caveats.
- Exact output files generated by the ArcGIS comparison script.

No commit is needed for the summary unless it is saved as a repository file.

---

## Self-Review Notes

Spec coverage:

- Scale-aware estimands: Task 2 and Task 8.
- Graph-orthogonal adjustment: Task 3 and Task 4.
- Spatial block cross-fitting: Task 4.
- Residual spatial bias bounds: Task 5 and Task 8.
- SG-SCCA artifacts: Task 6.
- ArcGIS-specific comparison: Task 7.
- Manuscript theory upgrade: Task 8.

The plan intentionally keeps ArcGIS claims scoped to the Causal Inference tool baseline represented by the local comparison report. It does not claim to exceed the entire ArcGIS platform.
