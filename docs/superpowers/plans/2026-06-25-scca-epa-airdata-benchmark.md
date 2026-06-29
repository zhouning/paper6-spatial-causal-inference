# SCCA EPA AirData Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a public EPA nonattainment x AirData annual benchmark for SCCA, including semi-synthetic known-effect validation and manuscript integration.

**Architecture:** Add one focused experiment module that prepares EPA county-year data, generates a GeoCausal config, runs the existing SCCA pipeline, and writes compact benchmark summaries. Extend evidence synthesis with one EPA row and update the IJGIS manuscript only after result artifacts exist.

**Tech Stack:** Python, pandas, geopandas when county geometries are available, existing `geocausal.pipeline`, pytest, LaTeX.

---

## File Structure

- Create `data_agent/experiments/epa_airdata_benchmark.py`: data parsing, panel preparation, config generation, SCCA run orchestration, semi-synthetic scenario generation, CLI.
- Create `data_agent/test_epa_airdata_benchmark.py`: unit tests for parser and panel behavior using tiny fixtures.
- Modify `data_agent/experiments/scca_evidence_synthesis.py`: add an optional EPA benchmark evidence row.
- Modify `data_agent/test_scca_evidence_synthesis.py`: assert EPA row inclusion when fixture artifacts exist.
- Create `examples/epa_nonattainment_airdata_example.yaml`: generated or static example config for reruns.
- Create `paper/ijgis_submission_20260605/07_results/epa_nonattainment_airdata/`: compact processed outputs and SCCA results.
- Modify `paper/ijgis_submission_20260605/01_manuscript/01_manuscript_ijgis.tex`: add EPA benchmark framing and results.

### Task 1: EPA Parser Tests

**Files:**
- Create: `data_agent/test_epa_airdata_benchmark.py`
- Create later: `data_agent/experiments/epa_airdata_benchmark.py`

- [ ] **Step 1: Write failing tests for AirData aggregation**

```python
def test_aggregate_airdata_monitor_rows_to_county_year():
    from data_agent.experiments.epa_airdata_benchmark import aggregate_airdata_county_year

    raw = pd.DataFrame(
        {
            "state_code": ["01", "01", "01"],
            "county_code": ["001", "001", "003"],
            "parameter_code": [88101, 88101, 88101],
            "year": [2020, 2020, 2020],
            "arithmetic_mean": [8.0, 10.0, 7.0],
            "observation_count": [100, 300, 50],
        }
    )

    result = aggregate_airdata_county_year(raw, pollutant_code=88101)

    row = result.loc[result["county_fips"] == "01001"].iloc[0]
    assert row["annual_mean"] == pytest.approx(9.5)
    assert row["monitor_count"] == 2
    assert set(result["county_fips"]) == {"01001", "01003"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest data_agent/test_epa_airdata_benchmark.py::test_aggregate_airdata_monitor_rows_to_county_year -v`

Expected: FAIL because `epa_airdata_benchmark` does not exist.

- [ ] **Step 3: Implement minimal aggregation**

Create `aggregate_airdata_county_year(raw, pollutant_code)` in the experiment module. Normalize column names to lower snake case, construct five-digit FIPS, filter pollutant code, compute observation-count weighted annual means, and return `county_fips`, `year`, `pollutant_code`, `annual_mean`, `monitor_count`, `observation_count`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest data_agent/test_epa_airdata_benchmark.py::test_aggregate_airdata_monitor_rows_to_county_year -v`

Expected: PASS.

### Task 2: Nonattainment and Neighbor Panel Tests

**Files:**
- Modify: `data_agent/test_epa_airdata_benchmark.py`
- Modify: `data_agent/experiments/epa_airdata_benchmark.py`

- [ ] **Step 1: Write failing test for nonattainment expansion**

```python
def test_expand_nonattainment_periods_to_county_year():
    from data_agent.experiments.epa_airdata_benchmark import expand_nonattainment_periods

    periods = pd.DataFrame(
        {
            "county_fips": ["01001", "01003"],
            "start_year": [2020, 2021],
            "end_year": [2021, pd.NA],
        }
    )

    result = expand_nonattainment_periods(periods, years=[2020, 2021, 2022])

    status = {
        (row.county_fips, row.year): row.nonattainment
        for row in result.itertuples(index=False)
    }
    assert status[("01001", 2020)] == 1
    assert status[("01001", 2022)] == 0
    assert status[("01003", 2022)] == 1
```

- [ ] **Step 2: Write failing test for neighbor exposure**

```python
def test_add_neighbor_exposure_uses_county_adjacency():
    from data_agent.experiments.epa_airdata_benchmark import add_neighbor_exposure

    panel = pd.DataFrame(
        {
            "county_fips": ["01001", "01003", "01005", "01001", "01003", "01005"],
            "year": [2020, 2020, 2020, 2021, 2021, 2021],
            "nonattainment_lag1": [1, 0, 1, 0, 1, 0],
        }
    )
    adjacency = {"01001": ["01003", "01005"], "01003": ["01001"], "01005": ["01001"]}

    result = add_neighbor_exposure(panel, adjacency, exposure_col="nonattainment_lag1")

    row = result[(result["county_fips"] == "01001") & (result["year"] == 2020)].iloc[0]
    assert row["neighbor_nonattainment_lag1"] == pytest.approx(0.5)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest data_agent/test_epa_airdata_benchmark.py::test_expand_nonattainment_periods_to_county_year data_agent/test_epa_airdata_benchmark.py::test_add_neighbor_exposure_uses_county_adjacency -v`

Expected: FAIL because functions are missing.

- [ ] **Step 4: Implement period expansion and neighbor exposure**

Add `expand_nonattainment_periods(periods, years)` and `add_neighbor_exposure(panel, adjacency, exposure_col)` with deterministic handling of open-ended `end_year` values.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest data_agent/test_epa_airdata_benchmark.py -v`

Expected: PASS for parser and panel tests.

### Task 3: Panel Builder and Config Generation

**Files:**
- Modify: `data_agent/test_epa_airdata_benchmark.py`
- Modify: `data_agent/experiments/epa_airdata_benchmark.py`
- Create: `examples/epa_nonattainment_airdata_example.yaml`

- [ ] **Step 1: Write failing test for panel preparation**

```python
def test_prepare_epa_panel_adds_lagged_outcome_and_exposure():
    from data_agent.experiments.epa_airdata_benchmark import prepare_epa_panel

    air = pd.DataFrame(
        {
            "county_fips": ["01001", "01001", "01003", "01003"],
            "year": [2020, 2021, 2020, 2021],
            "pollutant_code": [88101, 88101, 88101, 88101],
            "annual_mean": [9.0, 8.0, 7.0, 7.5],
            "monitor_count": [1, 1, 1, 1],
            "observation_count": [100, 100, 100, 100],
        }
    )
    nonattainment = pd.DataFrame(
        {
            "county_fips": ["01001", "01001", "01003", "01003"],
            "year": [2020, 2021, 2020, 2021],
            "nonattainment": [1, 1, 0, 1],
        }
    )
    centroids = pd.DataFrame({"county_fips": ["01001", "01003"], "x": [-86.6, -86.7], "y": [32.5, 31.9]})

    result = prepare_epa_panel(air, nonattainment, centroids, adjacency={"01001": ["01003"], "01003": ["01001"]})

    row = result[(result["county_fips"] == "01001") & (result["year"] == 2021)].iloc[0]
    assert row["baseline_annual_mean"] == pytest.approx(9.0)
    assert row["nonattainment_lag1"] == 1
    assert row["neighbor_nonattainment_lag1"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest data_agent/test_epa_airdata_benchmark.py::test_prepare_epa_panel_adds_lagged_outcome_and_exposure -v`

Expected: FAIL because `prepare_epa_panel` is missing.

- [ ] **Step 3: Implement panel preparation and config writer**

Add `prepare_epa_panel(...)` and `write_geocausal_config(panel_path, output_dir, config_path)`. The YAML must set `unit_id: county_year_id`, `exposure: nonattainment_lag1`, `outcome: annual_mean`, `baseline_outcome: baseline_annual_mean`, confounders `baseline_annual_mean`, `monitor_count`, `year_index`, and context columns `x`, `y`, `neighbor_nonattainment_lag1`.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest data_agent/test_epa_airdata_benchmark.py -v`

Expected: PASS.

### Task 4: Semi-Synthetic Validation

**Files:**
- Modify: `data_agent/test_epa_airdata_benchmark.py`
- Modify: `data_agent/experiments/epa_airdata_benchmark.py`

- [ ] **Step 1: Write failing test for known-effect scenarios**

```python
def test_make_semisynthetic_scenarios_records_true_effects():
    from data_agent.experiments.epa_airdata_benchmark import make_semisynthetic_scenarios

    panel = pd.DataFrame(
        {
            "county_year_id": ["a_2021", "b_2021", "c_2021", "d_2021"],
            "county_fips": ["a", "b", "c", "d"],
            "year": [2021, 2021, 2021, 2021],
            "annual_mean": [8.0, 7.0, 9.0, 6.0],
            "baseline_annual_mean": [8.5, 7.2, 8.8, 6.1],
            "nonattainment_lag1": [1, 0, 1, 0],
            "neighbor_nonattainment_lag1": [0.0, 0.5, 0.0, 0.5],
            "x": [0.0, 1.0, 0.0, 1.0],
            "y": [0.0, 0.0, 1.0, 1.0],
            "monitor_count": [1, 1, 1, 1],
            "year_index": [0, 0, 0, 0],
        }
    )

    scenarios = make_semisynthetic_scenarios(panel, true_effect=-1.25)

    assert {"stable_known_effect", "spatial_confounding", "spillover"} <= set(scenarios)
    stable = scenarios["stable_known_effect"]
    assert stable.metadata["true_effect"] == pytest.approx(-1.25)
    assert "synthetic_outcome" in stable.frame.columns
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest data_agent/test_epa_airdata_benchmark.py::test_make_semisynthetic_scenarios_records_true_effects -v`

Expected: FAIL because `make_semisynthetic_scenarios` is missing.

- [ ] **Step 3: Implement deterministic semi-synthetic scenarios**

Use fixed formulas, not random noise by default. Stable outcome equals baseline plus true effect times exposure plus mild year/context terms. Confounded scenario adds spatial latent risk not included in config. Spillover scenario adds neighbor exposure effect.

- [ ] **Step 4: Run test to verify pass**

Run: `python -m pytest data_agent/test_epa_airdata_benchmark.py -v`

Expected: PASS.

### Task 5: Evidence Synthesis EPA Row

**Files:**
- Modify: `data_agent/experiments/scca_evidence_synthesis.py`
- Modify: `data_agent/test_scca_evidence_synthesis.py`

- [ ] **Step 1: Write failing evidence synthesis test**

Add a fixture `epa_nonattainment_airdata/benchmark_summary.json` under `tmp_path` with real and semi-synthetic metrics, then assert `build_scca_evidence_table(tmp_path)` includes `epa_nonattainment_airdata`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest data_agent/test_scca_evidence_synthesis.py::test_scca_evidence_synthesis_includes_epa_airdata_when_available -v`

Expected: FAIL because EPA row is not parsed.

- [ ] **Step 3: Implement `_epa_airdata_row`**

Read `epa_nonattainment_airdata/benchmark_summary.json`, extract real-data effect, evidence grade, semi-synthetic scenario count, median absolute error, and downgrade rules. Return a bounded row when any scenario triggers spatial caution or when real-data grade is bounded.

- [ ] **Step 4: Run synthesis tests**

Run: `python -m pytest data_agent/test_scca_evidence_synthesis.py -v`

Expected: PASS.

### Task 6: Data Acquisition and Full Experiment

**Files:**
- Modify: `data_agent/experiments/epa_airdata_benchmark.py`
- Generated: `paper/ijgis_submission_20260605/07_results/epa_nonattainment_airdata/*`

- [ ] **Step 1: Add CLI for local and network modes**

CLI arguments: `--raw-dir`, `--output-dir`, `--years`, `--download`, `--pollutant-code`, `--skip-scca`.

- [ ] **Step 2: Run unit tests**

Run: `python -m pytest data_agent/test_epa_airdata_benchmark.py data_agent/test_scca_evidence_synthesis.py -v`

Expected: PASS.

- [ ] **Step 3: Download public inputs when approved**

Run: `python -m data_agent.experiments.epa_airdata_benchmark --download --years 1999-2024 --pollutant-code 88101`

Expected: raw files in local ignored raw directory, processed panel CSV, SCCA outputs, benchmark summary.

- [ ] **Step 4: Run evidence synthesis**

Run: `python -m data_agent.experiments.scca_evidence_synthesis`

Expected: `scca_evidence_synthesis.csv` includes the EPA row.

### Task 7: Manuscript Update and Verification

**Files:**
- Modify: `paper/ijgis_submission_20260605/01_manuscript/01_manuscript_ijgis.tex`
- Generated: `paper/ijgis_submission_20260605/01_manuscript/01_manuscript_ijgis.pdf`

- [ ] **Step 1: Update abstract and contribution language**

Mention synthetic benchmarks, Chongqing, EPA public policy benchmark, and county GIS reproducibility boundary check.

- [ ] **Step 2: Update experiments section**

Add a concise EPA subsection with dataset, panel size, real-data evidence, semi-synthetic known-effect validation, and limitations.

- [ ] **Step 3: Update evidence synthesis text**

Use generated result values from `benchmark_summary.json` and `scca_evidence_synthesis.csv`.

- [ ] **Step 4: Compile LaTeX**

Run from manuscript directory: `pdflatex 01_manuscript_ijgis.tex`, `bibtex 01_manuscript_ijgis`, `pdflatex 01_manuscript_ijgis.tex`, `pdflatex 01_manuscript_ijgis.tex`.

Expected: PDF generated without fatal errors.

- [ ] **Step 5: Final verification**

Run: `python -m pytest data_agent/test_epa_airdata_benchmark.py data_agent/test_scca_evidence_synthesis.py data_agent/test_geocausal_pipeline.py -v`

Expected: PASS or documented pre-existing skips only.
