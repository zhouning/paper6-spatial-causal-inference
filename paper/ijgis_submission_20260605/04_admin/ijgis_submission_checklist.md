# IJGIS Submission Checklist

## Package Status

- [x] Main LaTeX source copied into clean IJGIS submission workspace.
- [x] All currently referenced PDF figures copied into `01_manuscript/figures/`.
- [x] Original source snapshot preserved in `90_source_snapshot/`.
- [x] Cover letter draft created.
- [x] Title page and declarations draft created.
- [x] Internal IJGIS readiness notes created.
- [x] Required experiment plan created.
- [x] Compile manuscript from `01_manuscript/`.
- [ ] Inspect generated PDF for figure placement, overfull boxes, and page count.
- [ ] Decide whether IJGIS submission route requires anonymized files.
- [ ] Finalize repository URL and data availability statement.
- [ ] Confirm author information, ORCID IDs, funding, competing interests, and AI-use disclosure.

## Scientific Readiness Checks

- [x] Remove non-core context-source claims from the main manuscript claim.
- [x] Remove the multi-component framework framing from the main manuscript claim.
- [ ] Add a direct comparison against conventional spatial fixed effects, coordinate controls, and remote-sensing covariates.
- [ ] Add sensitivity analysis for unobserved confounding.
- [ ] Add spatial dependence handling, such as spatial block bootstrap, clustered uncertainty, or Moran-style residual diagnostics.
- [ ] Rerun synthetic experiments as a multi-seed benchmark and replace single-run claims.
- [ ] Fix or honestly report synthetic failures observed in stale output files.
- [ ] Clarify that synthetic scenarios validate implementation behavior, not external validity.
- [ ] Check the Chongqing LST analysis for MODIS 1 km aggregation bias and spatial interference.

## Submission File Decisions

- Manuscript: use `01_manuscript/01_manuscript_ijgis.tex` and compiled PDF.
- Figures: embedded in manuscript; upload separately only if the submission system asks.
- Supplement: create a real supplement before upload if added during revision.
- Cover letter: use `02_cover_letter/cover_letter_ijgis_draft.md` after final checks.
- Title/declarations: use `04_admin/title_page_declarations.md` as the source for form fields.
