# Paper 6 IJGIS Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revise Paper 6 so the IJGIS manuscript and generated evidence artifacts make the Chongqing outcome-scale estimand primary and clearly label building-level matching as diagnostic.

**Architecture:** The existing Chongqing analysis already computes change-of-support rows, including a pixel-aggregated estimand. This plan adds a matching-sensitivity artifact, updates evidence synthesis to prioritize the pixel-aggregated estimate and public audit boundaries, then rewrites the manuscript around the narrower claim.

**Tech Stack:** Python, pandas, pytest, LaTeX, existing `data_agent` experiment utilities.

---

### Task 1: Add Red Tests For Chongqing Sensitivity And Evidence Reframing

**Files:**
- Modify: `data_agent/test_chongqing_uhi_analysis.py`
- Modify: `data_agent/test_scca_evidence_synthesis.py`

- [ ] **Step 1: Add a failing test for matching sensitivity output**

Append this test to `data_agent/test_chongqing_uhi_analysis.py`:

```python
def test_run_matching_sensitivity_labels_near_threshold_balance():
    from data_agent.experiments.chongqing_uhi_analysis import run_matching_sensitivity

    sensitivity = run_matching_sensitivity(
        _matched_uhi_fixture(),
        variant="pre_treatment",
        threshold=10,
        calipers=(0.2,),
        n_bootstrap=20,
        random_state=0,
    )

    assert {
        "variant",
        "setting_label",
        "caliper",
        "att",
        "ci_lower",
        "ci_upper",
        "max_post_smd",
        "balance_status",
        "matched_treated_n",
        "matched_control_n",
        "interpretation_label",
    }.issubset(sensitivity.columns)
    assert set(sensitivity["variant"]) == {"pre_treatment"}
    assert sensitivity["interpretation_label"].isin(
        {"passes_balance", "near_threshold_not_passed", "fails_balance"}
    ).all()
```

- [ ] **Step 2: Add a failing test for writer contract**

In `test_chongqing_feature_specs_and_writer_contract`, create a `matching_sensitivity` DataFrame and pass it to `write_chongqing_outputs`. Add the expected output path and assert it exists:

```python
matching_sensitivity = pd.DataFrame(
    [
        {
            "variant": "pre_treatment",
            "setting_label": "caliper_0.20",
            "caliper": 0.2,
            "att": 0.2,
            "ci_lower": 0.1,
            "ci_upper": 0.3,
            "max_post_smd": 0.104,
            "balance_status": "near_threshold_not_passed",
            "matched_treated_n": 5,
            "matched_control_n": 5,
            "interpretation_label": "near_threshold_not_passed",
        }
    ]
)
```

Call:

```python
manifest = write_chongqing_outputs(
    output_dir=tmp_path,
    ablation=ablation,
    balance=balance,
    matched_counts=matched_counts,
    bootstrap=bootstrap,
    placebos=placebos,
    residual_diagnostics=residuals,
    matching_sensitivity=matching_sensitivity,
    metadata={"sample_size": 12, "treatment_threshold": 10},
)
```

Expected path:

```python
"matching_sensitivity_csv": tmp_path / "chongqing_matching_sensitivity.csv",
```

- [ ] **Step 3: Add a failing test for evidence synthesis**

In `data_agent/test_scca_evidence_synthesis.py`, after reading `synthesis`, add:

```python
chongqing_effect = synthesis.loc[
    synthesis["case"] == "chongqing_uhi",
    "effect_estimate",
].iloc[0]
assert chongqing_effect.startswith("Outcome-scale pixel ATT")
assert "building-level matching ATT" in chongqing_effect
assert "diagnostic approximation" in synthesis.loc[
    synthesis["case"] == "chongqing_uhi",
    "manuscript_use",
].iloc[0]
```

After reading `public_audit`, add:

```python
assert {
    "raw_chongqing_inputs_redistributed",
    "public_reconstruction_claim",
    "sentinel_pre_treatment_status_publicly_auditable",
    "primary_chongqing_estimand_family",
    "building_level_matching_role",
}.issubset(set(public_audit["item"]))
```

- [ ] **Step 4: Run the red tests**

Run:

```bash
pytest data_agent/test_chongqing_uhi_analysis.py::test_run_matching_sensitivity_labels_near_threshold_balance data_agent/test_scca_evidence_synthesis.py::test_scca_evidence_synthesis_writes_contract_files -q
```

Expected: fail because `run_matching_sensitivity`, `matching_sensitivity_csv`, and the new evidence text/audit fields do not exist yet.

### Task 2: Implement Matching Sensitivity Artifact

**Files:**
- Modify: `data_agent/experiments/chongqing_uhi_analysis.py`
- Modify: `data_agent/test_chongqing_uhi_analysis.py`

- [ ] **Step 1: Add output filename**

Add to `OUTPUT_FILES`:

```python
"matching_sensitivity_csv": "chongqing_matching_sensitivity.csv",
```

- [ ] **Step 2: Add balance interpretation helper**

Add near `_balance_interpretation`:

```python
def _match_balance_status(max_post_smd: Any) -> str:
    value = _finite_float(max_post_smd)
    if value is None:
        return "not_evaluated"
    if value < 0.10:
        return "passes_balance"
    if value < 0.11:
        return "near_threshold_not_passed"
    return "fails_balance"
```

If `_finite_float` is not available in this file, add:

```python
def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None
```

- [ ] **Step 3: Add `run_matching_sensitivity`**

Add after `run_threshold_placebos`:

```python
def run_matching_sensitivity(
    frame: pd.DataFrame,
    *,
    variant: str = "pre_treatment",
    threshold: int = 10,
    calipers: Iterable[float] = (0.15, 0.20, 0.25),
    n_bootstrap: int = 100,
    random_state: int = 0,
    outcome_col: str = "LST",
) -> pd.DataFrame:
    """Run declared caliper sensitivity for one Chongqing matching variant."""
    rows: list[dict[str, Any]] = []
    for offset, caliper in enumerate(calipers):
        row, _, _, _ = _match_variant(
            frame,
            variant=variant,
            threshold=threshold,
            caliper=float(caliper),
            n_bootstrap=n_bootstrap,
            random_state=random_state + offset,
            outcome_col=outcome_col,
        )
        status = _match_balance_status(row.get("max_post_smd"))
        rows.append(
            {
                "variant": variant,
                "setting_label": f"caliper_{float(caliper):.2f}",
                "caliper": float(caliper),
                "att": row.get("att"),
                "ci_lower": row.get("ci_lower"),
                "ci_upper": row.get("ci_upper"),
                "max_post_smd": row.get("max_post_smd"),
                "balance_status": status,
                "matched_treated_n": row.get("matched_treated_n"),
                "matched_control_n": row.get("matched_control_n"),
                "interpretation_label": status,
            }
        )
    return pd.DataFrame(rows)
```

- [ ] **Step 4: Wire sensitivity into full run and writer**

In `run_chongqing_uhi_analysis`, compute:

```python
matching_sensitivity = run_matching_sensitivity(
    frame,
    variant="pre_treatment",
    threshold=threshold,
    calipers=(0.15, 0.20, 0.25),
    n_bootstrap=max(20, min(n_bootstrap, 100)),
    random_state=random_state,
    outcome_col=outcome_col,
)
```

Pass `matching_sensitivity=matching_sensitivity` to `write_chongqing_outputs`.

Update `write_chongqing_outputs` signature:

```python
matching_sensitivity: pd.DataFrame | None = None,
```

Add:

```python
if matching_sensitivity is not None:
    frames["matching_sensitivity_csv"] = matching_sensitivity
```

- [ ] **Step 5: Run green tests**

Run:

```bash
pytest data_agent/test_chongqing_uhi_analysis.py -q
```

Expected: pass.

### Task 3: Reframe Evidence Synthesis And Public Audit Package

**Files:**
- Modify: `data_agent/experiments/scca_evidence_synthesis.py`
- Modify: `data_agent/test_scca_evidence_synthesis.py`

- [ ] **Step 1: Read pixel-aggregated row first**

In `_chongqing_row`, replace the current `cos_text` construction with logic that extracts:

```python
pixel = prim[prim["estimand"] == "pixel_aggregated"]
cluster = prim[prim["estimand"] == "building_cluster_robust"]
```

Use this effect text when both exist:

```python
effect_text = (
    f"Outcome-scale pixel ATT = {_fmt_num(pixel.iloc[0].get('att'))} C; "
    f"95% CI [{_fmt_num(pixel.iloc[0].get('ci_lower'))}, "
    f"{_fmt_num(pixel.iloc[0].get('ci_upper'))}]; "
    f"building-level matching ATT = {_fmt_num(record.get('att'))} C "
    f"(diagnostic approximation; matching CI {ci}); "
    f"cluster-robust building OLS ATT = {_fmt_num(cluster.iloc[0].get('att'))} C "
    f"(CR SE {_fmt_num(cluster.iloc[0].get('se'))}); "
    f"over-adjusted full-RS matching ATT = {full_att} C"
)
```

Fall back to the existing matching text only when change-of-support rows are missing.

- [ ] **Step 2: Add matching sensitivity to balance status**

Read `chongqing_matching_sensitivity.csv` in `_chongqing_row`. If present, append:

```python
; matching sensitivity labels = <labels>
```

to `balance_status`.

- [ ] **Step 3: Reword Chongqing row metadata**

Use:

```python
best_adjustment="outcome-scale pixel aggregation with pre-treatment context; building-level matching retained as diagnostic"
```

Use:

```python
manuscript_use="Use as the main real-data SCCA case; report the outcome-scale pixel estimate as primary and building-level matching as a diagnostic approximation with residual-spatial caution."
```

- [ ] **Step 4: Extend public audit package rows**

At the start of `build_chongqing_reviewer_audit_package`, append these rows:

```python
for item, value in (
    ("raw_chongqing_inputs_redistributed", "False"),
    ("public_reconstruction_claim", "structural_rerun_and_aggregate_audit_only"),
    ("sentinel_pre_treatment_status_publicly_auditable", "False"),
    ("primary_chongqing_estimand_family", "outcome_scale_pixel_aggregated"),
    ("building_level_matching_role", "diagnostic_approximation"),
):
    rows.append(_audit_row(item, value, "Data and Code Availability"))
```

Also append pre-treatment and pixel-aggregated change-of-support rows when available.

- [ ] **Step 5: Run green tests**

Run:

```bash
pytest data_agent/test_scca_evidence_synthesis.py -q
pytest data_agent/test_scca_evidence_rules.py -q
```

Expected: pass.

### Task 4: Regenerate Result Artifacts

**Files:**
- Modify generated files under `paper/ijgis_submission_20260605/07_results/`

- [ ] **Step 1: Regenerate Chongqing outputs if sample exists**

Run:

```bash
python -m data_agent.experiments.chongqing_uhi_analysis
```

Expected: `paper/ijgis_submission_20260605/07_results/chongqing_matching_sensitivity.csv` exists. If the module requires restricted local inputs not available through its default entrypoint, use the repository's existing wrapper or skip this step and document the blocker.

- [ ] **Step 2: Regenerate evidence synthesis**

Run:

```bash
python -m data_agent.experiments.scca_evidence_synthesis
```

Expected: `scca_evidence_synthesis.csv`, `scca_evidence_synthesis_report.md`, `chongqing_reviewer_audit_package.csv`, and JSON package update.

- [ ] **Step 3: Regenerate review figures if needed**

Run:

```bash
python scripts/make_review_figures.py
```

Expected: figures regenerate without error.

### Task 5: Revise Manuscript Text

**Files:**
- Modify: `paper/ijgis_submission_20260605/01_manuscript/01_manuscript_ijgis.tex`

- [ ] **Step 1: Rewrite abstract outcome paragraph**

Replace the Chongqing result sentence with text that starts from the pixel-aggregated estimate and then labels building-level matching as diagnostic.

- [ ] **Step 2: Tighten contributions**

Adjust contribution bullets so the first contribution is an audit protocol, the second is outcome-scale/change-of-support reporting, and the residual-Moran threshold is described as a warning rule.

- [ ] **Step 3: Revise Chongqing case subsection**

Make the order:

1. Data and scale.
2. Primary outcome-scale estimand.
3. Building-level matching diagnostic.
4. Pre-treatment versus Sentinel over-adjustment.
5. Residual spatial caution and threshold dependence.

- [ ] **Step 4: Reframe county case**

Change language from validation/external evidence to workflow reproducibility and spatial-diagnostic boundary check.

- [ ] **Step 5: Revise discussion, conclusion, and data availability**

Ensure the final claim is that SCCA makes assumptions and boundaries inspectable in GIS-facing workflows.

### Task 6: Final Verification

**Files:**
- Verify repository state only; do not edit unless failures are found.

- [ ] **Step 1: Run focused tests**

Run:

```bash
pytest data_agent/test_chongqing_uhi_analysis.py data_agent/test_scca_evidence_synthesis.py data_agent/test_scca_evidence_rules.py -q
```

Expected: pass.

- [ ] **Step 2: Compile manuscript if TeX is available**

Run from `paper/ijgis_submission_20260605/01_manuscript`:

```bash
pdflatex -interaction=nonstopmode 01_manuscript_ijgis.tex
bibtex 01_manuscript_ijgis
pdflatex -interaction=nonstopmode 01_manuscript_ijgis.tex
pdflatex -interaction=nonstopmode 01_manuscript_ijgis.tex
```

Expected: PDF generated. If `bibtex` is unnecessary because references are inline, document the actual compile path used.

- [ ] **Step 3: Check diff**

Run:

```bash
git status --short
git diff --stat
```

Expected: only intended code, tests, generated results, figures, and manuscript files changed; pre-existing `01_manuscript_ijgis.v1.bak.tex` remains untracked and untouched.
