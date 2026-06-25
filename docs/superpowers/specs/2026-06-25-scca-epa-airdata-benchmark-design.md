# SCCA EPA AirData Benchmark Design

## Goal

Add a public, reproducible spatiotemporal policy benchmark to Paper 6 by combining EPA Clean Air Act nonattainment records with EPA AirData annual air-quality summaries and county geometries. The benchmark is intended to strengthen SCCA validation without overstating causal identification.

## Scope

The first implementation uses an annual county-year panel. It does not download daily monitor data and does not implement the protected-area/Hansen forest-loss case. The county-year panel is the right first scope because it is small enough to reproduce in the repository workflow while still containing real policy timing, spatial neighborhoods, temporal baselines, and spillover risks.

The experiment has two evidence roles:

1. A real-world policy benchmark: nonattainment designation as treatment, annual pollution as outcome, and lagged pollution plus spatial context as adjustment variables.
2. A semi-synthetic validation layer: inject known treatment effects into the real EPA county-year geography to test whether SCCA diagnostics distinguish stable settings from intentionally fragile spatial-confounding settings.

## Data Sources

- EPA AirData annual concentration summaries, primarily `annual_conc_by_monitor_YYYY.zip`.
- EPA Green Book downloadable nonattainment history/status workbooks.
- Census cartographic county boundaries, preferably the 500k generalized county boundary file.

Raw downloads are local reproducibility inputs and should not be committed. Processed analysis tables and compact result artifacts may be committed if they remain small enough for normal Git history.

## Data Model

The prepared panel will use one row per county-year-pollutant target. The first target is PM2.5 because it has a clear annual concentration outcome and public AirData monitor summaries. Ozone can be added if the same parser works without creating an overly broad implementation.

Required columns:

- `county_fips`: five-digit county FIPS.
- `year`: calendar year.
- `pollutant`: pollutant code or label.
- `annual_mean`: county-level annual mean concentration aggregated from monitors.
- `monitor_count`: number of contributing monitors.
- `nonattainment`: county-year policy indicator derived from Green Book records.
- `nonattainment_lag1`: previous-year policy status, used as the primary exposure to reduce simultaneity.
- `baseline_annual_mean`: previous-year outcome.
- `neighbor_nonattainment_lag1`: neighboring-county exposure summary.
- `x`, `y`: county centroid coordinates for spatial diagnostics.
- Optional context columns: state fixed-effect encodings or region summaries if they are present in the processed table without making the first benchmark too large.

## SCCA Configuration

The SCCA run will treat `nonattainment_lag1` as the primary exposure and `annual_mean` as the outcome. Confounders will include at least `baseline_annual_mean`, `monitor_count`, and calendar-year indicators or a numeric year trend. Context columns will include centroid coordinates and `neighbor_nonattainment_lag1`.

The output directory will be:

`paper/ijgis_submission_20260605/07_results/epa_nonattainment_airdata`

The experiment will write:

- A prepared panel CSV.
- A generated GeoCausal/SCCA YAML config.
- The standard SCCA output package from `geocausal.pipeline.run_analysis`.
- A compact benchmark summary JSON and Markdown report.
- Semi-synthetic scenario summaries with true effect, estimated effect, error, grade, and triggered evidence rules.

## Evidence Boundary

The EPA real-world run is not a definitive causal proof. Nonattainment designations are policy responses to pollution, so treatment assignment is endogenous. The benchmark is valuable because it is public, spatiotemporal, policy-relevant, and contains real spatial dependence. The paper should describe it as a public SCCA stress test and policy benchmark.

The semi-synthetic layer is the stronger validation component because it has known injected effects on real geography. It should test at least:

- A stable scenario where treatment effect is recoverable after lagged-outcome and spatial-context adjustment.
- A confounded scenario where spatially structured latent risk creates residual Moran or spatial adjustment downgrade.
- A spillover scenario where neighboring nonattainment affects outcomes and should trigger spatial caution.

## Error Handling

The acquisition script should fail with clear messages when a source URL is unreachable, a workbook has unknown sheet/column names, AirData lacks required columns, or the panel has too few complete rows for SCCA. It should also support using already-downloaded local files so the benchmark can be rerun without network access.

## Testing

Add tests with tiny fixture tables for:

- AirData annual monitor aggregation to county-year outcomes.
- Green Book nonattainment parsing into county-year indicators.
- County neighbor exposure computation from a tiny adjacency fixture.
- Semi-synthetic scenario generation preserving true effect metadata.
- Evidence synthesis inclusion of the EPA benchmark row.

Tests should not require network access or large geospatial downloads.

## Manuscript Integration

After the experiment runs, update the IJGIS manuscript to include the EPA benchmark as a public spatiotemporal validation case. The text must preserve the bounded claim:

- SCCA improves auditability and spatial diagnostic discipline.
- The EPA policy benchmark strengthens public reproducibility.
- Semi-synthetic known-effect runs provide stronger validation than observational policy estimates alone.
- Neither the EPA case nor SCCA removes unmeasured spatial confounding or interference by itself.
