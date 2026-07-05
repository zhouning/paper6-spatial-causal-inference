# Paper 6 IJGIS Submission Package

This folder is a clean submission workspace for:

**Spatial Context Causal Adjustment: A Diagnostic Workflow for Geographic Observational Studies**

Target journal: International Journal of Geographical Information Science (IJGIS), Taylor & Francis.

Created: 2026-06-05

## Folder Layout

- `01_manuscript/` - Main LaTeX manuscript variants and compile-time figure copies required by the current source.
- `figures/` - Standalone PDF/PNG figure files for journal systems that request separate figure uploads.
- `02_cover_letter/` - IJGIS cover letter draft.
- `03_supplementary/` - Supplementary-material plan. Populate this before upload if the revision adds supplement content.
- `04_admin/` - Title page, declarations, and submission checklist.
- `05_internal_review/` - Internal IJGIS readiness notes and known risks.
- `05_internal_review/ijgis_required_experiments.md` - Required experiments and step-by-step execution plan before submission.

## Current Upload Candidates

- Non-anonymized manuscript source: `01_manuscript/01_manuscript_ijgis.tex`
- Double-anonymous manuscript source: `01_manuscript/01_manuscript_ijgis_anonymous.tex`
- Manuscript figure copies for LaTeX: `01_manuscript/figures/*.pdf`
- Standalone upload figures: `figures/*.pdf` (`figures/*.png` copies are also included for visual checking)
- Cover letter draft: `02_cover_letter/cover_letter_ijgis_draft.md`
- Title/declarations draft: `04_admin/title_page_declarations.md`
- Submission checklist: `04_admin/ijgis_submission_checklist.md`
- Anonymous-review verification note: `04_admin/taylor_francis_anonymous_review_verification.md`

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
pdflatex '-interaction=nonstopmode' '-output-directory=../06_build' 01_manuscript_ijgis_anonymous.tex
```

## Before Submission

This package now keeps both submission routes available. Use the non-anonymized manuscript if the live Taylor & Francis/IJGIS workflow does not require double-anonymous review. Use the anonymized manuscript if the portal or file-upload instructions indicate double-anonymous review.

The main scientific boundary is explicit: Chongqing is the main empirical case, the synthetic benchmark is an estimator stress test, and the county social-capital run is an ArcGIS/GIS reproducibility and spatial-diagnostic check rather than a second substantive theory test. Ning Zhou is the sole author, with SuperMap Software Co., Ltd. as the affiliation. The ORCID is recorded in the non-anonymized manuscript and title-page draft. Taylor & Francis Author Services confirms that double-anonymous submissions must remove identifying information, but the IJGIS-specific author-instructions page was blocked by Cloudflare from this environment on 2026-07-05. See `04_admin/taylor_francis_anonymous_review_verification.md` for the source record, then confirm the live IJGIS route in the submission portal before choosing the upload file.
