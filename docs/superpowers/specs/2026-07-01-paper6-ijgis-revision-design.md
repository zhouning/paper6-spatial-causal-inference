# Paper 6 IJGIS Revision Design

## Goal

Revise the latest Paper 6 IJGIS manuscript in response to the simulated reviewer concerns by changing the evidence chain, not only the wording. The revised paper should make the Chongqing outcome-scale estimand the main empirical result, downgrade building-level matching to a diagnostic approximation, and add reproducible sensitivity outputs that address balance, scale mismatch, residual spatial structure, and restricted-data transparency.

## Scope

This revision covers the IJGIS submission package under `paper/ijgis_submission_20260605`, the Chongqing and evidence-synthesis experiment scripts under `data_agent/experiments`, review figures under `scripts/make_review_figures.py`, and focused tests in `data_agent/test_*.py`.

The revision does not attempt to obtain new restricted Chongqing raw data. It must work from the existing analysis sample and generated outputs already supported by the repository.

## Review Issues To Resolve

1. The current manuscript presents a building-level ATT as the main Chongqing result even though the outcome is measured on a coarser MODIS pixel grid.
2. The preferred pre-treatment matching specification has maximum post-match SMD `0.104`, slightly above the declared `<0.10` balance threshold.
3. Sentinel-derived variables are treated as possible mediators, but the public audit package does not make the temporal/causal-role evidence boundary explicit enough.
4. The residual-Moran evidence grade is threshold-dependent for Chongqing.
5. The county case is useful for workflow reproducibility but should not read like a second substantive validation case.
6. The manuscript is dense; the main text should foreground the claim boundary and move secondary detail into compressed descriptions.

## Recommended Approach

Use an integrated manuscript-and-experiment revision.

The Chongqing section will report the pixel-aggregated/outcome-scale estimand as the main empirical estimate because it matches the resolution of the LST outcome. The building-level matching estimate will remain in the paper as a diagnostic approximation that supports direction and design auditing but does not carry the primary causal interpretation.

The code will add or expose a matching-sensitivity table for the pre-treatment specification. This table should show whether the slight SMD threshold miss is stable under reasonable matching or caliper alternatives, and it should state whether the paper treats the pre-treatment specification as `near-threshold balance` rather than `balance pass`.

The evidence synthesis will add explicit fields for:

- primary Chongqing estimand family: `outcome_scale_pixel_aggregated`
- building-level role: `diagnostic_approximation`
- pre-treatment balance status: `near_threshold_not_passed` when max SMD is between `0.10` and `0.11`
- residual-Moran threshold dependence for Chongqing
- restricted-data audit boundary and Sentinel temporal-role uncertainty

The manuscript will be rewritten around a narrower claim: SCCA is an auditable GIS-facing protocol for bounded spatial causal adjustment, not a new estimator or identification theorem.

## Algorithm And Experiment Changes

### Chongqing Outcome-Scale Emphasis

`run_change_of_support_analysis` already writes a pixel-aggregated estimand. The evidence-synthesis layer should use this output as the primary Chongqing empirical estimate when available. Building-level rows should remain visible and labeled as building-level approximations.

### Matching Sensitivity

Add a focused sensitivity output for the Chongqing pre-treatment adjustment set. At minimum it should evaluate a small declared set of calipers or matching settings already supported by the local code path. The output should include:

- variant
- setting label
- caliper
- ATT
- CI lower and upper
- max post-match SMD
- balance status
- matched treated and control counts
- interpretation label

The target interpretation labels are:

- `passes_balance` for max post-match SMD `< 0.10`
- `near_threshold_not_passed` for max post-match SMD `>= 0.10` and `< 0.11`
- `fails_balance` for max post-match SMD `>= 0.11`

### Evidence Synthesis

Update `scca_evidence_synthesis.py` so the Chongqing row no longer reads as if the building-level ATT is the main effect. It should report the pixel-aggregated estimate first, then give building-level matching and cluster-robust results as diagnostics.

The grade should remain bounded support unless all current downgrade issues disappear. The point is not to make the result look stronger; it is to make the evidence boundary more defensible.

### Public Audit Package

Extend the Chongqing reviewer audit package with non-sensitive fields that clarify:

- raw Chongqing inputs are not redistributable
- exact public reconstruction of the Chongqing effect is not claimed
- Sentinel variables are excluded from the preferred adjustment set because their pre-treatment status is not publicly auditable from the current package
- the public package supports structural rerun and aggregate audit, not full raw-data replication

### Manuscript Revision

Revise the abstract, contributions, methods, experiments, discussion, conclusion, and data availability sections.

The main text should state:

- SCCA is a diagnostic audit protocol.
- The main Chongqing estimate is an outcome-scale/pixel-aggregated association.
- The building-level ATT is a diagnostic approximation because multiple buildings share the same LST pixel.
- The pre-treatment matching design is causally preferable but slightly misses the strict balance threshold.
- Residual Moran threshold dependence is a warning, not a source of certainty.
- The county case is a GIS workflow reproducibility check.

## Files To Modify

- `data_agent/experiments/chongqing_uhi_analysis.py`
- `data_agent/experiments/scca_evidence_synthesis.py`
- `data_agent/test_chongqing_uhi_analysis.py`
- `data_agent/test_scca_evidence_synthesis.py`
- `scripts/make_review_figures.py` if figure captions or generated visuals need to reflect the new emphasis
- `paper/ijgis_submission_20260605/01_manuscript/01_manuscript_ijgis.tex`
- generated files under `paper/ijgis_submission_20260605/07_results/`
- generated figures under `paper/ijgis_submission_20260605/01_manuscript/figures/` if regenerated

## Testing And Verification

Run focused tests before regenerating manuscript outputs:

- `pytest data_agent/test_chongqing_uhi_analysis.py -q`
- `pytest data_agent/test_scca_evidence_synthesis.py -q`
- `pytest data_agent/test_scca_evidence_rules.py -q`

Regenerate relevant results:

- Chongqing analysis outputs if matching sensitivity is added to that script.
- Evidence synthesis outputs.
- Review figures if manuscript references change.
- LaTeX PDF if a TeX engine is available locally.

Verify:

- the Chongqing evidence row reports the pixel-aggregated estimate first
- the public audit package includes restricted-data and Sentinel role-boundary fields
- the manuscript no longer treats the building-level ATT as the primary empirical claim
- tests pass
- `git status` shows only intended files changed, plus any pre-existing untracked backup file left untouched

## Success Criteria

The revised paper should be able to answer the simulated IJGIS review as follows:

- Scale mismatch is addressed by making the outcome-scale estimate primary.
- The SMD `0.104` issue is openly labeled and supported by sensitivity output.
- Sentinel post-treatment ambiguity is treated as an audit boundary rather than asserted away.
- Residual-Moran threshold dependence is reported as a limitation.
- The county case is clearly framed as workflow reproducibility, not causal validation.
- The manuscript's central claim is narrower, more defensible, and backed by regenerated result artifacts.
