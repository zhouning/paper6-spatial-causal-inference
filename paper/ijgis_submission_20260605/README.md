# Paper 6 IJGIS Submission Package

This folder is a clean submission workspace for:

**Spatial Context Causal Adjustment: A Diagnostic Workflow for Geographic Observational Studies**

Target journal: International Journal of Geographical Information Science (IJGIS), Taylor & Francis.

Created: 2026-06-05

## Folder Layout

- `01_manuscript/` - Main LaTeX manuscript and all figures required by the current source.
- `02_cover_letter/` - IJGIS cover letter draft.
- `03_supplementary/` - Supplementary-material plan. Populate this before upload if the revision adds supplement content.
- `04_admin/` - Title page, declarations, and submission checklist.
- `05_internal_review/` - Internal IJGIS readiness notes and known risks.
- `05_internal_review/ijgis_required_experiments.md` - Required experiments and step-by-step execution plan before submission.

## Current Upload Candidates

- Manuscript source: `01_manuscript/01_manuscript_ijgis.tex`
- Manuscript figures: `01_manuscript/figures/*.pdf`
- Cover letter draft: `02_cover_letter/cover_letter_ijgis_draft.md`
- Title/declarations draft: `04_admin/title_page_declarations.md`
- Submission checklist: `04_admin/ijgis_submission_checklist.md`

## Compile

Run from `01_manuscript/`:

```powershell
pdflatex -interaction=nonstopmode 01_manuscript_ijgis.tex
bibtex 01_manuscript_ijgis
pdflatex -interaction=nonstopmode 01_manuscript_ijgis.tex
pdflatex -interaction=nonstopmode 01_manuscript_ijgis.tex
```

The manuscript currently uses inline `thebibliography`, so `bibtex` may be unnecessary unless the references are later moved to a `.bib` file.

To keep build artifacts outside the source folder, this package uses `06_build/` during verification:

```powershell
pdflatex '-interaction=nonstopmode' '-output-directory=../06_build' 01_manuscript_ijgis.tex
```

## Before Submission

The current manuscript is organized for IJGIS but should not be treated as submission-ready until the checklist in `04_admin/ijgis_submission_checklist.md` is resolved. The main scientific boundary is now explicit: Chongqing is the main empirical case, the synthetic benchmark is an estimator stress test, and the county social-capital run is a GIS/notebook reproducibility and spatial-diagnostic check rather than a second substantive theory test.
