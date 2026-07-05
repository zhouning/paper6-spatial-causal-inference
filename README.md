# Spatial Context Causal Adjustment (SCCA)

This repository contains the reproduction package and software boundary for the IJGIS manuscript:

**Spatial Context Causal Adjustment: A Diagnostic Workflow for Geographic Observational Studies**

For peer review, the anonymized repository is available at:

https://anonymous.4open.science/r/spatial-causal-inference-FDFE

SCCA is not a new causal estimator or identification theorem. It is a diagnostic workflow that wraps standard causal estimators with spatial-context construction, adjustment-set comparison, support and balance diagnostics, spatial robustness checks, residual-spatial warnings, and evidence grading.

## Current Paper Scope

The current IJGIS submission evaluates SCCA through four bounded components:

- **Chongqing urban heat case**: the main empirical case. The primary claim is an outcome-scale MODIS pixel result, while building-level matching is retained as a diagnostic approximation.
- **Synthetic stress tests**: controlled estimator and evidence-grade tests, used to characterize failure modes rather than external validity.
- **County ArcGIS Causal Inference parity case**: a GIS reproducibility and algorithm-comparison case using third-party Esri training/demo data, not an independent substantive validation case.
- **Synthetic positive control**: a clean design that should receive core support under the evidence-grade rules.

The manuscript deliberately reports bounded support where diagnostics require it. It does not claim to remove unmeasured spatial confounding, solve interference, or make restricted Chongqing raw inputs publicly reproducible.

## Repository Layout

- `data_agent/`: SCCA analysis modules, evidence rules, diagnostics, and experiment runners used by the manuscript.
- `geocausal/`: YAML-first CLI and adapter boundary for reusable GeoCausal/SCCA workflows.
- `arcgis_toolbox/`: ArcGIS Pro toolbox wrapper and county workflow notes.
- `qgis_provider/`: QGIS Processing provider skeleton.
- `examples/`: runnable county social-capital example configuration and CSV input.
- `paper/ijgis_submission_20260605/`: IJGIS manuscript package, generated figures, generated results, submission notes, and compiled PDFs.
- `DATA_AVAILABILITY.md`: restricted-data and reviewer-access notes.
- `REPRODUCIBILITY.md`: reproduction notes for public and restricted-input analyses.

## IJGIS Submission Files

The latest manuscript PDFs are generated under:

- `paper/ijgis_submission_20260605/06_build/01_manuscript_ijgis.pdf`
- `paper/ijgis_submission_20260605/06_build/01_manuscript_ijgis_anonymous.pdf`

Use the non-anonymized PDF if the live Taylor & Francis/IJGIS route does not require double-anonymous review. Use the anonymous PDF if the portal requests double-anonymous review. The anonymous-review source record is stored in `paper/ijgis_submission_20260605/04_admin/taylor_francis_anonymous_review_verification.md`.

## Quick Start

Use Python 3.11+ from the repository root.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

On Windows:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
```

Run the focused manuscript verification suite:

```bash
python -m pytest \
  data_agent/test_scca_evidence_rules.py \
  data_agent/test_scca_evidence_synthesis.py \
  data_agent/test_chongqing_uhi_analysis.py \
  data_agent/test_arcgis_sci_plus.py \
  data_agent/test_arcgis_sci_plus_county.py \
  data_agent/test_scca_county_social_capital.py \
  data_agent/test_scca_spatial_diagnostics.py
```

## Regenerate Manuscript Figures

The manuscript figures are generated with Python/matplotlib:

```bash
python scripts/make_review_figures.py
```

Figures are written to:

```text
paper/ijgis_submission_20260605/01_manuscript/figures/
```

## Compile Manuscript PDFs

Run from `paper/ijgis_submission_20260605/01_manuscript/`:

```powershell
pdflatex '-interaction=nonstopmode' '-output-directory=../06_build' 01_manuscript_ijgis.tex
pdflatex '-interaction=nonstopmode' '-output-directory=../06_build' 01_manuscript_ijgis_anonymous.tex
```

The manuscript currently uses an inline `thebibliography`, so BibTeX is not required unless references are later moved to a `.bib` file.

## Data Availability Boundary

The anonymized reviewer-facing repository contains manuscript source, code, synthetic generators, generated result tables, figures, diagnostic reports, and redistributable public/example data.

Raw Chongqing geospatial inputs and the building-level UHI analysis sample are not publicly redistributed because they include precise geometries or coordinates, floor attributes, and derived environmental variables. The repository includes aggregate-level Chongqing audit artifacts that support reviewer inspection without redistributing restricted raw geometries or building-level coordinates.

The county ArcGIS parity case uses third-party Esri training/demo data. Use is governed by the source terms documented in the data availability notes.

## Citation

A formal citation will be added after review. During peer review, use the anonymized 4open repository link above for reviewer-facing reproduction access.