# Open GIS Parity Package Design

## Goal

Make GeoCausal useful as an ArcGIS-free causal analysis product by ensuring a normal `geocausal run` produces a complete, inspectable GIS analysis package without requiring ArcGIS Pro.

This stage does not build a new desktop UI. It strengthens the shared `geocausal` core so CLI, notebooks, QGIS, and the optional ArcGIS toolbox all receive the same product-grade output contract.

## Product Positioning

The correct claim after this stage is:

> GeoCausal SCCA provides an open GIS causal evidence package for continuous-exposure spatial studies, with ArcGIS-style workflow outputs plus spatial diagnostics and evidence-boundary reporting.

The claim is not:

> GeoCausal reproduces proprietary ArcGIS internals or fully replaces every ArcGIS Pro user-interface feature.

## User-Facing Output Contract

Every successful `geocausal run` should write these additional files when the required inputs are available:

- `open_gis_analysis_package/analysis_joined.csv`
- `open_gis_analysis_package/gis_balance_summary.csv`
- `open_gis_analysis_package/gis_erf_curve_200.csv`
- `open_gis_analysis_package/gis_run_summary.json`
- `open_gis_analysis_package/gis_run_summary.md`

The package should be written under the configured analysis output directory. It should not depend on ArcPy, QGIS runtime classes, desktop GIS installation paths, or proprietary file formats.

## Analysis Joined Table

`analysis_joined.csv` should be one row per retained analysis unit, suitable for joining back to a GIS layer or opening directly in pandas, QGIS, Excel, or any BI tool. It should include:

- original retained input columns;
- `gc_unit_id`;
- `gc_exposure`;
- `gc_outcome`;
- `gc_propensity_score`;
- `gc_balancing_weight`;
- `gc_included`;
- `gc_trim_status`;
- target-outcome fields when `target_exposures.csv` exists.

`gc_propensity_score` is an open generalized-propensity-style score derived from the fitted exposure model density. `gc_balancing_weight` is the normalized inverse-density weight used by the ERF path. If those values cannot be estimated, the package should still write the table with `NaN` scores and weight `1.0`, and record a warning in the summary.

## Balance Summary

`gis_balance_summary.csv` should provide ArcGIS-user-readable balance diagnostics over confounders and context columns:

- `variable`;
- `role`;
- `raw_correlation`;
- `weighted_correlation`;
- `absolute_weighted_correlation`;
- `balanced_at_0_1`;
- `n_complete`;

The threshold should be fixed at `0.1` for this stage, matching the existing ArcGIS parity matrix language. Missing or constant variables should be reported as skipped rows instead of failing the whole run.

## ERF 200-Point Curve

`gis_erf_curve_200.csv` should resample the existing `erf_curve.csv` onto exactly 200 exposure grid rows for ArcGIS-style product parity. It should include:

- `exposure`;
- `response`;
- `ci_lower` when available;
- `ci_upper` when available;
- `source = interpolated_from_erf_curve`.

If the source ERF has fewer than two valid rows, write an empty file with the expected headers and record a warning.

## Run Summary

`gis_run_summary.json` and `gis_run_summary.md` should summarize:

- case name;
- row count and retained row count;
- exposure, outcome, confounders, and context columns;
- effect summary;
- evidence grade and reasons;
- spatial diagnostic highlights;
- generated package files;
- warnings.

The summary should speak in open-product language. It can say "ArcGIS-style" in docs, but runtime outputs should be branded as Open GIS / GeoCausal rather than as an ArcGIS clone.

## Architecture

Add a focused module under `geocausal/` for this package. The module should consume the existing `GeoCausalConfig`, retained analysis frame, `StudySpec`, `SCCAPaths`, and manifest-like summary data. It should not rerun the SCCA model.

`geocausal.pipeline.run_analysis` should call the package writer after core outputs and target-exposure outputs exist, then register package files in `manifest["files"]`.

The estimator should expose row-level generalized propensity scores and weights through a CSV output so the package writer can reuse the same values rather than recomputing a different model.

## Testing

Use TDD. First add a failing pipeline test that runs the fixture config and asserts the Open GIS package exists, has the expected file names, has 200 ERF rows, has score/weight columns, and has balance summary rows for confounders/context columns.

Then implement the minimal production code needed to pass that test. Afterward run the existing GeoCausal pipeline tests and QGIS/ArcGIS adapter smoke tests that exercise the shared core.

## Out Of Scope For This Stage

- A new graphical desktop interface.
- Exact proprietary ArcGIS algorithm reproduction.
- Gradient boosting propensity score fallback.
- Local ERF popups inside ArcGIS Pro.
- Installer packaging.
- Commercial website or dashboard UI.

Those are follow-up stages after the open output contract is stable.
