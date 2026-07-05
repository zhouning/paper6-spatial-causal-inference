# Taylor & Francis Anonymous-Review Verification

Date checked: 2026-07-05

## Accessible official sources checked

- Taylor & Francis Author Services, Anonymous peer review: https://authorservices.taylorandfrancis.com/publishing-your-research/peer-review/anonymous-peer-review/
- Taylor & Francis Author Services, Types of peer review: https://authorservices.taylorandfrancis.com/publishing-your-research/peer-review/types-peer-review/
- Taylor & Francis Author Services, Using the Taylor & Francis Submission Portal: https://authorservices.taylorandfrancis.com/publishing-your-research/making-your-submission/using-taylor-francis-submission-portal/

## What these official sources establish

- Taylor & Francis distinguishes single-anonymous and double-anonymous peer review.
- For journals using double-anonymous review, authors should provide both a manuscript with author details and a manuscript without author details.
- The anonymous manuscript should remove author-identifying information, including author names, affiliations, acknowledgements, funding details that reveal identity, file metadata, and author-identifying self-references where applicable.
- In the Taylor & Francis Submission Portal, a journal using double-anonymous review expects a file categorized as `Manuscript - anonymous`; figures, tables, and other reviewer-facing files also need anonymization.
- The portal warns that a non-anonymized manuscript for a double-anonymous journal may be returned before review.

## IJGIS-specific status

The IJGIS/Taylor & Francis author-instructions URL attempted from this environment was:

https://www.tandfonline.com/action/authorSubmission?journalCode=tgis20&page=instructions

Both the browser-backed lookup and local `curl.exe -L --max-time 25 -A "Mozilla/5.0"` returned a Cloudflare challenge page rather than the journal instructions. Therefore, the exact IJGIS single- versus double-anonymous review route was not verifiable from an accessible IJGIS-specific official page in this environment on 2026-07-05.

## Current package decision

Keep both upload routes ready:

- Non-anonymized route: `01_manuscript/01_manuscript_ijgis.tex` and `06_build/01_manuscript_ijgis.pdf`.
- Double-anonymous route: `01_manuscript/01_manuscript_ijgis_anonymous.tex` and `06_build/01_manuscript_ijgis_anonymous.pdf`.

Before upload, confirm the route shown inside the live Taylor & Francis/IJGIS submission portal. If the portal requests double-anonymous review, use the anonymized manuscript and the anonymized 4open repository link for reviewer-facing code/data access.