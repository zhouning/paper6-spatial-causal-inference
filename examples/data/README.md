# Example Data

This folder contains small public-source example inputs for GeoCausal SCCA
tooling tests, notebooks, ArcGIS Pro, and QGIS integration work.

## county_social_capital.csv

`county_social_capital.csv` is the county-level social-capital and longevity
example used to smoke-test the ArcGIS toolbox and the notebook/QGIS adapter
boundary.

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

