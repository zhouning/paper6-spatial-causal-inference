# GeoCausal Integration Surfaces

GeoCausal is designed as a reusable Python algorithm package with thin adapters
for GIS and notebook environments.

## Core Boundary

The reusable boundary is:

```python
from pathlib import Path

from geocausal.adapters import AnalysisRequest, run_scca_analysis

request = AnalysisRequest(
    case_name="generic_case",
    input_path=Path("input.csv"),
    output_dir=Path("results/generic_case"),
    unit_id="unit_id",
    exposure="exposure",
    outcome="outcome",
    confounders=("confounder_1", "confounder_2"),
    context_columns=("context_1",),
    bootstrap_group="group",
    lower_exposure_quantile=0.01,
    upper_exposure_quantile=0.99,
    target_outcomes=(70.0,),
)

manifest = run_scca_analysis(request)
```

This is the integration point for notebooks, ArcGIS Pro, QGIS, and command-line
automation. It accepts field names supplied by the user and does not contain
case-study-specific defaults.

The shared core writes the same SCCA evidence package for every interface:
effect estimates, ERF tables, balance and overlap diagnostics, robustness
tables, spatial diagnostics, spatial block bootstrap, graph-sensitivity
summaries, SLX direct/indirect/total effect summaries, exposure-mapping
summaries, `manifest.json`, and `result_summary.md` when those diagnostics are
estimable from the supplied data.

The shared core also writes an Open GIS analysis package for ArcGIS-free use:
`open_gis_analysis_package/analysis_joined.csv`,
`open_gis_analysis_package/gis_balance_summary.csv`,
`open_gis_analysis_package/gis_erf_curve_200.csv`,
`open_gis_analysis_package/gis_arcgis_style_erf_curve_200.csv`,
`open_gis_analysis_package/arcgis_style_matching_grid.csv`,
`open_gis_analysis_package/arcgis_style_balance_summary.csv`,
`open_gis_analysis_package/arcgis_style_calibrated_balance_summary.csv`,
`open_gis_analysis_package/gis_run_summary.json`, and
`open_gis_analysis_package/gis_run_summary.md`. These files expose retained
analysis rows, generalized propensity scores, balancing weights, ArcGIS-style
count matching, calibrated balance summaries, the default 200-point exposure-response
curve, an ArcGIS-style count-weighted kernel ERF benchmark, spatial diagnostics,
and evidence grading through ordinary
CSV/JSON/Markdown outputs. ArcGIS Pro is an optional adapter, not a runtime
dependency for the causal evidence package. The ArcGIS-free quickstart and
acceptance checklist are maintained in `docs/open_gis_analysis_package.md`.

## Notebook Use

Notebook users can prepare a CSV or GeoPackage, construct `AnalysisRequest`, and
call `run_scca_analysis`. The output folder contains CSV/JSON/Markdown artifacts
that can be read back into pandas, GeoPandas, matplotlib, or other plotting
libraries.

The repository includes a cross-platform smoke-test CSV at:

```text
examples/data/county_social_capital.csv
```

Example notebook call:

```python
from pathlib import Path

from geocausal.adapters import AnalysisRequest, build_analysis_joined_table, run_scca_analysis

request = AnalysisRequest(
    case_name="county_social_capital_example",
    input_path=Path("examples/data/county_social_capital.csv"),
    output_dir=Path("results/county_social_capital_example"),
    unit_id="FIPS",
    exposure="SocialAssoc",
    outcome="AveAgeDeath",
    confounders=("UnemployRate", "pHHinPoverty", "pNoHealthInsur"),
    context_columns=("Shape_Length", "Shape_Area"),
    bootstrap_group="STATE_NAME",
    lower_exposure_quantile=0.01,
    upper_exposure_quantile=0.99,
    target_outcomes=(70.0,),
    bootstrap_replicates=50,
)

manifest = run_scca_analysis(request)
build_analysis_joined_table(
    input_csv=request.input_path,
    target_exposures_csv=request.output_dir / "target_exposures.csv",
    output_csv=request.output_dir / "analysis_joined.csv",
    unit_id_field="FIPS",
)
```

For the committed county Shapefiles, the notebook path is:

```python
from geocausal.spatial_outputs import (
    build_spatial_analysis_outputs,
    prepare_county_analysis_table_from_shapefile,
)

analysis_input_csv = prepare_county_analysis_table_from_shapefile(
    county_path=Path("data/CountyData.shp"),
    output_csv=Path("results/county/county_analysis_input.csv"),
)

# Run AnalysisRequest on analysis_input_csv, then build analysis_joined.csv.

spatial_manifest = build_spatial_analysis_outputs(
    boundary_path=Path("data/CountyData.shp"),
    analysis_joined_csv=Path("results/county/analysis_joined.csv"),
    analysis_dir=Path("results/county"),
    output_dir=Path("results/county/spatial_outputs"),
    states_path=Path("data/States.shp"),
)
```

This writes GeoPackage, GeoJSON, Shapefile, chart PNGs, a static choropleth PNG,
and an interactive Folium HTML map. The same builder is available from the CLI
through `python -m geocausal.cli spatial-package ...`, including `open_gis_spatial_report.html` as a browser entry point with evidence fields, embedded image previews, and an embedded Folium map. GeoPackage and GeoJSON
preserve long analysis field names; Shapefile output is compatibility-only
because DBF field names are limited to 10 characters.

When target outcomes are configured, notebook users can also build a one-row-per-
unit joined analysis table from the original input and `target_exposures.csv`:

```python
from geocausal.adapters import build_analysis_joined_table

build_analysis_joined_table(
    input_csv=Path("input.csv"),
    target_exposures_csv=Path("results/generic_case/target_exposures.csv"),
    output_csv=Path("results/generic_case/analysis_joined.csv"),
    unit_id_field="unit_id",
)
```

## ArcGIS Pro Use

ArcGIS Pro uses the Python Toolbox at:

```text
arcgis_toolbox/GeoCausalSCCA.pyt
```

The toolbox only handles ArcGIS UI parameters, ArcPy data export, and optional
copying of CSV outputs back to ArcGIS tables. It delegates algorithm execution to
`geocausal.adapters.AnalysisRequest` and reuses the same
`build_analysis_joined_table` helper to create an ArcGIS-ready analysis table.

For direct comparison against Esri's built-in Causal Inference Analysis tool,
run `python -m geocausal.cli arcgis-causal` through ArcGIS Pro `propy.bat`. The
benchmark wrapper and county smoke command are documented in
`docs/arcgis_builtin_causal_benchmark.md`.

It also validates requested fields before opening the ArcPy cursor and reports
the core spatial-diagnostic and SLX summaries in the geoprocessing messages.

The ArcGIS toolbox deliberately does not duplicate the notebook spatial-output
builder. If a user needs GeoPackage/GeoJSON/Shapefile layers, static maps,
interactive HTML maps, or QGIS styles after an ArcGIS run, call
`geocausal.spatial_outputs.build_spatial_analysis_outputs` on the exported
`analysis_joined.csv` and the original boundary feature layer.

For a reproducible toolbox smoke test, import
`examples/data/county_social_capital.csv` into a file geodatabase table and use
the fields documented in `examples/data/README.md`.

## QGIS Path

The QGIS Processing provider follows the same adapter pattern:

1. Read QGIS layer/table parameters.
2. Export selected attributes and optional geometry-derived coordinates to CSV.
3. Construct `AnalysisRequest`.
4. Call `run_scca_analysis`.
5. Build `analysis_joined.csv` from `target_exposures.csv` when target outcomes
   are requested.
6. Register generated CSV/JSON/Markdown paths as QGIS Processing outputs.

No SCCA logic should be implemented directly in a QGIS plugin. The plugin should
remain a thin adapter over `geocausal`.

The repository includes the QGIS provider at:

```text
qgis_provider/geocausal_scca_algorithm.py
```

On this macOS machine it is linked into the default QGIS profile at:

```text
/Users/zhouning/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/geocausal_scca
```

## Why This Matters

Keeping the algorithm in `geocausal` prevents three incompatible versions of the
same method from emerging across ArcGIS, QGIS, and notebooks. The GIS wrappers are
interfaces; the causal inference engine remains one tested Python package.
