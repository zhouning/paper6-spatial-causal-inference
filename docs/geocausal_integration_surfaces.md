# GeoCausal Integration Surfaces

GeoCausal is designed as a reusable Python algorithm package with thin adapters
for GIS and notebook environments.

## Core Boundary

The reusable boundary is:

```python
from pathlib import Path

from geocausal.adapters import AnalysisRequest, run_scca_analysis

request = AnalysisRequest(
    case_name="generic_case",
    input_path=Path("input.csv"),
    output_dir=Path("results/generic_case"),
    unit_id="unit_id",
    exposure="exposure",
    outcome="outcome",
    confounders=("confounder_1", "confounder_2"),
    context_columns=("context_1",),
    bootstrap_group="group",
    lower_exposure_quantile=0.01,
    upper_exposure_quantile=0.99,
    target_outcomes=(70.0,),
)

manifest = run_scca_analysis(request)
```

This is the integration point for notebooks, ArcGIS Pro, QGIS, and command-line
automation. It accepts field names supplied by the user and does not contain
case-study-specific defaults.

## Notebook Use

Notebook users can prepare a CSV or GeoPackage, construct `AnalysisRequest`, and
call `run_scca_analysis`. The output folder contains CSV/JSON/Markdown artifacts
that can be read back into pandas, GeoPandas, matplotlib, or other plotting
libraries.

When target outcomes are configured, notebook users can also build a one-row-per-
unit joined analysis table from the original input and `target_exposures.csv`:

```python
from geocausal.adapters import build_analysis_joined_table

build_analysis_joined_table(
    input_csv=Path("input.csv"),
    target_exposures_csv=Path("results/generic_case/target_exposures.csv"),
    output_csv=Path("results/generic_case/analysis_joined.csv"),
    unit_id_field="unit_id",
)
```

## ArcGIS Pro Use

ArcGIS Pro uses the Python Toolbox at:

```text
arcgis_toolbox/GeoCausalSCCA.pyt
```

The toolbox only handles ArcGIS UI parameters, ArcPy data export, and optional
copying of CSV outputs back to ArcGIS tables. It delegates algorithm execution to
`geocausal.adapters.AnalysisRequest` and reuses the same
`build_analysis_joined_table` helper to create an ArcGIS-ready analysis table.

## QGIS Path

A future QGIS Processing provider should follow the same adapter pattern:

1. Read QGIS layer/table parameters.
2. Export selected attributes and geometry-derived coordinates to CSV or
   GeoPackage.
3. Construct `AnalysisRequest`.
4. Call `run_scca_analysis`.
5. Build `analysis_joined.csv` from `target_exposures.csv` when target outcomes
   are requested.
6. Register generated CSV/JSON outputs as QGIS result layers or report files.

No SCCA logic should be implemented directly in a QGIS plugin. The plugin should
remain a thin adapter over `geocausal`.

The current repository includes a runtime-light skeleton at:

```text
qgis_provider/geocausal_scca_algorithm.py
```

## Why This Matters

Keeping the algorithm in `geocausal` prevents three incompatible versions of the
same method from emerging across ArcGIS, QGIS, and notebooks. The GIS wrappers are
interfaces; the causal inference engine remains one tested Python package.
