# GeoCausal SCCA QGIS Provider

This folder defines the QGIS Processing integration for GeoCausal SCCA.

The plugin stays thin: it exports selected QGIS layer/table attributes to a CSV,
constructs `geocausal.adapters.AnalysisRequest`, runs the shared algorithm, and
returns the generated manifest/report/joined CSV paths as Processing outputs.
The same module remains importable without QGIS so the adapter can be tested in
ordinary Python.

No Paper 6 case-study field names or dataset paths belong in this provider.

## macOS install

For the local QGIS profile, link this directory into the QGIS plugin folder:

```bash
ln -s <local checkout> \
  "<local checkout> Support/QGIS/QGIS3/profiles/default/python/plugins/geocausal_scca"
```

This has already been done on this machine.

Restart QGIS, enable `GeoCausal SCCA` in Plugin Manager, then open Processing
Toolbox and run:

```text
GeoCausal > GeoCausal SCCA Analysis
```

## County CSV smoke-test fields

For macOS/QGIS smoke testing, load the committed cross-platform table:

```text
examples/data/county_social_capital.csv
```

Use these fields:

| Parameter | Value |
| --- | --- |
| Case Name | `county_social_capital_qgis_demo` |
| Unit ID Field | `FIPS` |
| Exposure Field | `SocialAssoc` |
| Outcome Field | `AveAgeDeath` |
| Confounder Fields | `UnemployRate`, `pHHinPoverty`, `pNoHealthInsur`, `MentalHealth`, `pAdultSmoking`, `pAdultObesity`, `FastFood`, `pInsufficientSleep`, `pAlcohol`, `pSuicideDeaths`, `AirPollution` |
| Context Fields | `Shape_Length`, `Shape_Area` |
| Bootstrap Group Field | `STATE_NAME` |
| Placebo Exposure Fields | optional: `Shape_Length`, `Shape_Area` |
| Lower Exposure Quantile | `0.01` |
| Upper Exposure Quantile | `0.99` |
| Target Outcome Values | `70` |
| Bootstrap Replicates | `50` for smoke testing, `200` for a fuller run |

If no coordinate fields are supplied, the plugin writes `_gc_x` and `_gc_y`
from geometry point-on-surface/centroid when the input has geometry. For the
committed county CSV, geometry is unavailable, so `STATE_NAME` is the appropriate
bootstrap grouping field.

## County shapefile smoke-test fields

The repository also includes the Windows-generated county and state Shapefiles:

```text
data/CountyData.shp
data/States.shp
```

When running the provider directly on `CountyData.shp`, use the Shapefile DBF
field names shown by QGIS:

| Parameter | Value |
| --- | --- |
| Case Name | `county_social_capital_qgis_shp_demo` |
| Unit ID Field | `FIPS` |
| Exposure Field | `SocialAsso` |
| Outcome Field | `AveAgeDeat` |
| Confounder Fields | `UnemployRa`, `pHHinPover`, `pNoHealthI`, `MentalHeal`, `pAdultSmok`, `pAdultObes`, `FastFood`, `pInsuffici`, `pAlcohol`, `pSuicideDe`, `AirPolluti` |
| Context Fields | `Shape_Leng`, `Shape_Area` |
| Bootstrap Group Field | `STATE_NAME` |
| Placebo Exposure Fields | optional: `Shape_Leng`, `Shape_Area` |
| Lower Exposure Quantile | `0.01` |
| Upper Exposure Quantile | `0.99` |
| Target Outcome Values | `70` |
| Bootstrap Replicates | `50` for smoke testing, `200` for a fuller run |

For notebook and Python workflows, `geocausal.spatial_outputs.prepare_county_analysis_table_from_shapefile`
normalizes these truncated fields back to the full algorithm names before
running SCCA, then joins `analysis_joined.csv` back to `CountyData.shp`.

## Outputs

The case output folder contains:

- `manifest.json`
- `analysis_report.md`
- `target_exposures.csv` when target outcomes are configured
- `analysis_joined.csv` for joining back to a QGIS layer/table

`qgis_process plugins` currently exits with macOS PasteBoard/XPC errors in this
headless shell against `/Applications/QGIS-final-4_0_2.app`, so final QGIS UI
smoke testing should be done by opening QGIS.app, enabling the plugin, and using
the fields above in Processing Toolbox.
