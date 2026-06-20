# GeoCausal Notebook Environment

This folder contains the Docker-backed notebook workflow for GeoCausal SCCA on macOS.

## Default example

The default notebook uses the committed county spatial data:

- `data/CountyData.shp`
- `data/States.shp`

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
  - visualizes the algorithm outputs as PNG charts, a static choropleth map, and an interactive Folium HTML map
- `run_county_social_capital_demo.py`:
  - runs the same workflow non-interactively for Docker smoke testing

## Output location

The notebook writes results under:

`paper/ijgis_submission_20260605/07_results/examples/county_social_capital_notebook_demo/`

This is separate from the committed example output directory so container runs do not overwrite tracked files by default.

## Container scope

The Docker image installs the geospatial notebook stack needed for mainstream vector outputs:

- GeoPandas/Fiona/Pyogrio/Shapely/PyProj/Rasterio for spatial I/O
- Matplotlib for static charts and maps
- Folium/Branca/Mapclassify for notebook-side web maps and choropleths

The canonical vector outputs are GeoPackage and GeoJSON. Shapefile is also written for compatibility, but its 10-character DBF field-name limit will truncate long analysis field names.
