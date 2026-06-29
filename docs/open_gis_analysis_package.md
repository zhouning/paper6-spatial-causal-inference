# Open GIS Analysis Package

GeoCausal writes an Open GIS analysis package on every successful `geocausal run`. The package is the ArcGIS-free product boundary for SCCA: ordinary CSV, JSON, and Markdown files that can be used from Python, QGIS, notebooks, Excel, BI tools, or a web GIS workflow without ArcPy or ArcGIS Pro.

This package replaces the ArcGIS dependency for the causal evidence workflow. ArcGIS can still be used as an optional map viewer or enterprise GIS shell, but it is not required to run SCCA, inspect evidence, join outputs to geometry, or audit the causal results.

## Run Without ArcGIS

From the repository root:

```bash
python -m geocausal.cli diagnose examples/county_social_capital_example.yaml
python -m geocausal.cli run examples/county_social_capital_example.yaml
```

The county example writes the Open GIS package under:

```text
paper/ijgis_submission_20260605/07_results/examples/county_social_capital_example/open_gis_analysis_package/
```

For scratch work, copy the YAML file and change only `output.directory` to an untracked folder such as `results/county_open_gis_smoke`.

## County Smoke Reference

For the committed county CSV and `examples/county_social_capital_example.yaml` settings, the current smoke expectation is:

- `diagnose` reports `original_n = 3108`, `kept_n = 3044`, and `removed_n = 64` after 1%/99% exposure trimming.
- `analysis_joined.csv` has 3044 rows and includes `gc_propensity_score`, `gc_balancing_weight`, `gc_arcgis_propensity_score`, `gc_arcgis_matching_weight`, `gc_arcgis_calibrated_weight`, and `gc_arcgis_gps_method`.
- `gis_balance_summary.csv` has 13 rows: 11 confounders plus 2 context columns, with ArcGIS-compatible mean/median/max absolute weighted-correlation fields.
- `gis_erf_curve_200.csv` has exactly 200 rows.
- `gis_arcgis_style_erf_curve_200.csv` has exactly 200 rows and records the count-weighted plug-in-bandwidth kernel ERF benchmark.
- `arcgis_style_matching_grid.csv`, `arcgis_style_balance_summary.csv`, and `arcgis_style_calibrated_balance_summary.csv` document the ArcGIS-style count matching baseline and GeoCausal calibrated balance layer.
- `gis_run_summary.json.evidence_grade` is `core_support` for this example run.
- `spatial-package` reports `row_count = 3108`, `matched_count = 3044`, and writes GeoPackage, GeoJSON, chart PNGs, map PNG/HTML, QGIS style, `open_gis_spatial_report.html`, and `spatial_output_manifest.json` when run against `data/CountyData.shp`. The report displays the run evidence grade and embeds chart/map previews for browser-only review.

## Files

| File | Purpose | Typical Use |
| --- | --- | --- |
| `analysis_joined.csv` | One retained analysis row per spatial unit, including original retained columns, `gc_unit_id`, exposure/outcome copies, generalized propensity scores, balancing weights, ArcGIS-style count matching weights, calibrated weights, selected GPS method, ArcGIS-compatible score/weight aliases, inclusion flags, and target-outcome fields when configured. | Join to a boundary layer by `gc_unit_id` or the original unit id such as `FIPS`; inspect in pandas, QGIS, Excel, or BI tools. |
| `gis_balance_summary.csv` | GIS-readable balance diagnostics for confounders and spatial context columns, with raw and weighted exposure correlations, mean/median/max absolute weighted-correlation aggregates, and a fixed `0.1` balance flag. | Audit whether adjustment reduced exposure-covariate dependence before mapping or reporting effects. |
| `gis_erf_curve_200.csv` | A 200-row exposure-response curve interpolated from the model ERF output. | Plot the default model ERF in QGIS, notebooks, dashboards, or reporting tools. |
| `gis_arcgis_style_erf_curve_200.csv` | A 200-row count-weighted kernel ERF using ArcGIS-style matching weights and a plug-in bandwidth. | Benchmark ERF parity against ArcGIS without requiring ArcPy at analysis time. |
| `arcgis_style_matching_grid.csv` | ArcGIS-style GPS matching grid search over OLS/GBM GPS methods, exposure bins, and propensity/exposure scale values, with the selected row marked. | Audit parity against ArcGIS matching behavior and benchmark selected parameters. |
| `arcgis_style_balance_summary.csv` | Balance diagnostics from the selected ArcGIS-style count matching weights. | Compare open GeoCausal count matching against ArcGIS built-in balance. |
| `arcgis_style_calibrated_balance_summary.csv` | Balance diagnostics after GeoCausal regularized calibration of the ArcGIS-style count weights. | Demonstrate the GeoCausal-only balance refinement layer intended to exceed ArcGIS balance. |
| `gis_run_summary.json` | Machine-readable run summary: case name, row counts, variables, evidence grade, generated files, and warnings. | Drive downstream automation, validation, or data-agent responses. |
| `gis_run_summary.md` | Human-readable summary for analysts and reviewers. | Attach to analysis reports or share with non-Python users. |

## Build Spatial Outputs

After `analysis_joined.csv` exists, generate an open spatial output package with one CLI command:

```bash
python -m geocausal.cli spatial-package \
  --boundary data/CountyData.shp \
  --analysis-joined results/county_open_gis_smoke/open_gis_analysis_package/analysis_joined.csv \
  --output-dir results/county_open_gis_smoke/spatial_outputs \
  --analysis-dir results/county_open_gis_smoke \
  --boundary-key FIPS \
  --analysis-key gc_unit_id \
  --states data/States.shp \
  --output-stem county_open_gis
```

The command reuses `geocausal.spatial_outputs.build_spatial_analysis_outputs` and writes open GIS deliverables such as GeoPackage, GeoJSON, Shapefile compatibility output, QGIS `.qml` styles, static PNG maps, interactive HTML maps, chart PNGs, `open_gis_spatial_report.html`, and `spatial_output_manifest.json`. The HTML report is the no-desktop-GIS browser entry point for reviewing generated files, counts, evidence grade, embedded chart/map PNGs, the embedded Folium map, and QGIS styles. When `--analysis-dir` is omitted and `--analysis-joined` is inside `open_gis_analysis_package/`, the CLI infers the parent GeoCausal run directory.

## QGIS Workflow

1. Run `python -m geocausal.cli run <config.yaml>` or use the QGIS Processing provider.
2. Add the boundary layer, for example `data/CountyData.shp`.
3. Add `open_gis_analysis_package/analysis_joined.csv` as a delimited text layer/table.
4. Join the boundary layer to the CSV using the stable unit id, for example `FIPS` on the boundary layer and `gc_unit_id` or `FIPS` in the CSV.
5. Style map layers from fields such as `gc_exposure`, `gc_outcome`, `gc_propensity_score`, `gc_balancing_weight`, `gc_arcgis_propensity_score`, `gc_arcgis_matching_weight`, `gc_arcgis_calibrated_weight`, `gc_arcgis_gps_method`, and target fields prefixed with `gc_target_`.
6. Keep `gis_balance_summary.csv` and `gis_run_summary.md` beside the map as the evidence audit trail.

## Python Workflow

```python
from pathlib import Path

import pandas as pd

package_dir = Path("results/county_open_gis_smoke/open_gis_analysis_package")
joined = pd.read_csv(package_dir / "analysis_joined.csv")
balance = pd.read_csv(package_dir / "gis_balance_summary.csv")
arcgis_style = pd.read_csv(package_dir / "arcgis_style_balance_summary.csv")
calibrated = pd.read_csv(package_dir / "arcgis_style_calibrated_balance_summary.csv")
erf = pd.read_csv(package_dir / "gis_erf_curve_200.csv")
arcgis_style_erf = pd.read_csv(package_dir / "gis_arcgis_style_erf_curve_200.csv")

print(joined[["gc_unit_id", "gc_exposure", "gc_outcome", "gc_arcgis_gps_method", "gc_arcgis_calibrated_weight"]].head())
print(balance.sort_values("absolute_weighted_correlation", ascending=False).head())
print(arcgis_style["absolute_weighted_correlation"].mean())
print(calibrated["absolute_weighted_correlation"].mean())
print(erf.shape)
print(arcgis_style_erf.shape)
```

With GeoPandas, join `analysis_joined.csv` back to a boundary layer and write an open spatial file:

```python
from pathlib import Path

import geopandas as gpd
import pandas as pd

boundary = gpd.read_file("data/CountyData.shp")
joined = pd.read_csv("results/county_open_gis_smoke/open_gis_analysis_package/analysis_joined.csv", dtype={"FIPS": "string", "gc_unit_id": "string"})
map_ready = boundary.merge(joined, left_on="FIPS", right_on="gc_unit_id", how="left")
map_ready.to_file("results/county_open_gis_smoke/county_open_gis.gpkg", layer="analysis_joined", driver="GPKG")
```

## Acceptance Checklist

A run is ready for ArcGIS-free review when these checks pass:

- `manifest.json` contains `files.open_gis_analysis_package` and `open_gis_package.package_dir`.
- `analysis_joined.csv` has the expected retained row count and non-empty `gc_unit_id` values.
- `analysis_joined.csv` includes `gc_propensity_score`, `gc_balancing_weight`, `gc_arcgis_propensity_score`, `gc_arcgis_matching_weight`, `gc_arcgis_calibrated_weight`, and `gc_arcgis_gps_method`; missing scores should be explained in `gis_run_summary.json.warnings`.
- `gis_erf_curve_200.csv` has exactly 200 rows when the source ERF has at least two valid points.
- `gis_arcgis_style_erf_curve_200.csv` has exactly 200 rows and `gis_run_summary.json.arcgis_style_erf` records bandwidth, weight sum, and effective sample size.
- `gis_balance_summary.csv` contains every configured confounder and context column that is available in the analysis frame plus ArcGIS-compatible mean/median/max balance aggregate fields.
- `gis_run_summary.json` records an evidence grade, generated-file list, selected ArcGIS-style GPS method, bins/scale, calibrated balance, calibration diagnostics, balance aggregates, and ArcGIS-style ERF diagnostics.
- The CSV can be joined back to the boundary layer by a stable unit identifier without proprietary software.

## Product Boundary

The Open GIS package is intentionally file-first. It focuses on a stable causal evidence contract instead of reproducing proprietary desktop UI behavior. The path toward exceeding ArcGIS is now explicit in the package: preserve ArcGIS-style count-matching and count-weighted ERF benchmarks for parity, then add GeoCausal-only calibrated balance, richer diagnostics, stronger open spatial outputs, QGIS/web GIS workflows, benchmarked evidence rules, and eventually a dedicated GeoCausal user interface on top of the same package.
