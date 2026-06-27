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
- `analysis_joined.csv` has 3044 rows and includes `gc_propensity_score` plus `gc_balancing_weight`.
- `gis_balance_summary.csv` has 13 rows: 11 confounders plus 2 context columns.
- `gis_erf_curve_200.csv` has exactly 200 rows.
- `gis_run_summary.json.evidence_grade` is `core_support` for this example run.
- `spatial-package` reports `row_count = 3108`, `matched_count = 3044`, and writes GeoPackage, GeoJSON, chart PNGs, map PNG/HTML, QGIS style, `open_gis_spatial_report.html`, and `spatial_output_manifest.json` when run against `data/CountyData.shp`.

## Files

| File | Purpose | Typical Use |
| --- | --- | --- |
| `analysis_joined.csv` | One retained analysis row per spatial unit, including original retained columns, `gc_unit_id`, exposure/outcome copies, generalized propensity scores, balancing weights, inclusion flags, and target-outcome fields when configured. | Join to a boundary layer by `gc_unit_id` or the original unit id such as `FIPS`; inspect in pandas, QGIS, Excel, or BI tools. |
| `gis_balance_summary.csv` | GIS-readable balance diagnostics for confounders and spatial context columns, with raw and weighted exposure correlations and a fixed `0.1` balance flag. | Audit whether adjustment reduced exposure-covariate dependence before mapping or reporting effects. |
| `gis_erf_curve_200.csv` | A 200-row exposure-response curve interpolated from the model ERF output. | Plot a stable curve in QGIS, notebooks, dashboards, or reporting tools. |
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

The command reuses `geocausal.spatial_outputs.build_spatial_analysis_outputs` and writes open GIS deliverables such as GeoPackage, GeoJSON, Shapefile compatibility output, QGIS `.qml` styles, static PNG maps, interactive HTML maps, chart PNGs, `open_gis_spatial_report.html`, and `spatial_output_manifest.json`. The HTML report is the no-desktop-GIS browser entry point for reviewing generated files, counts, map assets, and QGIS styles. When `--analysis-dir` is omitted and `--analysis-joined` is inside `open_gis_analysis_package/`, the CLI infers the parent GeoCausal run directory.

## QGIS Workflow

1. Run `python -m geocausal.cli run <config.yaml>` or use the QGIS Processing provider.
2. Add the boundary layer, for example `data/CountyData.shp`.
3. Add `open_gis_analysis_package/analysis_joined.csv` as a delimited text layer/table.
4. Join the boundary layer to the CSV using the stable unit id, for example `FIPS` on the boundary layer and `gc_unit_id` or `FIPS` in the CSV.
5. Style map layers from fields such as `gc_exposure`, `gc_outcome`, `gc_propensity_score`, `gc_balancing_weight`, and target fields prefixed with `gc_target_`.
6. Keep `gis_balance_summary.csv` and `gis_run_summary.md` beside the map as the evidence audit trail.

## Python Workflow

```python
from pathlib import Path

import pandas as pd

package_dir = Path("results/county_open_gis_smoke/open_gis_analysis_package")
joined = pd.read_csv(package_dir / "analysis_joined.csv")
balance = pd.read_csv(package_dir / "gis_balance_summary.csv")
erf = pd.read_csv(package_dir / "gis_erf_curve_200.csv")

print(joined[["gc_unit_id", "gc_exposure", "gc_outcome", "gc_balancing_weight"]].head())
print(balance.sort_values("absolute_weighted_correlation", ascending=False).head())
print(erf.shape)
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
- `analysis_joined.csv` includes `gc_propensity_score` and `gc_balancing_weight`; missing scores should be explained in `gis_run_summary.json.warnings`.
- `gis_erf_curve_200.csv` has exactly 200 rows when the source ERF has at least two valid points.
- `gis_balance_summary.csv` contains every configured confounder and context column that is available in the analysis frame.
- `gis_run_summary.json` records an evidence grade and generated-file list.
- The CSV can be joined back to the boundary layer by a stable unit identifier without proprietary software.

## Product Boundary

The Open GIS package is intentionally file-first. It focuses on a stable causal evidence contract instead of reproducing proprietary desktop UI behavior. The path toward exceeding ArcGIS is to keep strengthening this shared core: richer diagnostics, stronger open spatial outputs, QGIS/web GIS workflows, benchmarked evidence rules, and eventually a dedicated GeoCausal user interface on top of the same package.
