# SCCA County Social-Capital Validation Design

Date: 2026-06-19

## Goal

Add a third reproducible SCCA experiment using the US county social-capital and longevity dataset. This case should test whether the existing continuous-exposure SCCA workflow can run on a larger cross-domain observational dataset and report transparent credibility diagnostics without claiming geometry-based spatial identification that the data cannot support.

## Scientific Role

This experiment is an external validation case, not a replacement for the South London cholera and Soho pump cases.

The intended evidence roles are:

- Snow8: small spatial causal case with historical baseline outcome and supplier exposure.
- Soho: spatial mechanism case for Broad Street pump proximity.
- County social capital: larger cross-domain continuous-exposure validation with county identifiers and state-level robustness.

The county case should be described as non-geometric or weakly spatial unless county geometries are added later. It has `FIPS`, `STATE_NAME`, `CountyCode`, `Shape_Length`, and `Shape_Area`, but the inspected Excel file does not include polygon geometry or adjacency.

## Input Data

Source:

- `D:\北大MEM\01-课程学习\02-技术核心课\数据可视化技术及应用\CausalInferAnalysis\CausalInferAnalysis\CountyData_TableToExcel.xlsx`

Observed workbook structure:

- Sheet: `CountyData`
- Rows: 3108
- Columns: 20

Observed fields:

- Unit identifiers: `OBJECTID`, `STATE_NAME`, `CountyCode`, `County`, `FIPS`
- Outcome: `AveAgeDeath`
- Exposure: `SocialAssoc`
- Candidate confounders: `UnemployRate`, `pHHinPoverty`, `pNoHealthInsur`, `MentalHealth`, `pAdultSmoking`, `pAdultObesity`, `FastFood`, `pInsufficientSleep`, `pAlcohol`, `pSuicideDeaths`, `AirPollution`
- Weak spatial/context fields: `Shape_Length`, `Shape_Area`
- Robustness grouping: `STATE_NAME`

## Causal Question

Primary question:

> Are county-level social association rates associated with average age at death after adjusting for observed socioeconomic, health, behavioral, and environmental covariates?

Primary exposure:

- `SocialAssoc`

Primary outcome:

- `AveAgeDeath`

Primary adjustment set:

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

Context features:

- `Shape_Length`
- `Shape_Area`

State-level robustness:

- leave-one-`STATE_NAME`-out coefficient stability.

## Interpretation Boundaries

The output must not claim full spatial confounding control, adjacency-based inference, or county-neighborhood diagnostics. The analysis can support only:

- external validation that the SCCA pipeline handles a larger continuous-exposure dataset,
- observed-covariate adjustment,
- overlap and exposure-balance diagnostics,
- state-level leave-one-group-out robustness,
- weak spatial context through shape metrics.

If the diagnostics are weak, the report should mark the case as `moderate_support` or `weak_or_failed_support` and explain why.

## Architecture

Add a small county-specific adapter while reusing the existing SCCA modules.

New or changed files:

- `data_agent/scca/specs.py`: add `StudySpec.county_social_capital_default()`.
- `data_agent/experiments/run_scca_county_social_capital.py`: load the workbook, coerce expected numeric columns, run existing SCCA modules, and write provenance metadata.
- `data_agent/test_scca_county_social_capital.py`: tests for spec defaults, preprocessing, fixture end-to-end runner behavior, and manifest output contract.
- `README.md`: add a command for reproducing the county social-capital experiment.

Generated output directory:

- `paper/ijgis_submission_20260605/07_results/scca_county_social_capital/`

Expected generated files follow the existing SCCA contract:

- `data_profile.json`
- `variable_candidates.csv`
- `context_features.csv`
- `context_feature_manifest.json`
- `design_plan.json`
- `effect_estimates.csv`
- `erf_curve.csv`
- `model_diagnostics.json`
- `balance_summary.csv`
- `overlap_summary.json`
- `spatial_robustness.csv`
- `credibility_report.json`
- `analysis_report.md`
- `manifest.json`

## Data Flow

1. Load `CountyData_TableToExcel.xlsx`.
2. Select the `CountyData` sheet by default.
3. Copy the input table before preprocessing.
4. Coerce numeric columns:
   - `OBJECTID`
   - `CountyCode`
   - `FIPS`
   - `AveAgeDeath`
   - `SocialAssoc`
   - all configured confounders
   - `Shape_Length`
   - `Shape_Area`
5. Preserve `STATE_NAME` and `County` as text fields.
6. Run existing SCCA modules:
   - `profile_table`
   - `build_context_features`
   - `select_design`
   - `estimate_effects`
   - `audit_effects`
   - `write_report`
7. Write metadata including workbook path, SHA-256, sheet name, input rows/columns, code commit, dirty-state indicator, and generation timestamp.
8. Return parsed `manifest.json`.

## Estimation and Diagnostics

The existing SCCA estimators are sufficient for this checkpoint:

- `baseline_adjusted_ols`, interpreted here as adjusted OLS because no baseline outcome is configured.
- `generalized_propensity_erf`.

No difference-outcome estimator should run because the dataset has no baseline mortality outcome.

Required diagnostics:

- exposure overlap summary,
- exposure-balance correlations for confounders and shape context,
- state-level leave-one-out robustness using `STATE_NAME`,
- estimator status checks,
- credibility decision and reasons.

## Testing

Use TDD.

Minimum tests:

- `StudySpec.county_social_capital_default()` exposes expected exposure, outcome, confounders, context fields, and subgroup.
- County preprocessing preserves row count, coerces numeric fields, and keeps `STATE_NAME` text.
- Fixture end-to-end run writes all manifest-listed files.
- CLI prints parseable manifest JSON.
- Existing SCCA tests for Snow8 and Soho still pass.
- Existing causal inference tests still pass with the known deprecation warning.

## Acceptance Criteria

Implementation is complete only when:

- `data_agent/test_scca_county_social_capital.py` passes.
- `data_agent/test_scca_soho.py` and `data_agent/test_scca_snow8.py` still pass.
- `data_agent/test_causal_inference.py` still passes with only the known warning.
- Real workbook run produces `paper/ijgis_submission_20260605/07_results/scca_county_social_capital/manifest.json`.
- `credibility_report.json` records one of `strong_support`, `moderate_support`, or `weak_or_failed_support`.
- The final report describes the county case as external validation with limited spatial diagnostics, not as full geometry-aware spatial causal evidence.

## Non-Goals

- Do not join external county geometry in this checkpoint.
- Do not implement adjacency, Moran residual tests, or county-neighborhood lag features.
- Do not edit the IJGIS manuscript.
- Do not change Snow8 or Soho generated outputs unless required by shared code compatibility.
- Do not add LLM variable-role suggestion logic.

