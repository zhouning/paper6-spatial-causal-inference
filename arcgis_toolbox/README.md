# GeoCausal SCCA ArcGIS Toolbox

This folder contains an ArcGIS Pro Python Toolbox wrapper for the generic
GeoCausal SCCA framework.

## Tool

- Toolbox file: `GeoCausalSCCA.pyt`
- Tool label: `GeoCausal SCCA Analysis`

The toolbox is generic. It does not hard-code any Paper 6 case-study fields. The
user must choose the exposure, outcome, confounders, context fields, optional
grouping fields, and optional target outcome values in the ArcGIS Pro dialog.

## ArcGIS Pro Setup

1. Open ArcGIS Pro.
2. In Catalog, add this folder as a folder connection.
3. Browse to `arcgis_toolbox/GeoCausalSCCA.pyt`.
4. Open `GeoCausal SCCA Analysis`.
5. Choose the input features or table and field parameters.

The toolbox exports the selected ArcGIS table/features to a temporary CSV in the
chosen output folder, writes a GeoCausal YAML configuration, runs the GeoCausal
pipeline, and writes the output artifacts under the run subfolder
`<Output Report Folder>\<Case Name>\`.

When the input is a feature layer and X/Y fields are not supplied, the toolbox
derives `_gc_x` and `_gc_y` from feature centroids so the shared SCCA core can
run coordinate-based spatial diagnostics. When X/Y fields are supplied manually,
the toolbox validates that both fields exist and preserves them in the exported
CSV.

## Chinese Example Manuals

Chinese step-by-step manuals for the county social-capital example:

- `ArcGIS_Pro_使用手册_县域社会资本示例.md`
- `ArcGIS_Pro_quickstart_county_social_capital_zh.md`
- `ArcGIS_Pro_workflow_county_social_capital_zh.md`
- `ArcGIS_Pro_choropleth_join_county_social_capital_zh.md`
- `ArcGIS_Pro_layout_export_county_social_capital_zh.md`

The example input table is committed at:

```text
examples/data/county_social_capital.csv
```

For ArcGIS Pro, import that CSV into a file geodatabase first, then use the
field settings in `examples/data/README.md`. The same CSV can also be used
directly from notebooks and QGIS-side smoke tests.

## Main Parameters

- `Input Features or Table`: Any ArcGIS table or feature layer readable by ArcPy.
- `Case Name`: Output subfolder and run identifier.
- `Unit ID Field`: Optional stable feature/table identifier.
- `Exposure Field`: Continuous treatment/exposure variable.
- `Outcome Field`: Continuous outcome variable.
- `Confounding Variables`: Optional observed confounders.
- `Context Fields`: Optional spatial/context covariates.
- `Bootstrap Group Field`: Optional grouping field for grouped bootstrap.
- `Placebo Exposure Fields`: Optional negative-control or placebo exposures.
- `Lower/Upper Exposure Quantile`: Optional exposure trimming, default `0.01` and
  `0.99`.
- `Target Outcome Values`: Optional target outcomes for required-exposure tables.
- `Output Report Folder`: Folder where the complete GeoCausal output package is
  written.
- `Output ERF Table`: Optional ArcGIS table copy of `erf_curve.csv`.
- `Output Target Exposure Table`: Optional ArcGIS table copy of
  `target_exposures.csv`.
- `Output Effect Estimates Table`: Optional ArcGIS table copy of
  `effect_estimates.csv`.
- `Output Analysis Joined Table`: Optional one-row-per-unit table with target
  exposure fields when target outcomes are configured.

## Outputs

Each run writes the standard GeoCausal package:

- `analysis.yaml`
- `manifest.json`
- `effect_estimates.csv`
- `erf_curve.csv`
- `model_diagnostics.json`
- `balance_summary.csv`
- `overlap_summary.json`
- `context_ablation.csv`
- `placebo_tests.csv`
- `bootstrap_robustness.csv`
- `bootstrap_summary.json`
- `erf_stability.json`
- `spatial_diagnostics.json`
- `spatial_bootstrap_robustness.csv`
- `spatial_bootstrap_summary.json`
- `spatial_graph_sensitivity.csv`
- `spatial_graph_sensitivity_summary.json`
- `spatial_slx_estimates.csv`
- `spatial_slx_summary.json`
- `spatial_spillover_decomposition.csv`
- `spatial_spillover_summary.json`
- `spatial_exposure_mapping.csv`
- `spatial_exposure_mapping_summary.json`
- `result_summary.md`
- `robustness_report.md`
- `target_exposures.csv`, when target outcome values are provided

The ArcGIS geoprocessing messages summarize the credibility decision,
robustness interpretation, exposure trimming, target table, spatial Moran
diagnostics, SLX total effect, and result-summary file when those outputs are
available.

## Spatial Output Boundary

The ArcGIS toolbox is intentionally a thin ArcPy adapter. It writes analysis
tables and the full GeoCausal output package, but it does not duplicate the
notebook/QGIS spatial-output builder. To create GeoPackage, GeoJSON, Shapefile,
PNG, HTML, and QGIS `.qml` outputs from a completed run, use
`geocausal.spatial_outputs.build_spatial_analysis_outputs` with the original
boundary layer and `analysis_joined.csv`.

## Integration Boundary

ArcPy is used only in this toolbox layer to read ArcGIS inputs and optionally
copy CSV outputs back into ArcGIS tables. The algorithm is implemented in
`geocausal` and can also be called from notebooks or future QGIS plugins through
`geocausal.adapters.AnalysisRequest`.
