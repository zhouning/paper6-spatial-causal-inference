# GeoCausal Notebook Environment

This folder contains the Docker-backed notebook workflow for GeoCausal SCCA on macOS.

## Examples

Two notebook-backed examples are provided.

The county notebook uses the committed county spatial data:

- `data/CountyData.shp`
- `data/States.shp`

The Chongqing notebook uses the committed main-case analysis sample:

- `paper/ijgis_submission_20260605/07_results/chongqing_uhi_analysis_sample.csv`

## Start

From the repository root:

```bash
docker compose -f docker/notebook/docker-compose.yml up --build -d
```

Then open:

`http://localhost:8889/lab?token=geocausal`

## What is inside

- `county_social_capital_demo.ipynb`:
  - loads the county and state shapefiles
  - normalizes Shapefile-truncated county fields to the algorithm field names
  - runs `AnalysisRequest`
  - writes `analysis_joined.csv`
  - writes spatial outputs as GeoPackage, GeoJSON, and Shapefile
  - enriches the spatial files with `gc_spatial_*` direct, indirect, total, and graph-weight fields from the SLX exposure-mapping output
  - visualizes the algorithm outputs as PNG charts, static choropleth maps, and interactive Folium HTML maps
  - writes QGIS `.qml` styles for target exposure change, spatial indirect effect, and spatial total effect
- `run_county_social_capital_demo.py`:
  - runs the same workflow non-interactively for Docker smoke testing
- `chongqing_uhi_demo.ipynb`:
  - loads the Chongqing building-level UHI analysis sample
  - reruns the binary high-rise treatment PSM/ablation workflow
  - reports ATT, confidence intervals, matched counts, post-match SMD, threshold placebos, spatial block bootstrap, and residual Moran diagnostics
  - writes GIS-ready point outputs as CSV, GeoPackage, and GeoJSON
  - writes notebook-side PNG charts and an interactive Folium HTML point map
- `run_chongqing_uhi_demo.py`:
  - runs the same Chongqing workflow non-interactively for Docker smoke testing

## Output location

The county notebook writes results under:

`paper/ijgis_submission_20260605/07_results/examples/county_social_capital_notebook_demo/`

The Chongqing notebook writes results under:

`paper/ijgis_submission_20260605/07_results/examples/chongqing_uhi_notebook_demo/`

These directories are separate from committed result tables so container runs do not overwrite tracked manuscript evidence by default.

## Container scope

The Docker image installs the geospatial notebook stack needed for mainstream vector outputs:

- GeoPandas/Fiona/Pyogrio/Shapely/PyProj/Rasterio for spatial I/O
- Matplotlib for static charts and maps
- Folium/Branca/Mapclassify for notebook-side web maps and choropleths

The canonical vector outputs are GeoPackage and GeoJSON. Shapefile is also written for compatibility, but its 10-character DBF field-name limit will truncate long analysis field names.

## Spatial effect outputs

The notebook spatial manifest records:

- `spatial_outputs/county_social_capital_analysis.gpkg`
- `spatial_outputs/county_social_capital_analysis.geojson`
- `spatial_outputs/visualizations/spatial_slx_effects.png`
- `spatial_outputs/visualizations/spatial_indirect_effect_map.png`
- `spatial_outputs/visualizations/spatial_indirect_effect_map.html`
- `spatial_outputs/qgis_styles/*.qml`

The QGIS styles can be loaded onto the GeoPackage or GeoJSON layer from Layer
Properties > Symbology > Style > Load Style.

## Chongqing UHI outputs

The Chongqing notebook summary records:

- `chongqing_uhi_ablation.csv`
- `chongqing_uhi_balance.csv`
- `chongqing_uhi_matched_counts.csv`
- `chongqing_spatial_bootstrap.csv`
- `chongqing_placebo_thresholds.csv`
- `chongqing_residual_spatial_diagnostics.csv`
- `spatial_outputs/chongqing_uhi_points.gpkg`
- `spatial_outputs/chongqing_uhi_points.geojson`
- `visualizations/chongqing_uhi_att_variants.png`
- `visualizations/chongqing_uhi_balance.png`
- `visualizations/chongqing_uhi_lst_points.png`
- `visualizations/chongqing_uhi_lst_points.html`
