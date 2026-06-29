"""EPA nonattainment x AirData benchmark helpers for Paper 6 SCCA validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


@dataclass(frozen=True)
class SyntheticScenario:
    """A semi-synthetic validation frame and its known-effect metadata."""

    name: str
    frame: pd.DataFrame
    metadata: dict[str, Any]


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in normalized.columns
    ]
    return normalized


def _require_columns(frame: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def _fips_part(value: Any, width: int) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(width)


def aggregate_airdata_county_year(
    raw: pd.DataFrame,
    *,
    pollutant_code: int,
) -> pd.DataFrame:
    """Aggregate annual monitor-level AirData rows to county-year outcomes."""

    frame = _normalize_columns(raw)
    _require_columns(
        frame,
        [
            "state_code",
            "county_code",
            "parameter_code",
            "year",
            "arithmetic_mean",
            "observation_count",
        ],
    )
    frame = frame.loc[
        pd.to_numeric(frame["parameter_code"], errors="coerce") == int(pollutant_code)
    ].copy()
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "county_fips",
                "year",
                "pollutant_code",
                "annual_mean",
                "monitor_count",
                "observation_count",
            ]
        )

    frame["county_fips"] = [
        _fips_part(state, 2) + _fips_part(county, 3)
        for state, county in zip(frame["state_code"], frame["county_code"], strict=False)
    ]
    frame["year"] = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")
    frame["arithmetic_mean"] = pd.to_numeric(frame["arithmetic_mean"], errors="coerce")
    frame["observation_count"] = pd.to_numeric(
        frame["observation_count"], errors="coerce"
    ).fillna(0)
    frame = frame.dropna(subset=["year", "arithmetic_mean"])
    frame = frame.loc[frame["observation_count"] > 0].copy()

    rows: list[dict[str, Any]] = []
    for (county_fips, year), group in frame.groupby(["county_fips", "year"], sort=True):
        weights = group["observation_count"].astype(float)
        annual_mean = float((group["arithmetic_mean"] * weights).sum() / weights.sum())
        rows.append(
            {
                "county_fips": str(county_fips),
                "year": int(year),
                "pollutant_code": int(pollutant_code),
                "annual_mean": annual_mean,
                "monitor_count": int(len(group)),
                "observation_count": int(weights.sum()),
            }
        )
    return pd.DataFrame(rows)


def expand_nonattainment_periods(
    periods: pd.DataFrame,
    *,
    years: Iterable[int],
) -> pd.DataFrame:
    """Expand county nonattainment periods to a complete county-year indicator."""

    frame = _normalize_columns(periods)
    _require_columns(frame, ["county_fips", "start_year", "end_year"])
    year_values = sorted(int(year) for year in years)
    if not year_values:
        return pd.DataFrame(columns=["county_fips", "year", "nonattainment"])

    county_ids = sorted(str(value).zfill(5) for value in frame["county_fips"].dropna().unique())
    status = {
        (county_fips, year): 0
        for county_fips in county_ids
        for year in year_values
    }
    max_year = max(year_values)
    for row in frame.itertuples(index=False):
        county_fips = str(getattr(row, "county_fips")).zfill(5)
        start_year = pd.to_numeric(pd.Series([getattr(row, "start_year")]), errors="coerce").iloc[0]
        end_year = pd.to_numeric(pd.Series([getattr(row, "end_year")]), errors="coerce").iloc[0]
        if pd.isna(start_year):
            continue
        start = int(start_year)
        end = max_year if pd.isna(end_year) else int(end_year)
        for year in year_values:
            if start <= year <= end:
                status[(county_fips, year)] = 1

    rows = [
        {"county_fips": county_fips, "year": year, "nonattainment": value}
        for (county_fips, year), value in sorted(status.items())
    ]
    return pd.DataFrame(rows)


def add_neighbor_exposure(
    panel: pd.DataFrame,
    adjacency: dict[str, list[str]],
    *,
    exposure_col: str,
    output_col: str | None = None,
) -> pd.DataFrame:
    """Add same-year mean neighboring exposure from a county adjacency mapping."""

    frame = panel.copy()
    _require_columns(frame, ["county_fips", "year", exposure_col])
    neighbor_col = output_col or f"neighbor_{exposure_col}"
    lookup = {
        (str(row.county_fips).zfill(5), int(row.year)): float(getattr(row, exposure_col))
        for row in frame.itertuples(index=False)
        if not pd.isna(getattr(row, exposure_col))
    }
    values: list[float] = []
    for row in frame.itertuples(index=False):
        county_fips = str(row.county_fips).zfill(5)
        year = int(row.year)
        neighbor_values = [
            lookup[(str(neighbor).zfill(5), year)]
            for neighbor in adjacency.get(county_fips, [])
            if (str(neighbor).zfill(5), year) in lookup
        ]
        values.append(float(sum(neighbor_values) / len(neighbor_values)) if neighbor_values else 0.0)
    frame[neighbor_col] = values
    return frame


def prepare_epa_panel(
    airdata: pd.DataFrame,
    nonattainment: pd.DataFrame,
    centroids: pd.DataFrame,
    *,
    adjacency: dict[str, list[str]],
) -> pd.DataFrame:
    """Merge EPA outcomes, nonattainment status, and spatial context into a panel."""

    air = _normalize_columns(airdata)
    status = _normalize_columns(nonattainment)
    xy = _normalize_columns(centroids)
    _require_columns(
        air,
        [
            "county_fips",
            "year",
            "pollutant_code",
            "annual_mean",
            "monitor_count",
            "observation_count",
        ],
    )
    _require_columns(status, ["county_fips", "year", "nonattainment"])
    _require_columns(xy, ["county_fips", "x", "y"])

    for frame in (air, status, xy):
        frame["county_fips"] = frame["county_fips"].map(lambda value: str(value).zfill(5))
    air["year"] = pd.to_numeric(air["year"], errors="coerce").astype(int)
    status["year"] = pd.to_numeric(status["year"], errors="coerce").astype(int)

    panel = air.merge(status, on=["county_fips", "year"], how="left")
    panel["nonattainment"] = pd.to_numeric(panel["nonattainment"], errors="coerce").fillna(0).astype(int)
    panel = panel.merge(xy[["county_fips", "x", "y"]], on="county_fips", how="left")
    panel = panel.sort_values(["county_fips", "year"]).reset_index(drop=True)
    panel["baseline_annual_mean"] = panel.groupby("county_fips")["annual_mean"].shift(1)
    panel["nonattainment_lag1"] = panel.groupby("county_fips")["nonattainment"].shift(1)
    panel["year_index"] = panel["year"] - int(panel["year"].min())
    panel["county_year_id"] = panel["county_fips"] + "_" + panel["year"].astype(str)
    panel = add_neighbor_exposure(
        panel,
        adjacency,
        exposure_col="nonattainment_lag1",
        output_col="neighbor_nonattainment_lag1",
    )
    numeric = [
        "annual_mean",
        "baseline_annual_mean",
        "monitor_count",
        "observation_count",
        "x",
        "y",
        "nonattainment_lag1",
        "neighbor_nonattainment_lag1",
        "year_index",
    ]
    for column in numeric:
        panel[column] = pd.to_numeric(panel[column], errors="coerce")
    return panel.dropna(
        subset=[
            "annual_mean",
            "baseline_annual_mean",
            "nonattainment_lag1",
            "x",
            "y",
        ]
    ).reset_index(drop=True)


def make_semisynthetic_scenarios(
    panel: pd.DataFrame,
    *,
    true_effect: float = -1.0,
) -> dict[str, SyntheticScenario]:
    """Create deterministic known-effect outcomes on real or fixture geography."""

    base = panel.copy()
    required = [
        "baseline_annual_mean",
        "nonattainment_lag1",
        "neighbor_nonattainment_lag1",
        "x",
        "y",
        "year_index",
    ]
    _require_columns(base, required)
    for column in required:
        base[column] = pd.to_numeric(base[column], errors="coerce").fillna(0.0)

    x_centered = base["x"] - base["x"].mean()
    y_centered = base["y"] - base["y"].mean()
    x_scaled = x_centered / (x_centered.std(ddof=0) or 1.0)
    y_scaled = y_centered / (y_centered.std(ddof=0) or 1.0)
    secular = 0.03 * base["year_index"]
    context = 0.08 * x_scaled - 0.05 * y_scaled
    stable = base.copy()
    stable["synthetic_outcome"] = (
        stable["baseline_annual_mean"]
        + true_effect * stable["nonattainment_lag1"]
        + secular
        + context
    )
    confounded = stable.copy()
    latent_spatial_risk = 0.45 * x_scaled + 0.35 * y_scaled
    confounded["synthetic_outcome"] = stable["synthetic_outcome"] + latent_spatial_risk
    spillover = stable.copy()
    spillover_effect = true_effect * 0.6
    spillover["synthetic_outcome"] = (
        stable["synthetic_outcome"]
        + spillover_effect * spillover["neighbor_nonattainment_lag1"]
    )

    return {
        "stable_known_effect": SyntheticScenario(
            name="stable_known_effect",
            frame=stable,
            metadata={"true_effect": true_effect, "scenario_role": "recoverable"},
        ),
        "spatial_confounding": SyntheticScenario(
            name="spatial_confounding",
            frame=confounded,
            metadata={"true_effect": true_effect, "scenario_role": "spatial_confounding"},
        ),
        "spillover": SyntheticScenario(
            name="spillover",
            frame=spillover,
            metadata={
                "true_effect": true_effect,
                "spillover_effect": spillover_effect,
                "scenario_role": "neighbor_spillover",
            },
        ),
    }


def write_geocausal_config(
    *,
    panel_path: str | Path,
    output_dir: str | Path,
    config_path: str | Path,
    outcome: str = "annual_mean",
) -> Path:
    """Write a minimal GeoCausal YAML config for the EPA benchmark panel."""

    target = Path(config_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = f"""case_name: epa_nonattainment_airdata
input:
  path: {Path(panel_path).resolve().as_posix()}
  x: x
  y: y
variables:
  unit_id: county_year_id
  exposure: nonattainment_lag1
  outcome: {outcome}
  baseline_outcome: baseline_annual_mean
  confounders:
    - baseline_annual_mean
    - monitor_count
    - year_index
context:
  columns:
    - x
    - y
    - neighbor_nonattainment_lag1
robustness:
  bootstrap:
    group_column: county_fips
    n_replicates: 50
  placebo_exposures:
    - name: neighbor_nonattainment_lag1
      column: neighbor_nonattainment_lag1
      role: spatial_neighbor_exposure
      expected_relation: weaker_than_main
output:
  directory: {Path(output_dir).resolve().as_posix()}
"""
    target.write_text(text, encoding="utf-8")
    return target
