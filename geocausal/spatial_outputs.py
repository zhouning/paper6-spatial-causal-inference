from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


COUNTY_SHAPEFILE_FIELD_MAP = {
    "AveAgeDeat": "AveAgeDeath",
    "SocialAsso": "SocialAssoc",
    "UnemployRa": "UnemployRate",
    "pHHinPover": "pHHinPoverty",
    "pNoHealthI": "pNoHealthInsur",
    "MentalHeal": "MentalHealth",
    "pAdultSmok": "pAdultSmoking",
    "pAdultObes": "pAdultObesity",
    "pInsuffici": "pInsufficientSleep",
    "pSuicideDe": "pSuicideDeaths",
    "AirPolluti": "AirPollution",
    "Shape_Leng": "Shape_Length",
}

COUNTY_ANALYSIS_COLUMNS = (
    "FIPS",
    "SocialAssoc",
    "AveAgeDeath",
    "STATE_NAME",
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


def _require_geopandas() -> Any:
    try:
        import geopandas as gpd
    except ImportError as exc:
        raise RuntimeError(
            "GeoPandas is required for spatial output generation. "
            "Install the Docker notebook environment or geospatial Python dependencies."
        ) from exc
    return gpd


def _safe_field_token(value: object, *, max_length: int | None = None) -> str:
    token = re.sub(r"[^0-9A-Za-z_]+", "_", str(value).strip()).strip("_")
    if not token:
        token = "field"
    if token[0].isdigit():
        token = f"f_{token}"
    if max_length is not None:
        token = token[:max_length].rstrip("_") or "field"
    return token


def normalize_join_key(series: pd.Series, *, width: int | None = None) -> pd.Series:
    values = series.astype("string").fillna("").str.strip()
    values = values.str.replace(r"\.0$", "", regex=True)
    if width is not None:
        values = values.str.zfill(width)
    return values


def _infer_key_width(*series_items: pd.Series) -> int | None:
    widths: list[int] = []
    for series in series_items:
        values = normalize_join_key(series)
        digit_values = values[values.str.fullmatch(r"\d+", na=False)]
        if not digit_values.empty:
            widths.append(int(digit_values.str.len().max()))
    return max(widths) if widths else None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def prepare_county_analysis_table_from_shapefile(
    *,
    county_path: str | Path,
    output_csv: str | Path,
    field_map: dict[str, str] | None = None,
) -> Path:
    """Export CountyData.shp attributes to the full field names expected by SCCA."""
    gpd = _require_geopandas()
    county_path = Path(county_path)
    output_csv = Path(output_csv)
    counties = gpd.read_file(county_path)
    rename_map = field_map or COUNTY_SHAPEFILE_FIELD_MAP
    table = pd.DataFrame(counties.drop(columns=getattr(counties, "geometry").name))
    table = table.rename(columns={key: value for key, value in rename_map.items() if key in table.columns})

    missing = [column for column in COUNTY_ANALYSIS_COLUMNS if column not in table.columns]
    if missing:
        raise ValueError(
            "County shapefile is missing required analysis fields after normalization: "
            + ", ".join(missing)
        )

    table = table.loc[:, list(COUNTY_ANALYSIS_COLUMNS)].copy()
    table["FIPS"] = normalize_join_key(table["FIPS"], width=5)
    for column in COUNTY_ANALYSIS_COLUMNS:
        if column not in {"FIPS", "STATE_NAME"}:
            table[column] = pd.to_numeric(table[column], errors="coerce")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output_csv, index=False, encoding="utf-8-sig")
    return output_csv


def _load_joined_spatial_frame(
    *,
    boundary_path: Path,
    analysis_joined_csv: Path,
    boundary_key: str,
    analysis_key: str,
) -> Any:
    gpd = _require_geopandas()
    boundaries = gpd.read_file(boundary_path)
    analysis = pd.read_csv(
        analysis_joined_csv,
        encoding="utf-8-sig",
        dtype={analysis_key: "string"},
    )
    if boundary_key not in boundaries.columns:
        raise ValueError(f"Boundary key field is missing from spatial data: {boundary_key}")
    if analysis_key not in analysis.columns:
        raise ValueError(f"Analysis key field is missing from joined CSV: {analysis_key}")

    width = _infer_key_width(boundaries[boundary_key], analysis[analysis_key])
    boundaries = boundaries.copy()
    analysis = analysis.copy()
    boundaries["_gc_join_key"] = normalize_join_key(boundaries[boundary_key], width=width)
    analysis["_gc_join_key"] = normalize_join_key(analysis[analysis_key], width=width)

    duplicate_count = int(analysis["_gc_join_key"].duplicated().sum())
    if duplicate_count:
        analysis = analysis.drop_duplicates(subset=["_gc_join_key"], keep="first")

    merged = boundaries.merge(
        analysis.drop(columns=[analysis_key], errors="ignore"),
        on="_gc_join_key",
        how="left",
        suffixes=("", "_analysis"),
    )
    return merged.drop(columns=["_gc_join_key"])


def _spatial_columns(frame: Any) -> list[str]:
    return [column for column in frame.columns if column != getattr(frame, "geometry").name]


def _coerce_file_frame(frame: Any) -> Any:
    result = frame.copy()
    for column in _spatial_columns(result):
        if pd.api.types.is_bool_dtype(result[column]):
            result[column] = result[column].astype(str)
        elif pd.api.types.is_object_dtype(result[column]):
            result[column] = result[column].map(
                lambda value: json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list, tuple))
                else value
            )
    return result


def _shapefile_safe_frame(frame: Any) -> Any:
    result = _coerce_file_frame(frame)
    rename: dict[str, str] = {}
    used: set[str] = set()
    for column in _spatial_columns(result):
        safe = _safe_field_token(column, max_length=10)
        base = safe[:8] if len(safe) > 8 else safe
        candidate = safe
        counter = 1
        while candidate.lower() in used:
            suffix = str(counter)
            candidate = f"{base[: 10 - len(suffix)]}{suffix}"
            counter += 1
        used.add(candidate.lower())
        if candidate != column:
            rename[column] = candidate
    return result.rename(columns=rename)


def write_spatial_files(
    frame: Any,
    *,
    output_dir: Path,
    output_stem: str,
    formats: Iterable[str] = ("gpkg", "geojson", "shp"),
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, str] = {}
    requested = {item.lower().lstrip(".") for item in formats}
    file_frame = _coerce_file_frame(frame)

    if "gpkg" in requested:
        gpkg_path = output_dir / f"{output_stem}.gpkg"
        file_frame.to_file(gpkg_path, layer="county_analysis", driver="GPKG")
        outputs["gpkg"] = str(gpkg_path)

    if "geojson" in requested:
        geojson_path = output_dir / f"{output_stem}.geojson"
        geojson_frame = file_frame.to_crs(epsg=4326) if file_frame.crs else file_frame
        geojson_frame.to_file(geojson_path, driver="GeoJSON")
        outputs["geojson"] = str(geojson_path)

    if "shp" in requested:
        shp_dir = output_dir / f"{output_stem}_shp"
        shp_dir.mkdir(parents=True, exist_ok=True)
        shp_path = shp_dir / f"{output_stem}.shp"
        _shapefile_safe_frame(file_frame).to_file(shp_path, driver="ESRI Shapefile", encoding="UTF-8")
        outputs["shp"] = str(shp_path)

    return outputs


def _load_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def _plot_erf_curve(erf_curve: pd.DataFrame, output_path: Path) -> str | None:
    if erf_curve.empty or not {"exposure", "response"}.issubset(erf_curve.columns):
        return None
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    curve = erf_curve[["exposure", "response"]].apply(pd.to_numeric, errors="coerce").dropna()
    if curve.empty:
        return None
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(curve["exposure"], curve["response"], color="#1f6f8b", linewidth=2.2)
    ax.set_xlabel("Exposure")
    ax.set_ylabel("Estimated outcome response")
    ax.set_title("Exposure-response curve")
    ax.grid(True, color="#d9d9d9", linewidth=0.6)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return str(output_path)


def _plot_effect_estimates(effect_estimates: pd.DataFrame, output_path: Path) -> str | None:
    if effect_estimates.empty or "estimator" not in effect_estimates.columns:
        return None
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    estimates = effect_estimates.copy()
    estimates["coef"] = pd.to_numeric(estimates.get("coef"), errors="coerce")
    estimates["ci_lower"] = pd.to_numeric(estimates.get("ci_lower"), errors="coerce")
    estimates["ci_upper"] = pd.to_numeric(estimates.get("ci_upper"), errors="coerce")
    estimates = estimates.dropna(subset=["coef"]).reset_index(drop=True)
    if estimates.empty:
        return None
    y = list(range(len(estimates)))
    lower = (estimates["coef"] - estimates["ci_lower"]).clip(lower=0)
    upper = (estimates["ci_upper"] - estimates["coef"]).clip(lower=0)
    has_ci = lower.notna() & upper.notna()
    error_x = estimates.loc[has_ci, "coef"].to_numpy(dtype=float)
    error_y = [y[index] for index in estimates.index[has_ci]]
    error_lower = lower.loc[has_ci].to_numpy(dtype=float)
    error_upper = upper.loc[has_ci].to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(8, max(3.5, 0.6 * len(estimates) + 1.6)))
    ax.barh(y, estimates["coef"], color="#496a81")
    if has_ci.any():
        ax.errorbar(
            error_x,
            error_y,
            xerr=[error_lower, error_upper],
            fmt="none",
            ecolor="#1d2327",
            elinewidth=1,
            capsize=3,
        )
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(estimates["estimator"])
    ax.set_xlabel("Estimated coefficient")
    ax.set_title("Effect estimates")
    ax.grid(True, axis="x", color="#d9d9d9", linewidth=0.6)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return str(output_path)


def _plot_exposure_change_distribution(frame: Any, map_field: str, output_path: Path) -> str | None:
    if map_field not in frame.columns:
        return None
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    values = pd.to_numeric(frame[map_field], errors="coerce").dropna()
    if values.empty:
        return None
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(values, bins=32, color="#637f4f", edgecolor="white", linewidth=0.4)
    ax.axvline(0, color="#333333", linewidth=0.9)
    ax.set_xlabel(map_field)
    ax.set_ylabel("County count")
    ax.set_title("Target exposure-change distribution")
    ax.grid(True, axis="y", color="#d9d9d9", linewidth=0.6)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return str(output_path)


def _plot_static_map(
    frame: Any,
    *,
    map_field: str,
    output_path: Path,
    states_path: Path | None = None,
) -> str | None:
    if map_field not in frame.columns:
        return None
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    values = pd.to_numeric(frame[map_field], errors="coerce")
    if values.notna().sum() == 0:
        return None
    plot_frame = frame.copy()
    plot_frame[map_field] = values
    fig, ax = plt.subplots(figsize=(12, 8))
    plot_frame.plot(
        column=map_field,
        cmap="RdBu_r",
        legend=True,
        linewidth=0.08,
        edgecolor="#ffffff",
        missing_kwds={"color": "#efefef", "edgecolor": "#ffffff", "hatch": "///"},
        ax=ax,
    )
    if states_path and states_path.exists():
        try:
            states = _require_geopandas().read_file(states_path)
            if states.crs != plot_frame.crs and plot_frame.crs is not None:
                states = states.to_crs(plot_frame.crs)
            states.boundary.plot(ax=ax, color="#303030", linewidth=0.35)
        except Exception:
            pass
    ax.set_axis_off()
    ax.set_title("County target exposure change", pad=12)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return str(output_path)


def _map_center(frame: Any) -> tuple[float, float]:
    bounds = frame.total_bounds
    if len(bounds) != 4 or any(not math.isfinite(float(value)) for value in bounds):
        return 39.5, -98.35
    minx, miny, maxx, maxy = (float(value) for value in bounds)
    return (miny + maxy) / 2.0, (minx + maxx) / 2.0


def _write_interactive_map(frame: Any, *, map_field: str, output_path: Path) -> str | None:
    if map_field not in frame.columns:
        return None
    values = pd.to_numeric(frame[map_field], errors="coerce")
    if values.notna().sum() == 0:
        return None

    import branca.colormap as cm
    import folium

    map_frame = frame.copy()
    map_frame[map_field] = values
    map_frame = map_frame.to_crs(epsg=4326) if map_frame.crs else map_frame
    map_frame = map_frame.loc[map_frame.geometry.notna()].copy()
    map_frame = map_frame.loc[~map_frame.geometry.is_empty].copy()
    if map_frame.empty:
        return None
    map_frame["geometry"] = map_frame.geometry.simplify(0.01, preserve_topology=True)

    valid = map_frame[map_field].dropna()
    min_value = float(valid.min())
    max_value = float(valid.max())
    if min_value == max_value:
        max_value = min_value + 1.0
    color_map = cm.LinearColormap(
        ["#2f5d8c", "#f7f7f2", "#b84a3a"],
        vmin=min_value,
        vmax=max_value,
    )
    color_map.caption = map_field
    fmap = folium.Map(location=_map_center(map_frame), zoom_start=4, tiles="cartodbpositron")

    def style_function(feature: dict[str, Any]) -> dict[str, Any]:
        value = feature.get("properties", {}).get(map_field)
        if value is None:
            return {"fillColor": "#d9d9d9", "color": "#ffffff", "weight": 0.2, "fillOpacity": 0.25}
        return {
            "fillColor": color_map(float(value)),
            "color": "#ffffff",
            "weight": 0.2,
            "fillOpacity": 0.72,
        }

    tooltip_fields = [
        column
        for column in ("STATE_NAME", "County", "FIPS", map_field)
        if column in map_frame.columns
    ]
    folium.GeoJson(
        map_frame.to_json(),
        name="County analysis",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(fields=tooltip_fields) if tooltip_fields else None,
    ).add_to(fmap)
    color_map.add_to(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fmap.save(output_path)
    return str(output_path)


def write_analysis_visualizations(
    *,
    analysis_dir: str | Path,
    spatial_frame: Any,
    output_dir: str | Path,
    map_field: str = "gc_target_70_exposure_change",
    states_path: str | Path | None = None,
) -> dict[str, str]:
    analysis_dir = Path(analysis_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    states = Path(states_path) if states_path else None
    outputs: dict[str, str] = {}

    erf = _plot_erf_curve(
        _load_csv_if_exists(analysis_dir / "erf_curve.csv"),
        output_dir / "erf_curve.png",
    )
    if erf:
        outputs["erf_curve_png"] = erf
    effects = _plot_effect_estimates(
        _load_csv_if_exists(analysis_dir / "effect_estimates.csv"),
        output_dir / "effect_estimates.png",
    )
    if effects:
        outputs["effect_estimates_png"] = effects
    histogram = _plot_exposure_change_distribution(
        spatial_frame,
        map_field,
        output_dir / "target_exposure_change_histogram.png",
    )
    if histogram:
        outputs["target_exposure_change_histogram_png"] = histogram
    static_map = _plot_static_map(
        spatial_frame,
        map_field=map_field,
        output_path=output_dir / "target_exposure_change_map.png",
        states_path=states,
    )
    if static_map:
        outputs["target_exposure_change_map_png"] = static_map
    interactive_map = _write_interactive_map(
        spatial_frame,
        map_field=map_field,
        output_path=output_dir / "target_exposure_change_map.html",
    )
    if interactive_map:
        outputs["target_exposure_change_map_html"] = interactive_map
    return outputs


def build_spatial_analysis_outputs(
    *,
    boundary_path: str | Path,
    analysis_joined_csv: str | Path,
    output_dir: str | Path,
    analysis_dir: str | Path | None = None,
    boundary_key: str = "FIPS",
    analysis_key: str = "FIPS",
    output_stem: str = "county_social_capital_analysis",
    formats: Iterable[str] = ("gpkg", "geojson", "shp"),
    states_path: str | Path | None = None,
    map_field: str = "gc_target_70_exposure_change",
) -> dict[str, Any]:
    boundary_path = Path(boundary_path)
    analysis_joined_csv = Path(analysis_joined_csv)
    output_dir = Path(output_dir)
    analysis_dir_path = Path(analysis_dir) if analysis_dir else analysis_joined_csv.parent

    joined_frame = _load_joined_spatial_frame(
        boundary_path=boundary_path,
        analysis_joined_csv=analysis_joined_csv,
        boundary_key=boundary_key,
        analysis_key=analysis_key,
    )
    spatial_files = write_spatial_files(
        joined_frame,
        output_dir=output_dir,
        output_stem=output_stem,
        formats=formats,
    )
    visualization_dir = output_dir / "visualizations"
    visualizations = write_analysis_visualizations(
        analysis_dir=analysis_dir_path,
        spatial_frame=joined_frame,
        output_dir=visualization_dir,
        map_field=map_field,
        states_path=states_path,
    )
    manifest = {
        "boundary_path": str(boundary_path),
        "analysis_joined_csv": str(analysis_joined_csv),
        "analysis_dir": str(analysis_dir_path),
        "row_count": int(len(joined_frame)),
        "matched_count": int(joined_frame[map_field].notna().sum()) if map_field in joined_frame.columns else None,
        "crs": str(joined_frame.crs) if joined_frame.crs is not None else None,
        "map_field": map_field,
        "spatial_files": spatial_files,
        "visualizations": visualizations,
    }
    manifest_path = output_dir / "spatial_output_manifest.json"
    _write_json(manifest_path, manifest)
    manifest["manifest"] = str(manifest_path)
    return manifest
