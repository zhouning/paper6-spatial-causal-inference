# SCCA ArcGIS Commercial Benchmark Design

Date: 2026-06-26

## Goal

Reposition Paper6 and the SCCA implementation toward a commercial GIS causal-analysis product by benchmarking against ArcGIS Pro's **Causal Inference Analysis** tool and making SCCA's parity features, differentiators, gaps, and proof artifacts explicit.

## Product Positioning

SCCA should be positioned as an **open, spatial-diagnostic enhancement layer for GIS causal analysis**, not as a literal clone of ArcGIS Pro Causal Inference Analysis.

The commercial claim should be:

> ArcGIS Pro Causal Inference Analysis provides a GIS-facing continuous-exposure causal workflow based on propensity scores, balancing weights, exposure-response functions, and target counterfactual fields. SCCA matches the core operational pattern for open GIS and notebook workflows, then adds spatial residual diagnostics, neighborhood-exposure sensitivity, graph-sensitivity checks, spatial bootstrap robustness, and rule-based evidence grading.

This positioning keeps three boundaries clear:

- ArcGIS remains the commercial baseline and vocabulary anchor.
- SCCA's value is auditability and spatial caution, not a universal causal-identification guarantee.
- Paper6 can claim commercial relevance without claiming that SCCA is already a complete ArcGIS replacement.

## ArcGIS Baseline Capability Map

Source: Esri ArcGIS Pro Causal Inference Analysis tool reference, accessed 2026-06-26.

Baseline features to track:

| ArcGIS capability | Product meaning | SCCA status | Priority |
|---|---|---:|---:|
| Continuous exposure and continuous/binary outcome | Core tool scope | Supported for continuous workflows; binary handled by case modules | P0 |
| Confounding-variable table | User-declared covariate adjustment | Supported through `AnalysisRequest.confounders` | P0 |
| Propensity score calculation by OLS regression | Default propensity model | Partially supported through GPS-style and adjusted outcome workflows | P0 |
| Propensity score calculation by gradient boosting | ML fallback when regression cannot balance | Gap | P1 |
| Propensity score matching | Default balancing method | Partially supported in binary case modules; continuous matching parity needs explicit output contract | P0 |
| Inverse propensity score weighting | Faster balancing alternative | Partially supported by ERF weights; needs ArcGIS-named parity mode | P0 |
| Exposure trimming by lower/upper quantiles | Default 0.01/0.99 support trimming | Supported | P0 |
| Propensity score trimming | Stabilizes inverse weighting | Gap or implicit only; needs explicit parameters | P1 |
| Weighted correlation balance diagnostics | Determines whether confounders are balanced | Supported conceptually; needs ArcGIS-compatible balance summary fields | P0 |
| Balance type and threshold | Mean/median/max absolute correlation with default threshold 0.1 | Partial; needs user-facing parity names | P0 |
| ERF table with 200 exposure values | Main causal output | Supported ERF curve; needs exact 200-row parity option | P0 |
| Target exposure values for new outcomes | What-if outcome fields | Supported through target exposure outputs | P0 |
| Target outcome values for new exposures | What-if required-exposure fields | Supported or partially supported; verify output contract | P0 |
| Local ERF popups | Per-feature interactive chart UX | Gap in ArcGIS toolbox; notebook/HTML alternative possible | P2 |
| Bootstrapped ERF confidence intervals | Optional uncertainty output | Partially supported; needs M-out-of-N or documented alternative | P1 |
| Output feature/table fields for scores, weights, trimming | GIS table interoperability | Partially supported; needs ArcGIS-compatible aliases | P0 |

## SCCA Differentiators

The commercial differentiators should be visible in the product, paper, and demo outputs:

1. **Spatial residual diagnostics**: residual Moran's I, exposure Moran's I, and warning interpretation.
2. **Neighborhood-exposure sensitivity**: main coefficient after adding neighboring exposure.
3. **SLX-style sensitivity**: direct, indirect, and total-effect proxy summaries when graph/context data allow.
4. **Graph-sensitivity checks**: coefficient stability across multiple coordinate-kNN graph choices.
5. **Spatial block bootstrap**: sign stability and confidence interval summaries under spatial resampling.
6. **Evidence-grade rules**: machine-readable downgrade rules that prevent overstating GIS causal results.
7. **Open output contract**: CSV, JSON, Markdown, GeoPackage, GeoJSON, Shapefile, static maps, interactive maps, and QGIS styles where possible.
8. **Cross-interface core**: the same `geocausal` core powers notebooks, ArcGIS toolbox, QGIS provider, and command-line runs.

## Benchmark Dataset Strategy

### Primary commercial benchmark: county social capital

Use the county social-capital/longevity dataset because it is already aligned with ArcGIS Causal Inference Analysis examples and has current SCCA outputs:

- Exposure: `SocialAssoc`
- Outcome: `AveAgeDeath`
- Confounders: socioeconomic, health, behavioral, and environmental variables already in the county spec
- Default trimming: 1%-99%
- Target exposure: 70, already represented in target-exposure outputs
- Expected row parity: 3,044 included rows after trimming, matching the ArcGIS-facing example count recorded in the manuscript

This case should become the official **ArcGIS parity benchmark** for Paper6 and SCCA commercialization.

### Secondary spatial caution benchmark: EPA policy-structure semi-synthetic

Use the EPA Green Book/Census benchmark as a public stress test for spatial diagnostics and evidence downgrading. Because AQS AirData acquisition timed out in the current environment, this remains a **policy-structure semi-synthetic benchmark**, not an observational AirData validation case.

### Main empirical credibility case: Chongqing UHI

Retain Chongqing as the main scientific SCCA case, not as the ArcGIS commercial parity case. It supports the method's spatial-context adjustment logic but is less useful as an ArcGIS benchmark because raw inputs are restricted and the exposure is binary.

## Required Product Artifacts

The commercial benchmark should generate:

- `docs/arcgis_causal_inference_parity_matrix.md`
- `docs/scca_commercialization_brief_zh.md`
- `paper/ijgis_submission_20260605/07_results/arcgis_causal_inference_parity/arcgis_parity_matrix.csv`
- `paper/ijgis_submission_20260605/07_results/arcgis_causal_inference_parity/arcgis_parity_summary.md`
- updated manuscript language in `01_manuscript_ijgis.tex`
- updated integration-surface documentation that explains SCCA as an ArcGIS-compatible and ArcGIS-differentiated workflow

## Experiment Design

The ArcGIS parity experiment should not require ArcGIS Pro to be installed for every rerun. It should compare SCCA outputs against the documented ArcGIS tool contract and, when available, against exported ArcGIS example outputs.

Minimum checks:

1. SCCA uses the same input fields as the ArcGIS-facing county example.
2. SCCA trims the same 1%-99% exposure range and reports included/excluded rows.
3. SCCA writes ERF rows over the trimmed exposure support and records whether the row count matches the ArcGIS 200-row convention.
4. SCCA writes target-exposure and target-outcome outputs using ArcGIS-compatible field semantics.
5. SCCA writes propensity-score, balancing-weight, and inclusion/trimming columns or clearly identifies current gaps.
6. SCCA writes the added spatial-diagnostic outputs that ArcGIS does not expose as causal-evidence downgrade rules.
7. The parity report separates **matched**, **partial**, **gap**, and **SCCA-only differentiator** statuses.

## Manuscript Reframing

Paper6 should add an ArcGIS-oriented commercial relevance thread:

- Introduction: explain that current GIS causal tools make causal workflows accessible, but their outputs still need spatial residual diagnostics and evidence boundaries.
- Methods: state that SCCA is implemented as a shared core with ArcGIS/QGIS/notebook adapters.
- Experiments: rename the county case or add a subparagraph as "ArcGIS-facing commercial parity benchmark."
- Discussion: state that SCCA extends GIS causal inference products with open spatial diagnostics and rule-based downgrading.
- Limitations: avoid saying SCCA replaces ArcGIS; state that gradient boosting propensity scores, exact local ERF popups, and ArcGIS-native UI parity remain product-engineering work.

## Acceptance Criteria

This commercial benchmark phase is complete when:

- The parity matrix documents every ArcGIS capability listed above.
- The county benchmark report proves which items are already supported, partial, gaps, or SCCA-only differentiators.
- The manuscript explicitly positions ArcGIS as the commercial baseline and SCCA as an open spatial-diagnostic enhancement.
- The Chinese commercialization brief can be read by a business stakeholder without reading the paper.
- Focused tests for current EPA/evidence-synthesis work still pass.

## Non-Goals

- Do not claim SCCA is a complete ArcGIS Pro replacement.
- Do not reverse engineer proprietary ArcGIS internals.
- Do not require ArcGIS Pro installation for the open benchmark path.
- Do not claim observational AirData validation until AQS data are actually acquired and parsed.
- Do not turn the paper into a product brochure; the commercial positioning should sharpen the method's practical relevance while preserving IJGIS-level scientific caution.
