# Example Data

This folder contains small public-source example inputs for GeoCausal SCCA
tooling tests, notebooks, ArcGIS Pro, and QGIS integration work.

## county_social_capital.csv

`county_social_capital.csv` is the county-level social-capital and longevity
example used to smoke-test the ArcGIS toolbox and the notebook/QGIS adapter
boundary.

This is third-party training/demo data, not author-generated data. It is a
plain-table derivative of the `data/CountyData.*` example shapefile so the same
workflow can run without ArcPy on Windows, macOS, and Linux.

- Rows: 3108
- Unit ID: `FIPS`
- Exposure: `SocialAssoc`
- Outcome: `AveAgeDeath`
- Bootstrap group: `STATE_NAME`
- Suggested confounders:
  - `UnemployRate`
  - `pHHinPoverty`
  - `pNoHealthInsur`
  - `MentalHealth`
  - `pAdultSmoking`
  - `pAdultObesity`
  - `FastFood`
  - `pInsufficientSleep`
  - `pAlcohol`
  - `pSuicideDeaths`
  - `AirPollution`
- Suggested context fields:
  - `Shape_Length`
  - `Shape_Area`
- Suggested exposure trimming:
  - lower quantile: `0.01`
  - upper quantile: `0.99`
- Suggested target outcome:
  - `70`

This CSV is intentionally committed as a plain table so it can be used on
Windows, macOS, and Linux without ArcPy. ArcGIS Pro users can import it into a
file geodatabase before running `arcgis_toolbox/GeoCausalSCCA.pyt`; notebook and
QGIS users can read it directly.

## Original Small Reproduction Inputs

These files are committed so the Windows-tested SCCA reproduction cases can run
from a clean checkout on macOS or Linux without local absolute paths:

- `county/CountyData_TableToExcel.xlsx`
  - SHA256: `07766ff7e32899b538bba6b1b57eff351b67ad371a7db519895d177a3f871941`
  - Used by `python -m data_agent.experiments.run_scca_county_social_capital --workbook-path examples/data/county/CountyData_TableToExcel.xlsx`
- `snow8/subdistricts.csv`
  - SHA256: `6ff18b96dd9b48dcfe70873067dff0da2e479dd4172f75e64ce31ca0e9809c66`
  - Used by `python -m data_agent.experiments.run_scca_snow8 --csv-path examples/data/snow8/subdistricts.csv`
- `snow1/deaths_nd_by_house.csv`
  - SHA256: `1767706cd333276e9530eec7a8454203470a5a3aa13b9e812410727e10a38b86`
  - Used by `python -m data_agent.experiments.run_scca_soho --csv-path examples/data/snow1/deaths_nd_by_house.csv`

## Source and Use Terms

The source shapefile metadata in `data/CountyData.shp.xml` credits Esri, the
U.S. Census Bureau, NOAA/NOS/NGS, CDC WONDER/NCHS, County Health Rankings 2019,
ArcGIS Living Atlas of the World, the University of Wisconsin Population Health
Institute, and the Robert Wood Johnson Foundation. The average-age-at-death and
cause-of-death variables are derived from CDC WONDER Underlying Cause of Death
data. Smoking, obesity, physical inactivity, social capital, and air pollution
variables are from 2019 County Health Rankings through ArcGIS Living Atlas.

Use is governed by the Esri Master License and is restricted to training,
demonstration, and educational purposes. The metadata states that the data
cannot be sold or used for marketing without Esri's express written consent.
Keep the source metadata with redistributed copies and verify the source terms
before any public archival data release.
