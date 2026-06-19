# GeoCausal SCCA MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `geocausal/` Python package and CLI boundary that runs the Paper6 SCCA workflow from a YAML configuration and writes a complete reproducible analysis package.

**Architecture:** Keep the existing `data_agent.scca` implementation in place. Add `geocausal/` as a thin open-source framework layer for YAML config parsing, data loading, diagnostics, pipeline orchestration, CLI commands, and user-facing reports. Reuse `data_agent.scca.specs.StudySpec`, `SCCAPaths`, `build_context_features`, `estimate_effects`, `audit_effects`, and `data_agent.scca.robustness` instead of migrating algorithms.

**Tech Stack:** Python 3.11+, PyYAML, pandas, GeoPandas, pytest, argparse, existing `data_agent.scca` modules.

---

## Files

- Create `geocausal/__init__.py`
  - Version constant and public package marker.
- Create `geocausal/errors.py`
  - User-facing exception classes for configuration, input, and pipeline failures.
- Create `geocausal/config.py`
  - YAML loading, dataclasses, defaults, validation, and `StudySpec` conversion.
- Create `geocausal/io.py`
  - CSV, GeoPackage, GeoJSON, and Shapefile loading into a pandas/GeoPandas frame.
- Create `geocausal/pipeline.py`
  - `diagnose_config`, `run_analysis`, and report rebuilding orchestration.
- Create `geocausal/cli.py`
  - `init`, `diagnose`, `run`, and `report` commands using `argparse`.
- Create `data_agent/test_geocausal_config.py`
  - Tests for YAML parsing, validation, and `StudySpec` conversion.
- Create `data_agent/test_geocausal_io.py`
  - Tests for CSV and GeoJSON loading.
- Create `data_agent/test_geocausal_pipeline.py`
  - Tests for diagnose/run/report output contracts.
- Modify `README.md`
  - Add the minimal GeoCausal SCCA MVP workflow and command examples.

## Baseline Verification

- [ ] Run the current focused test suite before edits.

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_robustness.py data_agent/test_scca_county_social_capital.py data_agent/test_scca_soho.py data_agent/test_scca_snow8.py -q
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_causal_inference.py -q
```

Expected:

- SCCA tests pass.
- Causal inference tests pass with the existing event-loop deprecation warning only.

## Task 1: Configuration Model and Validation

**Files:**
- Create `geocausal/__init__.py`
- Create `geocausal/errors.py`
- Create `geocausal/config.py`
- Create `data_agent/test_geocausal_config.py`

- [ ] Write failing config tests in `data_agent/test_geocausal_config.py`.

```python
from pathlib import Path

import pytest

from geocausal.config import load_config, validate_config
from geocausal.errors import GeoCausalConfigError


def _write_yaml(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_load_config_defaults_and_study_spec(tmp_path):
    config_path = _write_yaml(
        tmp_path / "analysis.yaml",
        """
case_name: fixture_case
input:
  path: fixture.csv
  x: x
  y: y
variables:
  unit_id: unit_id
  exposure: exposure
  outcome: outcome
  confounders:
    - confounder
context:
  columns:
    - context
robustness:
  placebo_exposures:
    - name: placebo_check
      column: placebo
      role: negative_control
      expected_relation: weaker_than_main
  bootstrap:
    group_column: group
output:
  directory: results/fixture
""",
    )
    config = load_config(config_path)
    assert config.case_name == "fixture_case"
    assert config.input.format == "csv"
    assert config.input.x == "x"
    assert config.input.y == "y"
    assert config.variables.confounders == ("confounder",)
    assert config.context.columns == ("context",)
    assert config.robustness.bootstrap.n_replicates == 200
    assert config.resolve_input_path().name == "fixture.csv"
    assert config.resolve_output_dir().name == "fixture"

    spec = config.to_study_spec()
    assert spec.name == "fixture_case"
    assert spec.unit_id == "unit_id"
    assert spec.exposure == "exposure"
    assert spec.outcome == "outcome"
    assert spec.confounders == ("confounder",)
    assert spec.context_columns == ("context",)
    assert spec.coordinate_columns == ("x", "y")
    assert spec.subgroup_column == "group"


def test_load_config_infers_lon_lat_coordinate_columns(tmp_path):
    config_path = _write_yaml(
        tmp_path / "analysis.yaml",
        """
case_name: lon_lat_case
input:
  path: fixture.csv
  lon: longitude
  lat: latitude
variables:
  exposure: exposure
  outcome: outcome
output:
  directory: results/lon_lat
""",
    )
    config = load_config(config_path)
    assert config.input.format == "csv"
    assert config.to_study_spec().coordinate_columns == ("longitude", "latitude")
    assert config.to_study_spec().unit_id == "_gc_unit_id"


def test_validate_config_requires_core_fields(tmp_path):
    config_path = _write_yaml(
        tmp_path / "bad.yaml",
        """
case_name: bad_case
input:
  path: fixture.csv
variables:
  exposure: exposure
output:
  directory: results/bad
""",
    )
    with pytest.raises(GeoCausalConfigError, match="variables.outcome"):
        load_config(config_path)


def test_validate_config_rejects_unsupported_format(tmp_path):
    config_path = _write_yaml(
        tmp_path / "bad.yaml",
        """
case_name: bad_case
input:
  path: fixture.parquet
variables:
  exposure: exposure
  outcome: outcome
output:
  directory: results/bad
""",
    )
    with pytest.raises(GeoCausalConfigError, match="Unsupported input format"):
        load_config(config_path)


def test_validate_config_reports_missing_dataframe_columns(tmp_path):
    config_path = _write_yaml(
        tmp_path / "analysis.yaml",
        """
case_name: fixture_case
input:
  path: fixture.csv
  x: x
  y: y
variables:
  exposure: exposure
  outcome: outcome
  confounders:
    - missing_confounder
context:
  columns:
    - context
robustness:
  placebo_exposures:
    - name: missing_placebo
      column: missing_placebo
  bootstrap:
    group_column: group
output:
  directory: results/fixture
""",
    )
    config = load_config(config_path)
    with pytest.raises(GeoCausalConfigError) as exc:
        validate_config(config, available_columns={"x", "y", "exposure", "outcome", "context", "group"})
    message = str(exc.value)
    assert "missing_confounder" in message
    assert "missing_placebo" in message
```

- [ ] Run the new tests to verify they fail because `geocausal` does not exist.

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_geocausal_config.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'geocausal'
```

- [ ] Implement `geocausal/__init__.py`.

```python
"""GeoCausal: open geospatial causal inference tools derived from Paper6."""

__version__ = "0.1.0"
```

- [ ] Implement `geocausal/errors.py`.

```python
from __future__ import annotations


class GeoCausalError(Exception):
    """Base class for user-facing GeoCausal failures."""


class GeoCausalConfigError(GeoCausalError):
    """Raised when an analysis YAML file is invalid."""


class GeoCausalInputError(GeoCausalError):
    """Raised when an input dataset cannot be loaded or validated."""


class GeoCausalPipelineError(GeoCausalError):
    """Raised when an analysis cannot be completed."""
```

- [ ] Implement `geocausal/config.py`.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from data_agent.scca.specs import StudySpec

from .errors import GeoCausalConfigError


SUPPORTED_FORMATS = {
    ".csv": "csv",
    ".gpkg": "gpkg",
    ".geojson": "geojson",
    ".json": "geojson",
    ".shp": "shp",
}


@dataclass(frozen=True)
class InputConfig:
    path: Path
    format: str
    x: str | None = None
    y: str | None = None
    lon: str | None = None
    lat: str | None = None


@dataclass(frozen=True)
class VariablesConfig:
    exposure: str
    outcome: str
    unit_id: str = "_gc_unit_id"
    baseline_outcome: str | None = None
    population: str | None = None
    confounders: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ContextConfig:
    columns: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PlaceboExposureConfig:
    name: str
    column: str
    role: str = "placebo"
    expected_relation: str = "weaker_than_main"

    def to_robustness_test(self) -> dict[str, str]:
        return {
            "test_name": self.name,
            "exposure": self.column,
            "role": self.role,
            "expected_relation": self.expected_relation,
        }


@dataclass(frozen=True)
class BootstrapConfig:
    group_column: str | None = None
    n_replicates: int = 200


@dataclass(frozen=True)
class RobustnessConfig:
    placebo_exposures: tuple[PlaceboExposureConfig, ...] = field(default_factory=tuple)
    bootstrap: BootstrapConfig = field(default_factory=BootstrapConfig)


@dataclass(frozen=True)
class OutputConfig:
    directory: Path


@dataclass(frozen=True)
class GeoCausalConfig:
    case_name: str
    input: InputConfig
    variables: VariablesConfig
    context: ContextConfig
    robustness: RobustnessConfig
    output: OutputConfig
    config_path: Path

    def resolve_input_path(self) -> Path:
        if self.input.path.is_absolute():
            return self.input.path
        return (self.config_path.parent / self.input.path).resolve()

    def resolve_output_dir(self) -> Path:
        if self.output.directory.is_absolute():
            return self.output.directory
        return (self.config_path.parent / self.output.directory).resolve()

    def to_study_spec(self) -> StudySpec:
        coordinate_columns: tuple[str, str] | None = None
        if self.input.x and self.input.y:
            coordinate_columns = (self.input.x, self.input.y)
        elif self.input.lon and self.input.lat:
            coordinate_columns = (self.input.lon, self.input.lat)
        return StudySpec(
            name=self.case_name,
            unit_id=self.variables.unit_id,
            exposure=self.variables.exposure,
            outcome=self.variables.outcome,
            baseline_outcome=self.variables.baseline_outcome,
            population=self.variables.population,
            confounders=self.variables.confounders,
            context_columns=self.context.columns,
            coordinate_columns=coordinate_columns,
            subgroup_column=self.robustness.bootstrap.group_column,
        )


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GeoCausalConfigError(f"{name} must be a mapping.")
    return value


def _require_text(mapping: dict[str, Any], key: str, owner: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GeoCausalConfigError(f"{owner}.{key} is required.")
    return value.strip()


def _optional_text(mapping: dict[str, Any], key: str) -> str | None:
    value = mapping.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise GeoCausalConfigError(f"{key} must be a non-empty string when provided.")
    return value.strip()


def _text_tuple(value: Any, owner: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise GeoCausalConfigError(f"{owner} must be a list of column names.")
    return tuple(item.strip() for item in value)


def _infer_format(path: Path, explicit: str | None) -> str:
    if explicit:
        normalized = explicit.lower().lstrip(".")
        if normalized in {"csv", "gpkg", "geojson", "shp"}:
            return normalized
        raise GeoCausalConfigError(f"Unsupported input format: {explicit}")
    try:
        return SUPPORTED_FORMATS[path.suffix.lower()]
    except KeyError as exc:
        raise GeoCausalConfigError(f"Unsupported input format: {path.suffix or '<none>'}") from exc


def load_config(path: str | Path) -> GeoCausalConfig:
    config_path = Path(path).resolve()
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise GeoCausalConfigError(f"Cannot read config file: {config_path}") from exc
    if raw is None:
        raise GeoCausalConfigError("Config file is empty.")
    root = _require_mapping(raw, "config")

    case_name = _require_text(root, "case_name", "config")
    input_raw = _require_mapping(root.get("input"), "input")
    variables_raw = _require_mapping(root.get("variables"), "variables")
    context_raw = _require_mapping(root.get("context", {}), "context")
    robustness_raw = _require_mapping(root.get("robustness", {}), "robustness")
    output_raw = _require_mapping(root.get("output"), "output")

    input_path = Path(_require_text(input_raw, "path", "input"))
    input_config = InputConfig(
        path=input_path,
        format=_infer_format(input_path, _optional_text(input_raw, "format")),
        x=_optional_text(input_raw, "x"),
        y=_optional_text(input_raw, "y"),
        lon=_optional_text(input_raw, "lon"),
        lat=_optional_text(input_raw, "lat"),
    )

    variables = VariablesConfig(
        exposure=_require_text(variables_raw, "exposure", "variables"),
        outcome=_require_text(variables_raw, "outcome", "variables"),
        unit_id=_optional_text(variables_raw, "unit_id") or "_gc_unit_id",
        baseline_outcome=_optional_text(variables_raw, "baseline_outcome"),
        population=_optional_text(variables_raw, "population"),
        confounders=_text_tuple(variables_raw.get("confounders"), "variables.confounders"),
    )

    placebo_items = robustness_raw.get("placebo_exposures", [])
    if not isinstance(placebo_items, list):
        raise GeoCausalConfigError("robustness.placebo_exposures must be a list.")
    placebo_exposures = []
    for index, item in enumerate(placebo_items):
        item_raw = _require_mapping(item, f"robustness.placebo_exposures[{index}]")
        column = _require_text(item_raw, "column", f"robustness.placebo_exposures[{index}]")
        placebo_exposures.append(
            PlaceboExposureConfig(
                name=_optional_text(item_raw, "name") or column,
                column=column,
                role=_optional_text(item_raw, "role") or "placebo",
                expected_relation=_optional_text(item_raw, "expected_relation") or "weaker_than_main",
            )
        )

    bootstrap_raw = _require_mapping(robustness_raw.get("bootstrap", {}), "robustness.bootstrap")
    n_replicates = bootstrap_raw.get("n_replicates", 200)
    if not isinstance(n_replicates, int) or n_replicates <= 0:
        raise GeoCausalConfigError("robustness.bootstrap.n_replicates must be a positive integer.")

    config = GeoCausalConfig(
        case_name=case_name,
        input=input_config,
        variables=variables,
        context=ContextConfig(columns=_text_tuple(context_raw.get("columns"), "context.columns")),
        robustness=RobustnessConfig(
            placebo_exposures=tuple(placebo_exposures),
            bootstrap=BootstrapConfig(
                group_column=_optional_text(bootstrap_raw, "group_column"),
                n_replicates=n_replicates,
            ),
        ),
        output=OutputConfig(directory=Path(_require_text(output_raw, "directory", "output"))),
        config_path=config_path,
    )
    return config


def required_columns(config: GeoCausalConfig) -> set[str]:
    columns = {
        config.variables.exposure,
        config.variables.outcome,
        *config.variables.confounders,
        *config.context.columns,
    }
    if config.variables.unit_id != "_gc_unit_id":
        columns.add(config.variables.unit_id)
    if config.variables.baseline_outcome:
        columns.add(config.variables.baseline_outcome)
    if config.variables.population:
        columns.add(config.variables.population)
    if config.input.x:
        columns.add(config.input.x)
    if config.input.y:
        columns.add(config.input.y)
    if config.input.lon:
        columns.add(config.input.lon)
    if config.input.lat:
        columns.add(config.input.lat)
    if config.robustness.bootstrap.group_column:
        columns.add(config.robustness.bootstrap.group_column)
    for placebo in config.robustness.placebo_exposures:
        columns.add(placebo.column)
    return {column for column in columns if column}


def validate_config(config: GeoCausalConfig, available_columns: set[str] | None = None) -> list[str]:
    warnings: list[str] = []
    if config.input.format == "csv":
        has_xy = bool(config.input.x and config.input.y)
        has_lon_lat = bool(config.input.lon and config.input.lat)
        if not has_xy and not has_lon_lat:
            warnings.append("CSV input has no coordinate columns; geometry-derived bootstrap groups are unavailable.")
    if available_columns is not None:
        missing = sorted(required_columns(config) - set(available_columns))
        if missing:
            raise GeoCausalConfigError(f"Missing required columns: {', '.join(missing)}")
    return warnings
```

- [ ] Run config tests.

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_geocausal_config.py -q
```

Expected:

```text
5 passed
```

- [ ] Commit Task 1.

```powershell
git add geocausal/__init__.py geocausal/errors.py geocausal/config.py data_agent/test_geocausal_config.py
git commit -m "Add GeoCausal config model"
```

## Task 2: Input Data Loading

**Files:**
- Create `geocausal/io.py`
- Create `data_agent/test_geocausal_io.py`

- [ ] Write failing IO tests in `data_agent/test_geocausal_io.py`.

```python
import pandas as pd
import pytest

from geocausal.config import load_config
from geocausal.errors import GeoCausalInputError
from geocausal.io import load_dataset


def _write_config(tmp_path, input_block: str):
    path = tmp_path / "analysis.yaml"
    path.write_text(
        f"""
case_name: io_case
input:
{input_block}
variables:
  exposure: exposure
  outcome: outcome
output:
  directory: results/io
""",
        encoding="utf-8",
    )
    return load_config(path)


def test_load_dataset_csv_adds_default_unit_id(tmp_path):
    csv_path = tmp_path / "fixture.csv"
    pd.DataFrame(
        {
            "x": [0.0, 1.0],
            "y": [2.0, 3.0],
            "exposure": [0.1, 0.2],
            "outcome": [5.0, 6.0],
        }
    ).to_csv(csv_path, index=False)
    config = _write_config(
        tmp_path,
        f"""
  path: {csv_path.name}
  x: x
  y: y
""",
    )
    loaded = load_dataset(config)
    assert list(loaded.frame["_gc_unit_id"]) == ["1", "2"]
    assert loaded.geometry_available is False
    assert loaded.columns == {"_gc_unit_id", "x", "y", "exposure", "outcome"}


def test_load_dataset_geojson_preserves_geometry(tmp_path):
    geopandas = pytest.importorskip("geopandas")
    from shapely.geometry import Point

    geojson_path = tmp_path / "fixture.geojson"
    gdf = geopandas.GeoDataFrame(
        {"exposure": [1.0, 2.0], "outcome": [3.0, 5.0]},
        geometry=[Point(0, 0), Point(1, 1)],
        crs="EPSG:4326",
    )
    gdf.to_file(geojson_path, driver="GeoJSON")
    config = _write_config(
        tmp_path,
        f"""
  path: {geojson_path.name}
""",
    )
    loaded = load_dataset(config)
    assert loaded.geometry_available is True
    assert "_gc_unit_id" in loaded.frame.columns
    assert loaded.frame.crs.to_string() == "EPSG:4326"


def test_load_dataset_rejects_missing_input_file(tmp_path):
    config = _write_config(
        tmp_path,
        """
  path: missing.csv
  x: x
  y: y
""",
    )
    with pytest.raises(GeoCausalInputError, match="Input file does not exist"):
        load_dataset(config)
```

- [ ] Run IO tests to verify they fail because `geocausal.io` does not exist.

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_geocausal_io.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'geocausal.io'
```

- [ ] Implement `geocausal/io.py`.

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import GeoCausalConfig
from .errors import GeoCausalInputError


@dataclass(frozen=True)
class LoadedDataset:
    frame: pd.DataFrame
    path: Path
    format: str
    geometry_available: bool
    columns: set[str]
    warnings: tuple[str, ...] = ()


def _ensure_unit_id(frame: pd.DataFrame, unit_id: str) -> pd.DataFrame:
    if unit_id in frame.columns:
        frame[unit_id] = frame[unit_id].astype(str)
        return frame
    if unit_id == "_gc_unit_id":
        frame.insert(0, "_gc_unit_id", [str(i) for i in range(1, len(frame) + 1)])
        return frame
    raise GeoCausalInputError(f"Unit id column is missing: {unit_id}")


def _read_spatial(path: Path) -> pd.DataFrame:
    try:
        import geopandas as gpd
    except ImportError as exc:
        raise GeoCausalInputError("GeoPandas is required for spatial input formats.") from exc
    try:
        return gpd.read_file(path)
    except Exception as exc:
        raise GeoCausalInputError(f"Cannot read spatial input file: {path}") from exc


def load_dataset(config: GeoCausalConfig) -> LoadedDataset:
    path = config.resolve_input_path()
    if not path.exists():
        raise GeoCausalInputError(f"Input file does not exist: {path}")

    warnings: list[str] = []
    if config.input.format == "csv":
        try:
            frame = pd.read_csv(path, encoding="utf-8-sig")
        except Exception as exc:
            raise GeoCausalInputError(f"Cannot read CSV input file: {path}") from exc
        geometry_available = False
    elif config.input.format in {"gpkg", "geojson", "shp"}:
        frame = _read_spatial(path)
        geometry_available = "geometry" in frame.columns
        crs = getattr(frame, "crs", None)
        if geometry_available and crs is None:
            warnings.append("Spatial input has geometry but no CRS metadata.")
    else:
        raise GeoCausalInputError(f"Unsupported input format: {config.input.format}")

    frame = frame.copy()
    frame = _ensure_unit_id(frame, config.variables.unit_id)
    return LoadedDataset(
        frame=frame,
        path=path,
        format=config.input.format,
        geometry_available=geometry_available,
        columns=set(str(column) for column in frame.columns),
        warnings=tuple(warnings),
    )
```

- [ ] Run IO and config tests.

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_geocausal_config.py data_agent/test_geocausal_io.py -q
```

Expected:

```text
8 passed
```

- [ ] Commit Task 2.

```powershell
git add geocausal/io.py data_agent/test_geocausal_io.py
git commit -m "Add GeoCausal input loading"
```

## Task 3: Pipeline Orchestration and Output Contract

**Files:**
- Create `geocausal/pipeline.py`
- Create `data_agent/test_geocausal_pipeline.py`

- [ ] Write failing pipeline tests in `data_agent/test_geocausal_pipeline.py`.

```python
import json
from pathlib import Path

import pandas as pd
import pytest

from geocausal.config import load_config
from geocausal.errors import GeoCausalConfigError
from geocausal.pipeline import diagnose_config, rebuild_report, run_analysis


def _fixture_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "unit_id": [f"u{i}" for i in range(1, 9)],
            "group": ["A", "A", "B", "B", "C", "C", "D", "D"],
            "x": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            "y": [0.0, 1.0, 0.5, 1.5, 2.0, 2.5, 3.0, 3.5],
            "exposure": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            "outcome": [2.0, 2.6, 3.5, 4.1, 5.2, 5.9, 6.8, 7.5],
            "baseline": [1.5, 1.7, 2.0, 2.2, 2.4, 2.5, 2.8, 3.0],
            "confounder": [1.0, 1.1, 1.6, 1.8, 2.3, 2.6, 3.0, 3.3],
            "context": [8.0, 7.5, 7.0, 6.4, 5.9, 5.3, 4.8, 4.2],
            "placebo": [7.0, 6.9, 6.7, 6.6, 6.5, 6.4, 6.2, 6.1],
        }
    )


def _write_fixture_config(tmp_path: Path, csv_name: str = "fixture.csv") -> Path:
    config_path = tmp_path / "analysis.yaml"
    config_path.write_text(
        f"""
case_name: geocausal_fixture
input:
  path: {csv_name}
  x: x
  y: y
variables:
  unit_id: unit_id
  exposure: exposure
  outcome: outcome
  baseline_outcome: baseline
  confounders:
    - baseline
    - confounder
context:
  columns:
    - context
robustness:
  placebo_exposures:
    - name: placebo_check
      column: placebo
      role: negative_control
      expected_relation: weaker_than_main
  bootstrap:
    group_column: group
    n_replicates: 5
output:
  directory: results/geocausal_fixture
""",
        encoding="utf-8",
    )
    return config_path


def test_diagnose_config_returns_rows_columns_and_warnings(tmp_path):
    _fixture_frame().to_csv(tmp_path / "fixture.csv", index=False)
    config = load_config(_write_fixture_config(tmp_path))
    diagnosis = diagnose_config(config)
    assert diagnosis["case_name"] == "geocausal_fixture"
    assert diagnosis["input_rows"] == 8
    assert diagnosis["input_columns"] >= 9
    assert diagnosis["output_writable"] is True
    assert diagnosis["errors"] == []


def test_diagnose_config_raises_for_missing_columns(tmp_path):
    frame = _fixture_frame().drop(columns=["placebo"])
    frame.to_csv(tmp_path / "fixture.csv", index=False)
    config = load_config(_write_fixture_config(tmp_path))
    with pytest.raises(GeoCausalConfigError, match="placebo"):
        diagnose_config(config)


def test_run_analysis_writes_complete_output_package(tmp_path):
    _fixture_frame().to_csv(tmp_path / "fixture.csv", index=False)
    config = load_config(_write_fixture_config(tmp_path))
    manifest = run_analysis(config)
    output_dir = config.resolve_output_dir()
    expected_files = {
        "effect_estimates.csv",
        "erf_curve.csv",
        "context_ablation.csv",
        "placebo_tests.csv",
        "bootstrap_robustness.csv",
        "bootstrap_summary.json",
        "erf_stability.json",
        "robustness_report.md",
        "manifest.json",
    }
    assert expected_files.issubset({path.name for path in output_dir.iterdir()})
    assert manifest["case_name"] == "geocausal_fixture"
    assert manifest["exposure"] == "exposure"
    assert manifest["outcome"] == "outcome"
    assert manifest["row_count"] == 8
    assert manifest["files"]["manifest"] == "manifest.json"
    saved_manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert saved_manifest["robustness_interpretation"] in {
        "robust_support",
        "bounded_support",
        "fragile_support",
    }


def test_rebuild_report_uses_existing_manifest(tmp_path):
    output_dir = tmp_path / "results"
    output_dir.mkdir()
    (output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "case_name": "reported_case",
                "robustness_interpretation": "bounded_support",
                "files": {"manifest": "manifest.json"},
            }
        ),
        encoding="utf-8",
    )
    report = rebuild_report(output_dir)
    assert report["case_name"] == "reported_case"
    assert (output_dir / "geocausal_report.md").exists()
    assert "reported_case" in (output_dir / "geocausal_report.md").read_text(encoding="utf-8")
```

- [ ] Run pipeline tests to verify they fail because `geocausal.pipeline` does not exist.

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_geocausal_pipeline.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'geocausal.pipeline'
```

- [ ] Implement `geocausal/pipeline.py`.

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from data_agent.scca.context import build_context_features
from data_agent.scca.design import select_design
from data_agent.scca.diagnostics import audit_effects
from data_agent.scca.estimators import estimate_effects
from data_agent.scca.profiling import profile_table
from data_agent.scca.robustness import (
    make_quantile_grid_groups,
    run_context_ablation,
    run_group_bootstrap,
    run_placebo_tests,
    summarize_erf_stability,
    write_robustness_outputs,
)
from data_agent.scca.reporting import write_report
from data_agent.scca.specs import SCCAPaths

from . import __version__
from .config import GeoCausalConfig, validate_config
from .errors import GeoCausalConfigError, GeoCausalPipelineError
from .io import LoadedDataset, load_dataset


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    try:
        import numpy as np

        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating, float)):
            numeric = float(value)
            return numeric if np.isfinite(numeric) else None
    except Exception:
        pass
    return value


def _ensure_output_writable(output_dir: Path) -> bool:
    output_dir.mkdir(parents=True, exist_ok=True)
    probe = output_dir / ".geocausal_write_probe"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()
    return True


def diagnose_config(config: GeoCausalConfig) -> dict[str, Any]:
    loaded = load_dataset(config)
    warnings = [*loaded.warnings, *validate_config(config, loaded.columns)]
    output_writable = _ensure_output_writable(config.resolve_output_dir())
    return {
        "case_name": config.case_name,
        "input_path": str(loaded.path),
        "input_format": loaded.format,
        "input_rows": int(len(loaded.frame)),
        "input_columns": int(len(loaded.frame.columns)),
        "geometry_available": loaded.geometry_available,
        "output_directory": str(config.resolve_output_dir()),
        "output_writable": output_writable,
        "warnings": warnings,
        "errors": [],
    }


def _main_effect(effect_estimates_path: Path) -> float:
    estimates = pd.read_csv(effect_estimates_path)
    if estimates.empty:
        return float("nan")
    baseline = estimates.loc[estimates["estimator"] == "baseline_adjusted_ols"]
    row = baseline.iloc[0] if not baseline.empty else estimates.iloc[0]
    return float(pd.to_numeric(pd.Series([row.get("coef")]), errors="coerce").iloc[0])


def _bootstrap_group(loaded: LoadedDataset, config: GeoCausalConfig, features: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    group_column = config.robustness.bootstrap.group_column
    if group_column:
        return features, group_column
    spec = config.to_study_spec()
    if spec.coordinate_columns and all(column in features.columns for column in spec.coordinate_columns):
        generated = "_gc_grid_group"
        x_col, y_col = spec.coordinate_columns
        features = features.copy()
        features[generated] = make_quantile_grid_groups(features, x_col, y_col, bins=4)
        return features, generated
    raise GeoCausalConfigError(
        "robustness.bootstrap.group_column is required when coordinate columns are unavailable."
    )


def _write_geocausal_manifest(
    config: GeoCausalConfig,
    loaded: LoadedDataset,
    paths: SCCAPaths,
    credibility: dict[str, Any],
    robustness_manifest: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    files = {
        "effect_estimates": paths.effect_estimates.name,
        "erf_curve": paths.erf_curve.name,
        "context_ablation": "context_ablation.csv",
        "placebo_tests": "placebo_tests.csv",
        "bootstrap_robustness": "bootstrap_robustness.csv",
        "bootstrap_summary": "bootstrap_summary.json",
        "erf_stability": "erf_stability.json",
        "robustness_report": "robustness_report.md",
        "manifest": "manifest.json",
    }
    manifest = {
        "geocausal_version": __version__,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "case_name": config.case_name,
        "config_path": str(config.config_path),
        "input_path": str(loaded.path),
        "input_format": loaded.format,
        "row_count": int(len(loaded.frame)),
        "exposure": config.variables.exposure,
        "outcome": config.variables.outcome,
        "confounders": list(config.variables.confounders),
        "context_columns": list(config.context.columns),
        "credibility_decision": credibility.get("decision"),
        "robustness_interpretation": robustness_manifest.get("robustness_interpretation"),
        "warnings": warnings,
        "files": files,
    }
    (paths.output_dir / "manifest.json").write_text(
        json.dumps(_json_ready(manifest), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest


def run_analysis(config: GeoCausalConfig) -> dict[str, Any]:
    diagnosis = diagnose_config(config)
    warnings = list(diagnosis["warnings"])
    loaded = load_dataset(config)
    spec = config.to_study_spec()
    paths = SCCAPaths(output_dir=config.resolve_output_dir())
    paths.ensure()

    try:
        profile_table(loaded.frame, spec, paths)
        features, _ = build_context_features(loaded.frame, spec, paths)
        select_design(features, spec, paths)
        estimate_effects(features, spec, paths)
        credibility = audit_effects(features, spec, paths)
        write_report(
            spec,
            paths,
            credibility,
            metadata={
                "source_path": str(loaded.path),
                "config_path": str(config.config_path),
                "geocausal_version": __version__,
            },
        )
        main_coef = _main_effect(paths.effect_estimates)
        ablation = run_context_ablation(features, spec, config.case_name)
        placebo = run_placebo_tests(
            features,
            spec,
            config.case_name,
            [item.to_robustness_test() for item in config.robustness.placebo_exposures],
        )
        bootstrap_features, group_column = _bootstrap_group(loaded, config, features)
        bootstrap_rows, bootstrap_summary = run_group_bootstrap(
            bootstrap_features,
            spec,
            config.case_name,
            group_column=group_column,
            n_replicates=config.robustness.bootstrap.n_replicates,
        )
        erf_curve = pd.read_csv(paths.erf_curve)
        erf_summary = summarize_erf_stability(erf_curve, config.case_name)
        main_limitation = "; ".join(str(reason) for reason in credibility.get("reasons", []))
        robustness_manifest = write_robustness_outputs(
            output_dir=paths.output_dir,
            case_name=config.case_name,
            original_decision=str(credibility.get("decision", "unknown")),
            main_coef=main_coef,
            main_limitation=main_limitation,
            ablation=ablation,
            placebo=placebo,
            bootstrap_rows=bootstrap_rows,
            bootstrap_summary=bootstrap_summary,
            erf_summary=erf_summary,
        )
    except GeoCausalConfigError:
        raise
    except Exception as exc:
        raise GeoCausalPipelineError(f"GeoCausal analysis failed: {exc}") from exc

    return _write_geocausal_manifest(config, loaded, paths, credibility, robustness_manifest, warnings)


def rebuild_report(output_dir: str | Path) -> dict[str, Any]:
    target = Path(output_dir)
    manifest_path = target / "manifest.json"
    if not manifest_path.exists():
        raise GeoCausalPipelineError(f"manifest.json is missing in {target}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = f"""# GeoCausal Analysis Report

## Case

`{manifest.get("case_name")}`

## Interpretation

`{manifest.get("robustness_interpretation")}`

## Files

{chr(10).join(f"- {key}: `{value}`" for key, value in manifest.get("files", {}).items())}
"""
    (target / "geocausal_report.md").write_text(report, encoding="utf-8")
    return manifest
```

- [ ] Run pipeline tests.

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_geocausal_config.py data_agent/test_geocausal_io.py data_agent/test_geocausal_pipeline.py -q
```

Expected:

```text
12 passed
```

- [ ] Commit Task 3.

```powershell
git add geocausal/pipeline.py data_agent/test_geocausal_pipeline.py
git commit -m "Add GeoCausal SCCA pipeline"
```

## Task 4: CLI Commands

**Files:**
- Create `geocausal/cli.py`
- Modify `data_agent/test_geocausal_pipeline.py`

- [ ] Add CLI tests to `data_agent/test_geocausal_pipeline.py`.

Append:

```python
import subprocess
import sys


def test_cli_init_writes_template(tmp_path):
    output = tmp_path / "template.yaml"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "geocausal.cli",
            "init",
            "--template",
            "scca",
            "--output",
            str(output),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=True,
    )
    assert output.exists()
    assert "case_name:" in output.read_text(encoding="utf-8")
    assert str(output) in result.stdout


def test_cli_diagnose_and_run(tmp_path):
    _fixture_frame().to_csv(tmp_path / "fixture.csv", index=False)
    config_path = _write_fixture_config(tmp_path)
    diagnose = subprocess.run(
        [sys.executable, "-m", "geocausal.cli", "diagnose", str(config_path)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "geocausal_fixture" in diagnose.stdout

    run = subprocess.run(
        [sys.executable, "-m", "geocausal.cli", "run", str(config_path)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "bounded_support" in run.stdout or "robust_support" in run.stdout or "fragile_support" in run.stdout
    assert (tmp_path / "results" / "geocausal_fixture" / "manifest.json").exists()


def test_cli_report_rebuilds_markdown(tmp_path):
    output_dir = tmp_path / "results"
    output_dir.mkdir()
    (output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "case_name": "cli_report_case",
                "robustness_interpretation": "bounded_support",
                "files": {"manifest": "manifest.json"},
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "-m", "geocausal.cli", "report", str(output_dir)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "cli_report_case" in result.stdout
    assert (output_dir / "geocausal_report.md").exists()
```

- [ ] Run CLI tests to verify they fail because `geocausal.cli` does not exist.

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_geocausal_pipeline.py -q
```

Expected:

```text
No module named geocausal.cli
```

- [ ] Implement `geocausal/cli.py`.

```python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config
from .errors import GeoCausalError
from .pipeline import diagnose_config, rebuild_report, run_analysis


SCCA_TEMPLATE = """case_name: example_scca
input:
  path: data/example.csv
  format: csv
  x: x
  y: y
variables:
  unit_id: unit_id
  exposure: exposure
  outcome: outcome
  confounders:
    - confounder
context:
  columns:
    - context
robustness:
  placebo_exposures:
    - name: placebo_check
      column: placebo
      role: negative_control
      expected_relation: weaker_than_main
  bootstrap:
    group_column: group
    n_replicates: 200
output:
  directory: results/example_scca
"""


def _cmd_init(args: argparse.Namespace) -> int:
    if args.template != "scca":
        raise GeoCausalError(f"Unsupported template: {args.template}")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(SCCA_TEMPLATE, encoding="utf-8")
    print(f"Wrote GeoCausal SCCA template: {output}")
    return 0


def _cmd_diagnose(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    diagnosis = diagnose_config(config)
    print(json.dumps(diagnosis, indent=2, ensure_ascii=False))
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    manifest = run_analysis(config)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    manifest = rebuild_report(args.output_dir)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GeoCausal SCCA command line tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Write an example analysis YAML.")
    init_parser.add_argument("--template", default="scca", help="Template name. V1 supports 'scca'.")
    init_parser.add_argument("--output", default="analysis.yaml", help="Output YAML path.")
    init_parser.set_defaults(func=_cmd_init)

    diagnose_parser = subparsers.add_parser("diagnose", help="Validate config and input data.")
    diagnose_parser.add_argument("config", help="Path to analysis YAML.")
    diagnose_parser.set_defaults(func=_cmd_diagnose)

    run_parser = subparsers.add_parser("run", help="Run an SCCA analysis from YAML.")
    run_parser.add_argument("config", help="Path to analysis YAML.")
    run_parser.set_defaults(func=_cmd_run)

    report_parser = subparsers.add_parser("report", help="Rebuild a Markdown report from a result directory.")
    report_parser.add_argument("output_dir", help="Directory containing manifest.json.")
    report_parser.set_defaults(func=_cmd_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except GeoCausalError as exc:
        print(f"GeoCausal error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] Run CLI and package tests.

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_geocausal_config.py data_agent/test_geocausal_io.py data_agent/test_geocausal_pipeline.py -q
```

Expected:

```text
15 passed
```

- [ ] Commit Task 4.

```powershell
git add geocausal/cli.py data_agent/test_geocausal_pipeline.py
git commit -m "Add GeoCausal CLI"
```

## Task 5: README and End-to-End Verification

**Files:**
- Modify `README.md`

- [ ] Add a GeoCausal section to `README.md` after the SCCA robustness section.

Use this text:

````markdown
## GeoCausal SCCA MVP

Paper6 also exposes the SCCA workflow as a first open-source framework boundary under `geocausal/`. The V1 interface is YAML-first and can be used through the module CLI:

```powershell
D:\adk\.venv\Scripts\python.exe -m geocausal.cli init --template scca --output analysis.yaml
D:\adk\.venv\Scripts\python.exe -m geocausal.cli diagnose analysis.yaml
D:\adk\.venv\Scripts\python.exe -m geocausal.cli run analysis.yaml
D:\adk\.venv\Scripts\python.exe -m geocausal.cli report results/example_scca
```

The MVP supports CSV, GeoPackage, GeoJSON, and Shapefile inputs. It writes `effect_estimates.csv`, `erf_curve.csv`, `context_ablation.csv`, `placebo_tests.csv`, `bootstrap_robustness.csv`, `bootstrap_summary.json`, `erf_stability.json`, `robustness_report.md`, and `manifest.json`.
````

- [ ] Run the new GeoCausal tests.

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_geocausal_config.py data_agent/test_geocausal_io.py data_agent/test_geocausal_pipeline.py -q
```

Expected:

```text
15 passed
```

- [ ] Run focused existing SCCA tests.

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_scca_robustness.py data_agent/test_scca_county_social_capital.py data_agent/test_scca_soho.py data_agent/test_scca_snow8.py -q
```

Expected:

```text
42 passed
```

- [ ] Run existing causal inference tests.

```powershell
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_causal_inference.py -q
```

Expected:

```text
21 passed, 1 warning
```

- [ ] Inspect git diff.

```powershell
git status -sb
git diff --stat
```

Expected:

- Modified `README.md`.
- No unexpected files.

- [ ] Commit Task 5.

```powershell
git add README.md
git commit -m "Document GeoCausal SCCA MVP"
```

## Final Step

- [ ] Run final status and log checks.

```powershell
git status -sb
git log -5 --oneline --decorate
```

Expected:

- Worktree clean.
- Latest commits include the GeoCausal config, IO, pipeline, CLI, and docs commits.

- [ ] Push when the user confirms or when continuing the same approved Paper6 workflow.

```powershell
git push origin main
git status -sb
```

Expected:

- `main` and `origin/main` aligned.

- [ ] Final response must report:
  - final commit hash,
  - push/sync status,
  - test commands and pass counts,
  - new package/CLI entry points,
  - the exact output files created by `geocausal run`.
