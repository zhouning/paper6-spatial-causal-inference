# GeoCausal SCCA MVP Design

## Goal

Create a first open-source algorithm-framework outcome from Paper6 while the manuscript is being strengthened. The first release is a Python package plus CLI inside the Paper6 repository, exposing the Spatial Context Causal Adjustment (SCCA) workflow as a reproducible tool rather than only as case-specific experiment scripts.

The V1 product is intentionally SCCA-first. It is not a full ArcGIS Pro Causal Inference Analysis clone and does not attempt to wrap every Paper6 method at once. It turns the already validated Paper6 SCCA pipeline, diagnostics, and robustness suite into a reusable open-source interface that can later be split into an independent repository.

## Product Boundary

- Package location: `geocausal/` at the Paper6 repository root.
- CLI command: `geocausal`.
- Primary interface: YAML configuration.
- V1 algorithm scope: SCCA main effect estimation, exposure-response curve output, context diagnostics, placebo tests, context ablation, grouped or block bootstrap robustness, ERF stability, and Markdown/JSON reporting.
- Supported data formats: CSV, GeoPackage, GeoJSON, and Shapefile.
- Out of scope for V1:
  - QGIS plugin or web UI.
  - Packaging and publishing to PyPI.
  - Full migration of `data_agent/scca` internals into `geocausal`.
  - Full wrapping of PSM, DiD, spatial Granger, GCCM, causal forest, LLM causal reasoning, or world-model counterfactual methods.
  - Manuscript text revision.

## Positioning

GeoCausal should be described as an open-source geospatial causal inference toolkit derived from Paper6. The first release emphasizes transparent spatial context adjustment and reproducible robustness evidence. The product should be comparable in usability intent to commercial GIS causal tools, but its first contribution is narrower and more research-grade:

- Open YAML configuration instead of proprietary dialog settings.
- Scriptable CLI instead of GUI-only operation.
- Reproducibility manifest and report artifacts by default.
- Paper6-specific SCCA diagnostics and robustness checks as first-class outputs.

## Recommended Implementation Route

Use a thin framework boundary over the existing Paper6 SCCA modules.

`geocausal/` owns configuration parsing, data loading, pipeline orchestration, CLI behavior, and user-facing reporting. It calls the existing `data_agent.scca` and `data_agent.scca.robustness` modules for the underlying SCCA algorithms. This avoids destabilizing the existing Paper6 experiments and preserves the tests that already validate Snow8, Soho, county social capital, and robustness behavior.

The implementation must not move or rewrite the existing SCCA internals unless a small adapter is required. Any deeper migration can be done after V1 is usable and tested.

## CLI Design

V1 commands:

```powershell
geocausal init --template scca
geocausal run analysis.yaml
geocausal diagnose analysis.yaml
geocausal report results/
```

Command responsibilities:

- `init --template scca`: write a minimal example YAML configuration to the current directory or a requested path.
- `run analysis.yaml`: validate config, load data, execute SCCA analysis, execute configured robustness checks, and write a complete output package.
- `diagnose analysis.yaml`: validate config and input data without fitting the full analysis. This should catch missing columns, invalid coordinate settings, insufficient sample size, and unwritable output paths.
- `report results/`: rebuild or summarize report artifacts from an existing result directory when the manifest and intermediate files are already present.

The CLI should return nonzero exit codes for validation and runtime failures. Error messages should be concise and written for applied researchers rather than Python developers.

## YAML Configuration

The V1 YAML schema should be stable enough to use in examples and paper reproduction.

Example:

```yaml
case_name: snow8_open
input:
  path: data/example.csv
  format: csv
  x: x
  y: y
variables:
  exposure: perc_sou
  outcome: deaths
  confounders:
    - pop
    - deprivation
context:
  columns:
    - dist_pump
    - district
robustness:
  placebo_exposures:
    - name: lambeth_supplier_share
      column: perc_lam
      role: competing_supplier
      expected_relation: weaker_or_opposite_than_perc_sou
  bootstrap:
    group_column: district
    n_replicates: 200
output:
  directory: results/snow8_open
```

Required fields:

- `case_name`
- `input.path`
- `variables.exposure`
- `variables.outcome`
- `output.directory`

Optional fields:

- `input.format`: inferred from file extension when omitted.
- `input.x`, `input.y`, `input.lon`, `input.lat`: required only for CSV when no geometry exists.
- `variables.confounders`: defaults to an empty list.
- `context.columns`: defaults to an empty list.
- `robustness.placebo_exposures`: defaults to no placebo tests.
- `robustness.bootstrap.group_column`: optional. If absent and geometry is available, the pipeline may create coordinate-grid groups.
- `robustness.bootstrap.n_replicates`: default `200`.

## Data Loading

Supported input formats:

- CSV: read with pandas. Spatial position is constructed from `x/y` or `lon/lat` when provided. CSV without coordinates is allowed only for analyses that do not require geometry-derived blocks.
- GeoPackage: read with GeoPandas.
- GeoJSON: read with GeoPandas.
- Shapefile: read with GeoPandas.

The loader should preserve user columns without renaming them. It may add internal helper columns with a reserved prefix such as `_gc_`.

V1 should not require CRS transformations unless a specific context feature needs projected distance. If geometry is present but CRS is missing, diagnostics should warn and continue when no distance computation is required.

## Pipeline

The main V1 pipeline should perform these steps:

1. Parse and validate YAML.
2. Load input data.
3. Validate required columns and output path.
4. Build an SCCA study specification from the YAML fields.
5. Run the SCCA main effect estimator using existing Paper6 SCCA modules.
6. Write `effect_estimates.csv`.
7. Write or derive `erf_curve.csv` when the SCCA estimator provides an exposure-response curve.
8. Run context ablation using `data_agent.scca.robustness`.
9. Run configured placebo exposure tests.
10. Run grouped bootstrap using the configured group column or generated coordinate-grid groups.
11. Summarize ERF stability.
12. Write reports and manifest.

If a step is unavailable because the input does not support it, the result should record `status: skipped` with a reason rather than failing silently. Failures should stop execution only when they invalidate the main analysis or requested robustness checks.

## Output Package

`geocausal run analysis.yaml` writes a complete analysis directory.

Required files:

- `effect_estimates.csv`
- `erf_curve.csv`
- `context_ablation.csv`
- `placebo_tests.csv`
- `bootstrap_robustness.csv`
- `bootstrap_summary.json`
- `erf_stability.json`
- `robustness_report.md`
- `manifest.json`

`manifest.json` should include:

- package version or local implementation version
- run timestamp
- input file path
- config file path
- case name
- exposure and outcome columns
- confounder and context columns
- row count
- output file inventory
- high-level robustness interpretation
- warnings and skipped steps

The Markdown report should summarize the main effect, ERF direction, ablation stability, placebo results, bootstrap confidence interval, and limitations.

## Error Handling

Validation errors should be explicit and actionable:

- Missing input file.
- Unsupported input format.
- Missing exposure or outcome column.
- Missing listed confounder, context, placebo, or bootstrap group column.
- CSV has no coordinates when geometry-derived grouping is requested.
- Bootstrap sample has too few valid groups.
- Output directory cannot be created or written.
- Empty data after dropping rows required for the model.

CLI output should avoid long Python tracebacks for expected user errors. Internal exceptions may still be shown behind a future verbose flag, but V1 should keep the normal path concise.

## Testing Strategy

V1 tests should be focused and integration-oriented:

- YAML config parsing and validation.
- CSV loading with `x/y` and `lon/lat`.
- GeoJSON or GeoPackage loading fixture.
- `geocausal diagnose` catches missing columns and invalid output paths.
- `geocausal run` on a small fixture creates all required output files.
- Output manifest contains the expected case name, variable names, output inventory, and warnings.
- Robustness helpers remain compatible with the new pipeline.
- Existing Paper6 SCCA and causal inference tests continue to pass.

The implementation plan should add tests before code for the new `geocausal` boundary. It does not need to re-test every numerical property already covered by `data_agent.scca` tests, but it must verify that the new CLI produces a usable result package.

## Success Criteria

The MVP is complete when:

1. A user can create or write an SCCA YAML file.
2. `geocausal diagnose analysis.yaml` validates the configuration and input data.
3. `geocausal run analysis.yaml` produces the complete output package on fixture data.
4. The framework can run at least one existing Paper6 SCCA case through the new YAML interface.
5. Tests for the new package pass alongside the existing SCCA tests.
6. README or a dedicated docs page shows the minimal install/run workflow.

## Future Extensions

After V1, the framework can add:

- PyPI packaging and independent repository split.
- QGIS processing provider.
- Web API or lightweight dashboard.
- ArcGIS-like matching/IPW/GPS workflow as a separate method family.
- DiD, spatial Granger, GCCM, causal forest, and world-model counterfactual modules.
- Publication-ready figure generation.
