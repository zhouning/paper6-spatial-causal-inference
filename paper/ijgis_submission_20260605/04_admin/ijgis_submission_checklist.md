# IJGIS Submission Checklist

## Package Status

- [x] Main LaTeX source is in the clean IJGIS submission workspace.
- [x] All currently referenced PDF figures are in `01_manuscript/figures/`.
- [x] Cover letter draft is ready for editor-facing submission text.
- [x] Title page and declarations draft are aligned with the main manuscript.
- [x] Non-anonymized manuscript compiles from `01_manuscript/` into `06_build/`.
- [x] Double-anonymous manuscript variant compiles from `01_manuscript/` into `06_build/`.
- [x] Non-anonymized data and code availability statement includes the public repository URL and restricted-data boundary.
- [x] Double-anonymous manuscript variant withholds the public GitHub URL and author-identifying repository metadata.
- [x] Funding, competing-interest, and AI-use statements are present in the main manuscript and admin file.
- [x] Record Ning Zhou ORCID: https://orcid.org/0009-0002-5647-7388. No co-author ORCID is needed for this single-author submission.
- [x] Check Taylor & Francis generic anonymous-review guidance and record the source basis in `04_admin/taylor_francis_anonymous_review_verification.md`: double-anonymous submissions must remove identifying information, and the Submission Portal may return non-anonymized files when a journal uses double-anonymous review.
- [ ] Confirm the IJGIS-specific peer-review route in the live Taylor & Francis submission portal. The official IJGIS author-instructions page was blocked by Cloudflare from this environment on 2026-07-05, and exact IJGIS single- versus double-anonymous status could not be verified from an accessible official journal page.
- [ ] If the portal requires double-anonymous review and asks for reviewer code/data before review, create an anonymized reviewer-facing archive with `.git`, author names, ORCID, email addresses, public GitHub URL, cover letter, and title/declaration files removed.
- [x] Programmatic PDF checks completed after the last compile: both routes generate PDFs, LaTeX logs contain no undefined citations/references/errors, anonymized PDF text does not expose author names, ORCID, email, affiliation, or public GitHub URL, and sampled rendered pages are nonblank.
- [ ] Manual visual inspection of the final generated PDF is still recommended for figure placement and visual readability because the local image viewer was blocked by the Windows sandbox helper.

## Scientific Readiness Checks

- [x] Reframe SCCA as a diagnostic workflow, not a new identification theorem.
- [x] Remove strong GeoFM, LLM, and world-model claims from the main manuscript claim.
- [x] Clarify that synthetic scenarios are estimator stress tests, not external validity evidence.
- [x] Report synthetic fragility honestly and include a clean synthetic positive control.
- [x] Add Chongqing adjustment variants, balance diagnostics, threshold sensitivity, residual Moran diagnostics, and change-of-support audit.
- [x] Report the Chongqing primary result as an outcome-scale pixel slope, not a building-level ATT.
- [x] Keep the strict-balance near miss and residual-spatial warning visible in the abstract, results, discussion, and conclusion.
- [x] Bound the county social-capital case as ArcGIS SCI-style algorithmic comparison and GIS reproducibility evidence, not independent substantive causal validation.
- [x] State restricted Chongqing raw-data limits and third-party county-data provenance in Data and Code Availability.

## Submission File Decisions

- Manuscript, non-anonymized route: use `01_manuscript/01_manuscript_ijgis.tex` and `06_build/01_manuscript_ijgis.pdf`.
- Manuscript, double-anonymous route: use `01_manuscript/01_manuscript_ijgis_anonymous.tex` and `06_build/01_manuscript_ijgis_anonymous.pdf`; keep title/declarations separate for editor-only form fields.
- Figures: embedded in manuscript; upload separately only if the submission system asks.
- Supplement: do not upload the placeholder supplement plan. Upload `03_supplementary/supplementary_proofs_and_outputs.pdf` only if IJGIS requests supplementary material and the contents are final-reviewed.
- Cover letter: use `02_cover_letter/cover_letter_ijgis_draft.md`.
- Title/declarations: use `04_admin/title_page_declarations.md` as the source for form fields.
