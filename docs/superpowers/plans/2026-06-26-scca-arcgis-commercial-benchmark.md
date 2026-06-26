# SCCA ArcGIS Commercial Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a commercial-facing ArcGIS Causal Inference Analysis benchmark layer for Paper6/SCCA that documents parity, gaps, differentiators, and manuscript positioning.

**Architecture:** Add a small reporting package around existing SCCA county-social-capital outputs rather than replacing the causal engine. The benchmark reads current result artifacts, writes an ArcGIS parity matrix and summary report, then updates documentation and manuscript language to position SCCA as an open spatial-diagnostic enhancement to GIS causal inference tools.

**Tech Stack:** Python, pandas, existing `geocausal`/SCCA result artifacts, Markdown, CSV, LaTeX, pytest.

---

## File Structure

- Create `data_agent/experiments/arcgis_commercial_benchmark.py`: build static ArcGIS parity rows, inspect SCCA result artifacts, and write CSV/Markdown reports.
- Create `data_agent/test_arcgis_commercial_benchmark.py`: tests for parity rows, status classification, and report output contract.
- Create `docs/arcgis_causal_inference_parity_matrix.md`: human-readable capability comparison.
- Create `docs/scca_commercialization_brief_zh.md`: Chinese business-facing commercialization brief.
- Modify `docs/geocausal_integration_surfaces.md`: add ArcGIS commercial benchmark positioning.
- Modify `paper/ijgis_submission_20260605/01_manuscript/01_manuscript_ijgis.tex`: add concise ArcGIS-facing commercial relevance language.
- Generated directory `paper/ijgis_submission_20260605/07_results/arcgis_causal_inference_parity/`.

### Task 1: ArcGIS Parity Matrix Contract

**Files:**
- Create: `data_agent/test_arcgis_commercial_benchmark.py`
- Create later: `data_agent/experiments/arcgis_commercial_benchmark.py`

- [ ] **Step 1: Write failing test for required ArcGIS capability rows**

```python
def test_arcgis_parity_matrix_contains_required_capabilities():
    from data_agent.experiments.arcgis_commercial_benchmark import build_arcgis_parity_matrix

    matrix = build_arcgis_parity_matrix()
    capabilities = set(matrix["arcgis_capability"])

    assert "continuous_exposure_outcome_workflow" in capabilities
    assert "ols_or_gradient_boosting_propensity_score" in capabilities
    assert "propensity_score_matching" in capabilities
    assert "inverse_propensity_score_weighting" in capabilities
    assert "one_to_ninetynine_exposure_trimming" in capabilities
    assert "weighted_correlation_balance_threshold" in capabilities
    assert "erf_table" in capabilities
    assert "target_exposure_and_target_outcome_fields" in capabilities
    assert "local_erf_popups" in capabilities
    assert "spatial_residual_diagnostics" in capabilities
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_arcgis_commercial_benchmark.py::test_arcgis_parity_matrix_contains_required_capabilities -v`

Expected: FAIL because `arcgis_commercial_benchmark` does not exist.

- [ ] **Step 3: Implement static parity matrix**

Create `build_arcgis_parity_matrix()` returning a pandas DataFrame with columns:

```python
[
    "arcgis_capability",
    "arcgis_product_meaning",
    "scca_status",
    "commercial_priority",
    "evidence_artifact",
    "next_action",
]
```

Use statuses only from:

```python
{"matched", "partial", "gap", "scca_only_differentiator"}
```

- [ ] **Step 4: Run test to verify pass**

Run: `D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_arcgis_commercial_benchmark.py::test_arcgis_parity_matrix_contains_required_capabilities -v`

Expected: PASS.

### Task 2: County Benchmark Artifact Inspection

**Files:**
- Modify: `data_agent/test_arcgis_commercial_benchmark.py`
- Modify: `data_agent/experiments/arcgis_commercial_benchmark.py`

- [ ] **Step 1: Write failing test for county result inspection**

```python
def test_inspect_county_outputs_records_arcgis_parity_metrics(tmp_path):
    from data_agent.experiments.arcgis_commercial_benchmark import inspect_county_parity_artifacts

    results_dir = tmp_path / "07_results"
    results_dir.mkdir()
    (results_dir / "county_social_capital_spatial_notebook_summary.json").write_text(
        json.dumps(
            {
                "result_summary": {
                    "baseline_adjusted_ols": {"coef": 0.181, "n": 3044},
                    "spatial_diagnostics": {"residual_moran_i": 0.313},
                },
                "spatial_manifest": {"row_count": 3108, "matched_count": 3044},
            }
        ),
        encoding="utf-8",
    )

    metrics = inspect_county_parity_artifacts(results_dir)

    assert metrics["input_rows"] == 3108
    assert metrics["included_rows"] == 3044
    assert metrics["baseline_coef"] == pytest.approx(0.181)
    assert metrics["residual_moran_i"] == pytest.approx(0.313)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_arcgis_commercial_benchmark.py::test_inspect_county_outputs_records_arcgis_parity_metrics -v`

Expected: FAIL because helper is missing.

- [ ] **Step 3: Implement artifact inspection**

Read `county_social_capital_spatial_notebook_summary.json`, extract:

- `input_rows`
- `included_rows`
- `baseline_coef`
- `spatial_neighbor_adjusted_coef`
- `spatial_lag_adjusted_coef`
- `residual_moran_i`
- `residual_moran_p_value`
- `spatial_files_available`
- `visualization_files_available`

Return `None` or `"NA"` only when an artifact is genuinely absent.

- [ ] **Step 4: Run test to verify pass**

Run: `D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_arcgis_commercial_benchmark.py::test_inspect_county_outputs_records_arcgis_parity_metrics -v`

Expected: PASS.

### Task 3: Report Writer and CLI

**Files:**
- Modify: `data_agent/test_arcgis_commercial_benchmark.py`
- Modify: `data_agent/experiments/arcgis_commercial_benchmark.py`

- [ ] **Step 1: Write failing output contract test**

```python
def test_write_arcgis_commercial_benchmark_outputs(tmp_path):
    from data_agent.experiments.arcgis_commercial_benchmark import write_arcgis_commercial_benchmark

    manifest = write_arcgis_commercial_benchmark(output_dir=tmp_path, results_dir=tmp_path)

    assert (tmp_path / "arcgis_parity_matrix.csv").exists()
    assert (tmp_path / "arcgis_parity_summary.md").exists()
    assert (tmp_path / "arcgis_commercial_benchmark_manifest.json").exists()
    assert manifest["parity_matrix_csv"].endswith("arcgis_parity_matrix.csv")
    assert manifest["status_counts"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_arcgis_commercial_benchmark.py::test_write_arcgis_commercial_benchmark_outputs -v`

Expected: FAIL because writer is missing.

- [ ] **Step 3: Implement writer and CLI**

Add:

```python
def write_arcgis_commercial_benchmark(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    results_dir: str | Path = DEFAULT_RESULTS_DIR,
) -> dict[str, Any]:
    ...
```

Write:

- `arcgis_parity_matrix.csv`
- `arcgis_parity_summary.md`
- `arcgis_commercial_benchmark_manifest.json`

Add CLI:

```bash
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.arcgis_commercial_benchmark
```

- [ ] **Step 4: Run test to verify pass**

Run: `D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_arcgis_commercial_benchmark.py -v`

Expected: PASS.

### Task 4: Documentation Artifacts

**Files:**
- Create: `docs/arcgis_causal_inference_parity_matrix.md`
- Create: `docs/scca_commercialization_brief_zh.md`
- Modify: `docs/geocausal_integration_surfaces.md`

- [ ] **Step 1: Create ArcGIS parity matrix Markdown**

Include:

- ArcGIS baseline scope
- SCCA matched features
- partial features
- gaps
- SCCA-only differentiators
- direct link to official ArcGIS tool page
- link to generated `07_results/arcgis_causal_inference_parity/arcgis_parity_matrix.csv`

- [ ] **Step 2: Create Chinese commercialization brief**

Include:

- target users
- business pain point
- ArcGIS baseline
- SCCA product value
- MVP package
- product roadmap
- risk boundaries

- [ ] **Step 3: Update integration surfaces doc**

Add one subsection under "ArcGIS Pro Use":

```markdown
### Commercial Benchmark Positioning
...
```

State that the ArcGIS toolbox is a thin adapter and the commercial benchmark is a product comparison layer, not a separate causal engine.

- [ ] **Step 4: Verify docs mention key terms**

Run: `rg -n "ArcGIS Causal Inference Analysis|commercial|parity|spatial-diagnostic|evidence grade" docs`

Expected: each new document appears in search results.

### Task 5: Manuscript Reframing

**Files:**
- Modify: `paper/ijgis_submission_20260605/01_manuscript/01_manuscript_ijgis.tex`

- [ ] **Step 1: Update introduction contribution language**

Add one sentence after the interface/reproducibility contribution:

```latex
The implementation is also evaluated against the operational contract of ArcGIS Pro's Causal Inference Analysis workflow, using the county case as a GIS-facing commercial parity benchmark while preserving a stricter spatial-diagnostic evidence boundary.
```

- [ ] **Step 2: Update county subsection framing**

Rename or extend the county subsection so it reads as:

```latex
\subsection{County GIS, ArcGIS-facing parity, and spatial-diagnostic validation}
```

Add a paragraph that states:

- ArcGIS provides the commercial baseline vocabulary.
- SCCA reproduces the county workflow count/direction.
- SCCA adds spatial diagnostics and bounded support downgrading.

- [ ] **Step 3: Update Discussion practical value**

Add a paragraph explaining SCCA's product value:

- not replacing ArcGIS,
- open core,
- inspectable outputs,
- spatial downgrade logic,
- deployable across ArcGIS/QGIS/notebook surfaces.

- [ ] **Step 4: Compile LaTeX**

Run from `paper/ijgis_submission_20260605/01_manuscript`:

```bash
pdflatex 01_manuscript_ijgis.tex
bibtex 01_manuscript_ijgis
pdflatex 01_manuscript_ijgis.tex
pdflatex 01_manuscript_ijgis.tex
```

Expected: PDF generated without fatal errors.

### Task 6: Verification and Commit

**Files:**
- All files above

- [ ] **Step 1: Run focused test suite**

Run:

```bash
D:\adk\.venv\Scripts\python.exe -m pytest data_agent/test_arcgis_commercial_benchmark.py data_agent/test_epa_airdata_benchmark.py data_agent/test_epa_airdata_panel.py data_agent/test_scca_evidence_synthesis_epa.py data_agent/test_scca_evidence_synthesis.py -v
```

Expected: PASS.

- [ ] **Step 2: Run commercial benchmark CLI**

Run:

```bash
D:\adk\.venv\Scripts\python.exe -m data_agent.experiments.arcgis_commercial_benchmark
```

Expected: generated files under `paper/ijgis_submission_20260605/07_results/arcgis_causal_inference_parity/`.

- [ ] **Step 3: Inspect git status**

Run: `git status --short`

Expected: only Paper6/SCCA benchmark, docs, manuscript, and generated result artifacts are changed.

- [ ] **Step 4: Commit**

Run:

```bash
git add data_agent docs paper/ijgis_submission_20260605
git commit -m "Add ArcGIS commercial benchmark plan for SCCA"
```

Expected: commit succeeds.
