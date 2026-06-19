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


def test_load_config_rejects_malformed_yaml(tmp_path):
    config_path = _write_yaml(
        tmp_path / "bad.yaml",
        """
case_name: bad_case
input:
  path: fixture.csv
  x: x
  y: y
variables
  exposure: exposure
  outcome: outcome
output:
  directory: results/bad
""",
    )
    with pytest.raises(GeoCausalConfigError, match="Invalid YAML|cannot parse"):
        load_config(config_path)


def test_load_config_rejects_incomplete_coordinate_pairs(tmp_path):
    only_x = _write_yaml(
        tmp_path / "only_x.yaml",
        """
case_name: only_x_case
input:
  path: fixture.csv
  x: x
variables:
  exposure: exposure
  outcome: outcome
output:
  directory: results/only_x
""",
    )
    mixed = _write_yaml(
        tmp_path / "mixed.yaml",
        """
case_name: mixed_case
input:
  path: fixture.csv
  x: x
  lat: latitude
variables:
  exposure: exposure
  outcome: outcome
output:
  directory: results/mixed
""",
    )
    with pytest.raises(GeoCausalConfigError, match="coordinate columns.*x/y or lon/lat"):
        load_config(only_x)
    with pytest.raises(GeoCausalConfigError, match="coordinate columns.*x/y or lon/lat"):
        load_config(mixed)


def test_load_config_rejects_extra_partial_coordinate_pair(tmp_path):
    config_path = _write_yaml(
        tmp_path / "extra_partial.yaml",
        """
case_name: extra_partial_case
input:
  path: fixture.csv
  x: x
  y: y
  lat: latitude
variables:
  exposure: exposure
  outcome: outcome
output:
  directory: results/extra_partial
""",
    )
    with pytest.raises(GeoCausalConfigError, match="coordinate columns.*x/y or lon/lat"):
        load_config(config_path)


def test_load_config_accepts_explicit_json_geojson_alias(tmp_path):
    config_path = _write_yaml(
        tmp_path / "analysis.yaml",
        """
case_name: json_case
input:
  path: fixture.json
  format: json
variables:
  exposure: exposure
  outcome: outcome
output:
  directory: results/json
""",
    )
    config = load_config(config_path)
    assert config.input.format == "geojson"


def test_validate_config_rejects_boolean_n_replicates(tmp_path):
    config_path = _write_yaml(
        tmp_path / "analysis.yaml",
        """
case_name: bool_case
input:
  path: fixture.csv
  x: x
  y: y
variables:
  exposure: exposure
  outcome: outcome
robustness:
  bootstrap:
    n_replicates: true
output:
  directory: results/bool
""",
    )
    with pytest.raises(GeoCausalConfigError, match="n_replicates"):
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
