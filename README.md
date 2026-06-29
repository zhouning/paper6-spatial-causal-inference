# GeoCausal SCCA: Spatial Context Causal Adjustment

This repository is the Paper6 reproduction package and open-source software boundary for:

**Spatial Context Causal Adjustment (SCCA) for geographic observational studies: a reproducible workflow for constructing spatial-context adjustment sets, checking balance and common support, running spatial robustness diagnostics, and reporting bounded causal evidence.**

SCCA is not presented as a new causal estimator. It is an engineering-grade diagnostic framework that wraps standard causal estimators with spatial context design, spatial diagnostics, robustness checks, and evidence grading so that geographic observational studies can be audited and reproduced.

## What This Repository Provides

- `geocausal/`: the first open-source GeoCausal SCCA package boundary with YAML-first CLI, Python adapter API, spatial input loading, and machine-readable outputs.
- `data_agent/scca/`: the SCCA method modules used by the paper, including profiling, context construction, design selection, estimators, diagnostics, robustness, spatial diagnostics, reporting, and evidence rules.
- `arcgis_toolbox/`: ArcGIS Pro toolbox wrapper and county social-capital workflow notes.
- `qgis_provider/`: QGIS Processing provider skeleton for running GeoCausal SCCA.
- `examples/`: cross-platform county social-capital configuration and example inputs for county, Snow8, and Soho smoke/reproduction cases.
- `data/`: CountyData and States shapefiles used for GIS joins, map rendering, and ArcGIS/QGIS demonstrations.
- `paper/ijgis_submission_20260605/`: IJGIS-oriented manuscript package, generated results, reports, figures, and internal review materials.

## SCCA Workflow

The current SCCA implementation follows a reproducible seven-stage workflow:

1. Profile the geographic observational table and candidate variables.
2. Build spatial context features from user-supplied context columns and geometry/coordinate information when available.
3. Select the adjustment design and document the spatial-context adjustment set.
4. Estimate treatment effects and exposure-response functions with transparent baseline models.
5. Check balance, common support, overlap, and model diagnostics.
6. Run spatial robustness checks, including context ablation, placebo exposures, bootstrap sensitivity, residual spatial diagnostics, and spatial lag/SLX-style adjusted estimates where inputs permit.
7. Write evidence outputs, credibility grades, reports, and manifests that can be inspected by reviewers or loaded into GIS tools.

## Quick Start

Use Python 3.11+ from the repository root.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

On Windows, replace `source .venv/bin/activate` with:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run focused GeoCausal/SCCA tests:

```bash
python -m pytest \
  data_agent/test_geocausal_config.py \
  data_agent/test_geocausal_io.py \
  data_agent/test_geocausal_pipeline.py \
  data_agent/test_geocausal_adapters.py \
  data_agent/test_geocausal_spatial_outputs.py \
  data_agent/test_scca_evidence_rules.py \
  data_agent/test_scca_spatial_diagnostics.py
```

## Run The County SCCA Example

The committed county social-capital example is the fastest end-to-end GeoCausal SCCA run:

```bash
python -m geocausal.cli diagnose examples/county_social_capital_example.yaml
python -m geocausal.cli run examples/county_social_capital_example.yaml
python -m geocausal.cli report paper/ijgis_submission_20260605/07_results/examples/county_social_capital_example
```

The example studies county-level social association (`SocialAssoc`) and average age at death (`AveAgeDeath`) with demographic, health, socioeconomic, and spatial context covariates. It writes results under:

```text
paper/ijgis_submission_20260605/07_results/examples/county_social_capital_example/
```

The included shapefile `data/CountyData.shp` can be joined by `FIPS` to GeoCausal outputs such as `target_exposures.csv` and `analysis_joined.csv` for map rendering in ArcGIS Pro, QGIS, or a web GIS frontend.

## YAML And Python APIs

Start a new SCCA configuration from the CLI:

```bash
python -m geocausal.cli init --template scca --output analysis.yaml
python -m geocausal.cli diagnose analysis.yaml
python -m geocausal.cli run analysis.yaml
python -m geocausal.cli report results/example_case
```

Programmatic callers can use the adapter API:

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
)

manifest = run_scca_analysis(request)
build_analysis_joined_table(
    input_csv=request.input_path,
    target_exposures_csv=request.output_dir / "target_exposures.csv",
    output_csv=request.output_dir / "analysis_joined.csv",
    unit_id_field=request.unit_id,
)
```

## Output Contract

A completed SCCA run is designed to be machine-readable as well as reviewer-readable. Key outputs include:

- `data_profile.json`, `variable_candidates.csv`, `context_features.csv`, `context_feature_manifest.json`
- `design_plan.json`, `effect_estimates.csv`, `erf_curve.csv`, `target_exposures.csv`
- `balance_summary.csv`, `overlap_summary.json`, `model_diagnostics.json`
- `spatial_robustness.csv`, `context_ablation.csv`, `placebo_tests.csv`
- `bootstrap_robustness.csv`, `bootstrap_summary.json`, `erf_stability.json`
- `credibility_report.json`, `robustness_report.md`, `analysis_report.md`, `manifest.json`

These files are intentionally stable because they are consumed by notebooks, ArcGIS/QGIS workflows, GIS Data Agent integration surfaces, and paper result tables.

Every successful `geocausal run` also writes an Open GIS analysis package under the run output directory:

- `open_gis_analysis_package/analysis_joined.csv`
- `open_gis_analysis_package/gis_balance_summary.csv`
- `open_gis_analysis_package/gis_erf_curve_200.csv`
- `open_gis_analysis_package/gis_run_summary.json`
- `open_gis_analysis_package/gis_run_summary.md`

This package is designed for ArcGIS-free use in Python, QGIS, notebooks, Excel, or BI tools while preserving the GIS causal-analysis concepts users expect: retained analysis rows, generalized propensity scores, balancing weights, balance diagnostics, a 200-point exposure-response curve, target-outcome outputs, spatial diagnostics, and evidence grading.

See `docs/open_gis_analysis_package.md` for the ArcGIS-free quickstart, file semantics, spatial-package CLI command, QGIS/Python workflows, and acceptance checklist.

## Reproduction Cases

The new-version paper centers on SCCA as a spatial causal workflow and evaluates it through multiple cases:

- **Chongqing UHI case**: building-height exposure, LST outcome, land-cover/elevation/urban context adjustment, balance checks, spatial bootstrap, placebo thresholds, and residual spatial diagnostics. Raw Chongqing geospatial inputs and building-level samples are restricted local inputs and are not tracked on GitHub.
- **Snow cholera case**: South London subdistrict cholera data for spatial-context causal reasoning and robustness diagnostics.
- **Soho Broad Street pump mechanism case**: household-level mechanism-oriented SCCA demonstration.
- **US CountyData case**: county social capital and longevity example with CSV, shapefile, ArcGIS comparison, and map-ready joins.
- **Synthetic and audit cases**: multi-seed benchmarks, estimator stress tests, GeoFM/AlphaEarth ablation, LLM DAG validation, and world-model holdout validation used as supporting evidence rather than the main SCCA software boundary.

Representative commands:

```bash
python -m data_agent.experiments.run_scca_snow8 --csv-path examples/data/snow8/subdistricts.csv
python -m data_agent.experiments.run_scca_soho --csv-path examples/data/snow1/deaths_nd_by_house.csv
python -m data_agent.experiments.run_scca_county_social_capital --workbook-path examples/data/county/CountyData_TableToExcel.xlsx
python -m data_agent.experiments.run_scca_robustness_summary
```

For the restricted Chongqing UHI analysis sample:

```bash
python -c "import pandas as pd; from data_agent.experiments.chongqing_uhi_analysis import run_chongqing_uhi_analysis; df = pd.read_csv('/path/to/chongqing_uhi_analysis_sample.csv'); run_chongqing_uhi_analysis(df, n_bootstrap=500, n_spatial_bootstrap=500)"
```

Expected Chongqing result files are written under `paper/ijgis_submission_20260605/07_results/` and include:

- `chongqing_uhi_ablation.csv`
- `chongqing_uhi_balance.csv`
- `chongqing_uhi_matched_counts.csv`
- `chongqing_spatial_bootstrap.csv`
- `chongqing_placebo_thresholds.csv`
- `chongqing_residual_spatial_diagnostics.csv`
- `chongqing_uhi_analysis_manifest.json`
- `chongqing_uhi_analysis_report.md`

## GIS Integrations

- ArcGIS Pro toolbox: `arcgis_toolbox/GeoCausalSCCA.pyt`
- ArcGIS county workflow notes: `arcgis_toolbox/ArcGIS_Pro_使用手册_县域社会资本示例.md`
- QGIS Processing provider skeleton: `qgis_provider/geocausal_scca_algorithm.py`
- Map-ready county shapefile: `data/CountyData.shp`
- Cross-platform county CSV: `examples/data/county_social_capital.csv`
- Original county workbook copy used for SCCA reproduction: `examples/data/county/CountyData_TableToExcel.xlsx`
- Snow/Soho SCCA inputs: `examples/data/snow8/subdistricts.csv` and `examples/data/snow1/deaths_nd_by_house.csv`

The intended GIS pattern is:

1. Run SCCA from YAML, Python, ArcGIS Pro, QGIS, or GIS Data Agent.
2. Join output tables back to geometry by a stable unit identifier such as `FIPS`.
3. Render estimated effects, target exposures, support flags, balance summaries, and credibility diagnostics as map layers or linked tables.

## Data And Licensing Notes

Chongqing raw geospatial inputs and building-level analysis samples are excluded from GitHub because they include precise geometry/coordinate information and require separate permission and sensitivity review. See `DATA_AVAILABILITY.md` and `REPRODUCIBILITY.md`.

The county example uses third-party training/demo data, not author-generated data. The shapefile metadata credits Esri, U.S. Census Bureau, NOAA/NOS/NGS, CDC WONDER/NCHS, County Health Rankings 2019 through ArcGIS Living Atlas, the University of Wisconsin Population Health Institute, and the Robert Wood Johnson Foundation. Use is governed by the source terms documented in `DATA_AVAILABILITY.md`.

## Paper Entry Points

- IJGIS package overview: `paper/ijgis_submission_20260605/README.md`
- Main manuscript TeX: `paper/ijgis_submission_20260605/01_manuscript/01_manuscript_ijgis.tex`
- Compiled manuscript PDF: `paper/ijgis_submission_20260605/06_build/01_manuscript_ijgis.pdf`
- SCCA evidence synthesis: `paper/ijgis_submission_20260605/07_results/scca_evidence_synthesis_report.md`
- SCCA method comparison: `paper/ijgis_submission_20260605/07_results/scca_method_comparison_report.md`
- County ArcGIS comparison: `paper/ijgis_submission_20260605/07_results/geocausal_county_arcgis_comparison/arcgis_geocausal_comparison.md`
- Reproducibility guide: `REPRODUCIBILITY.md`
- Data availability notes: `DATA_AVAILABILITY.md`
