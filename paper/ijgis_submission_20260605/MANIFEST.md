# Manifest

## Manuscript

| File | Role | Source |
| --- | --- | --- |
| `01_manuscript/01_manuscript_ijgis.tex` | Non-anonymized IJGIS manuscript source | current IJGIS manuscript |
| `01_manuscript/01_manuscript_ijgis_anonymous.tex` | Double-anonymous IJGIS manuscript source | current IJGIS manuscript |
| `06_build/01_manuscript_ijgis.pdf` | Compiled non-anonymized verification PDF | generated from `01_manuscript/01_manuscript_ijgis.tex` |
| `06_build/01_manuscript_ijgis_anonymous.pdf` | Compiled double-anonymous verification PDF | generated from `01_manuscript/01_manuscript_ijgis_anonymous.tex` |

## Standalone Figures

These files mirror the PDF figures referenced by the manuscript and are intended for journal systems that ask for separate figure uploads. PNG copies are included in the same folder for quick visual checking.

| File | Role | Source |
| --- | --- | --- |
| `figures/fig_scca_dag.pdf` | Figure 1 standalone upload file | `scripts/make_review_figures.py` |
| `figures/fig_chongqing_loveplot.pdf` | Chongqing balance figure standalone upload file | `scripts/make_review_figures.py` |
| `figures/fig_chongqing_threshold_curve.pdf` | Threshold-placebo figure standalone upload file | `scripts/make_review_figures.py` |
| `figures/fig_chongqing_residual_moran.pdf` | Residual-Moran figure standalone upload file | `scripts/make_review_figures.py` |
| `figures/fig_threshold_calibration_roc.pdf` | Residual-Moran calibration figure standalone upload file | `scripts/make_review_figures.py` |

## Compile-Time Figure Copies

| File | Role |
| --- | --- |
| `01_manuscript/figures/fig_scca_dag.pdf` | Figure 1 source-side copy for LaTeX compile |
| `01_manuscript/figures/fig_chongqing_loveplot.pdf` | Source-side copy for LaTeX compile |
| `01_manuscript/figures/fig_chongqing_threshold_curve.pdf` | Source-side copy for LaTeX compile |
| `01_manuscript/figures/fig_chongqing_residual_moran.pdf` | Source-side copy for LaTeX compile |
| `01_manuscript/figures/fig_threshold_calibration_roc.pdf` | Source-side copy for LaTeX compile |

## Administrative Files

| File | Role |
| --- | --- |
| `02_cover_letter/cover_letter_ijgis_draft.md` | Cover letter draft for editor-facing submission text |
| `03_supplementary/supplementary_material_plan.md` | Supplement plan and candidate contents |
| `04_admin/title_page_declarations.md` | Author, affiliation, and declarations draft |
| `04_admin/ijgis_submission_checklist.md` | Pre-submission status checklist |
| `04_admin/taylor_francis_anonymous_review_verification.md` | Anonymous-review source record |
| `05_internal_review/ijgis_readiness_notes.md` | Internal journal-fit and revision-risk notes |
| `05_internal_review/ijgis_required_experiments.md` | Retained provenance for earlier required-experiment planning |
