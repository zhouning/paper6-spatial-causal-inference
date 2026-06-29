# ArcGIS Causal Inference Analysis vs. SCCA Parity Matrix

Source baseline: Esri ArcGIS Pro **Causal Inference Analysis** tool reference, accessed 2026-06-26.

Official tool page:

https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-statistics/causal-inference-analysis.htm

## Commercial Positioning

ArcGIS Pro Causal Inference Analysis is the commercial GIS baseline for user-facing causal analysis with continuous exposures. SCCA should be positioned as an open spatial-diagnostic enhancement layer that matches the core workflow where feasible and adds explicit evidence-boundary outputs for spatial data.

The intended claim is:

> SCCA supports ArcGIS-style continuous-exposure causal analysis outputs and extends them with spatial residual diagnostics, neighborhood-exposure sensitivity, graph-sensitivity checks, spatial bootstrap robustness, and rule-based evidence grading.

The intended claim is not:

> SCCA fully replaces ArcGIS Pro Causal Inference Analysis or reproduces proprietary ArcGIS internals.

## Capability Matrix

| ArcGIS capability | ArcGIS product role | SCCA status | Commercial priority | Evidence or next action |
|---|---|---:|---:|---|
| Continuous exposure and outcome workflow | Main causal-analysis mode | Matched | P0 | SCCA supports continuous exposure-response workflows through `AnalysisRequest`. |
| User-declared confounders | Adjustment design input | Matched | P0 | `AnalysisRequest.confounders` supplies the adjustment set. |
| OLS propensity score model | Default propensity score route | Matched | P0 | Open GIS outputs expose ArcGIS-named GPS score and weight aliases. |
| Gradient boosting propensity score model | ML fallback for harder balancing | Matched | P1 | ArcGIS-style matching now evaluates OLS and GBM GPS methods and records the selected method. |
| Propensity score matching | Balancing method | Partial | P0 | Binary Chongqing module supports matching; continuous-exposure matching needs ArcGIS-compatible contract. |
| Inverse propensity score weighting | Faster balancing method | Partial | P0 | ERF weighting exists; output should expose ArcGIS-compatible weight fields. |
| 1%-99% exposure trimming | Default support guard | Matched | P0 | Current county workflow uses 1%-99% trimming and retains 3,044 of 3,108 rows. |
| Propensity-score trimming | Stabilizes weighting | Gap | P1 | Add explicit lower/upper propensity trimming parameters and report fields. |
| Weighted-correlation balance threshold | Decides whether confounders are balanced | Matched | P0 | Open GIS balance CSVs and run summary expose mean/median/max absolute weighted-correlation fields. |
| ERF curve output | Main effect visualization | Matched | P0 | SCCA writes `erf_curve.csv`; add exact 200-point ArcGIS parity option if needed. |
| Target exposure values | What-if outcome at specified exposure | Matched | P0 | SCCA target-exposure outputs are already used in county demo. |
| Target outcome values | Required exposure for specified outcome | Partial | P0 | Verify output contract and add product docs. |
| Local ERF popups | Per-feature interactive UX | Gap | P2 | Notebook/HTML map can approximate; ArcGIS pop-up parity is a later UI task. |
| Bootstrapped ERF confidence intervals | Optional uncertainty bands | Partial | P1 | SCCA has bootstrap robustness; ArcGIS-style ERF CI parity requires explicit report. |
| Output table fields for scores, weights, inclusion | GIS table interoperability | Partial | P0 | Add field aliases and `analysis_joined.csv` documentation. |
| Residual spatial autocorrelation | Spatial diagnostic beyond ArcGIS causal workflow | SCCA-only differentiator | P0 | County case residual Moran's I = 0.313, triggering bounded support. |
| Neighbor-exposure sensitivity | Interference/spillover warning | SCCA-only differentiator | P0 | County neighbor-exposure term remains significant. |
| SLX-style direct/indirect/total summaries | Spatial sensitivity interpretation | SCCA-only differentiator | P1 | Current county notebook writes SLX summaries. |
| Graph-sensitivity checks | Robustness over neighborhood definitions | SCCA-only differentiator | P1 | Current county notebook tests multiple coordinate-kNN graphs. |
| Machine-readable evidence grades | Productized claim boundary | SCCA-only differentiator | P0 | `scca_evidence_grade_rules.json` and evidence synthesis outputs. |

## Benchmark Path

The county social-capital case should be treated as the primary commercial parity benchmark:

- Exposure: `SocialAssoc`
- Outcome: `AveAgeDeath`
- Included rows after 1%-99% trimming: 3,044
- Input boundary rows: 3,108
- Baseline adjusted coefficient: 0.181
- Spatial-lag adjusted coefficient: 0.145
- Residual Moran's I: 0.313
- Evidence grade: bounded support

This benchmark lets the paper say that SCCA can reproduce the ArcGIS-facing workflow shape and sample accounting, while adding spatial diagnostics that prevent an over-strong causal interpretation.

## Generated Benchmark Artifacts

The executable benchmark now writes:

- `paper/ijgis_submission_20260605/07_results/arcgis_causal_inference_parity/arcgis_parity_matrix.csv`
- `paper/ijgis_submission_20260605/07_results/arcgis_causal_inference_parity/arcgis_parity_summary.md`
- `paper/ijgis_submission_20260605/07_results/arcgis_causal_inference_parity/arcgis_commercial_benchmark_manifest.json`

## Product Gap Summary

P0 gaps before a strong commercial demo:

- Keep ArcGIS-compatible balance summary names stable across GIS package versions.
- Keep explicit propensity-score and balancing-weight output aliases stable across GIS package versions.
- Exact ERF row-count option, including 200-point ArcGIS-style output.
- Target outcome output contract verification.

P1 gaps after the demo:

- Propensity-score trimming controls.
- ArcGIS-style bootstrapped ERF confidence bands.

P2 gaps:

- ArcGIS-native local ERF popups.
- A polished commercial UI beyond the Python toolbox.
