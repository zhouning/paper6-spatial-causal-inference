# ArcGIS Built-in Causal Inference Benchmark

This note documents the reproducible benchmark path for ArcGIS Pro's built-in **Causal Inference Analysis** tool against GeoCausal Open GIS outputs.

Official ArcGIS Pro tool reference: <https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-statistics/causal-inference-analysis.htm>

## Runtime Entry Point

Use ArcGIS Pro's `propy.bat`, not the clone environment `python.exe` directly:

```powershell
& 'D:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat' -m geocausal.cli arcgis-causal ...
```

On this machine, direct execution of
`D:\Users\zn198\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone3\python.exe`
can find ArcPy but fails license initialization with:

```text
RuntimeError: The Product License has not been initialized.
```

`propy.bat` enters the same clone environment while initializing ArcGIS Pro runtime correctly. Verified runtime:

```text
sys.executable = D:\Users\zn198\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone3\python.exe
ArcGIS Pro = 3.7
ProductInfo = ArcInfo
```

## GeoCausal CLI Wrapper

GeoCausal exposes the ArcGIS built-in benchmark through:

```powershell
& 'D:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat' -m geocausal.cli arcgis-causal `
  --input-features examples\data\county_social_capital.csv `
  --output-workspace D:\tmp\paper6_arcgis_builtin_causal_20260627\arcgis_builtin_summary.gdb `
  --output-csv-dir D:\tmp\paper6_arcgis_builtin_causal_20260627\csv_summary `
  --manifest D:\tmp\paper6_arcgis_builtin_causal_20260627\arcgis_causal_manifest_summary.json `
  --outcome-field AveAgeDeath `
  --exposure-field SocialAssoc `
  --confounders UnemployRate,pHHinPoverty,pNoHealthInsur,MentalHealth,pAdultSmoking,pAdultObesity,FastFood,pInsufficientSleep,pAlcohol,pSuicideDeaths,AirPollution `
  --output-stem county_arcgis_builtin `
  --target-outcomes 70 `
  --lower-exp-trim 0.01 `
  --upper-exp-trim 0.99 `
  --ps-method REGRESSION `
  --balancing-method MATCHING `
  --enable-erf-popups NO_POPUP `
  --create-bootstrap-ci NO_CI
```

The wrapper calls `arcpy.stats.CausalInferenceAnalysis` and writes:

- ArcGIS file geodatabase outputs: `*_features`, `*_erf`
- CSV exports for open comparison: `*_features.csv`, `*_erf.csv`
- JSON manifest with ArcGIS version, product, parameters, messages, and parsed summary metrics

## ArcPy Parameter Detail

The ArcGIS tool documents **Confounding Variables** as a value table. In ArcPy 3.7, passing a plain Python `list[list]` fails before useful geoprocessing messages are emitted. The wrapper therefore constructs:

```python
value_table = arcpy.ValueTable(2)
value_table.addRow("UnemployRate NUMERIC")
```

Categorical fields can be requested from the CLI with `FIELD_NAME:CATEGORICAL`; otherwise fields default to `NUMERIC`.

## County Benchmark Evidence

Successful real-data run on `examples/data/county_social_capital.csv`:

```json
{
  "original_n": 3108,
  "exposure_trimmed_n": 64,
  "propensity_score_trimmed_n": 0,
  "final_n": 3044,
  "selected_num_bins": 25,
  "selected_propensity_exposure_scale": 0.8,
  "bandwidth": 2.4415,
  "mean_original_correlation": 0.1898,
  "mean_weighted_correlation": 0.0559
}
```

ArcGIS output CSV checks:

- `county_arcgis_builtin_features.csv`: 3108 rows, with `RECRD_USED` marking the 3044 analysis rows.
- `county_arcgis_builtin_erf.csv`: 200 rows, with `EXPOSURE` and `RESPONSE` columns.

## ArcGIS-vs-GeoCausal Comparison Builder

After both output packages exist, build a comparison table with ordinary Python:

```powershell
python -m geocausal.cli arcgis-compare `
  --arcgis-manifest D:\tmp\paper6_arcgis_builtin_causal_20260627\arcgis_causal_manifest_final.json `
  --open-gis-dir D:\tmp\paper6_open_gis_smoke_20260627\results\open_gis_analysis_package `
  --output-dir D:\tmp\paper6_arcgis_builtin_causal_20260627\geocausal_comparison_final
```

Current real-data comparison from the same county smoke run:

```json
{
  "arcgis_final_n": 3044,
  "geocausal_joined_rows": 3044,
  "arcgis_erf_rows": 200,
  "geocausal_erf_rows": 200,
  "erf_exposure_mae": 4.263256414560601e-16,
  "erf_response_mae": 1.2736428374694144,
  "erf_response_rmse": 1.3805616459314445,
  "arcgis_mean_weighted_correlation": 0.0559,
  "geocausal_confounder_mean_abs_weighted_correlation": 0.11135132300647173,
  "geocausal_all_mean_abs_weighted_correlation": 0.09707161677961383,
  "geocausal_max_abs_weighted_correlation": 0.2178475400766404
}
```

Interpretation:

- ArcGIS and GeoCausal retain the same `3044` analysis rows after 1%/99% exposure trimming.
- ArcGIS and GeoCausal both produce a 200-row ERF table on the same exposure grid.
- The current ArcGIS ERF and GeoCausal ERF differ by `1.27` years MAE on response values.
- ArcGIS's built-in matching balance is stronger for the county confounders in this run: `0.0559` versus GeoCausal confounder mean absolute weighted correlation `0.1114`.
- GeoCausal still adds open outputs, evidence grading, spatial diagnostics, SLX/spillover checks, QGIS/browser reports, and reproducible manifests that the ArcGIS built-in tool does not provide as a single open package.