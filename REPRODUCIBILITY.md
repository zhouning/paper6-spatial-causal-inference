# Reproducibility Guide

This guide describes how to reproduce the Paper6 code, figures, and main experiment outputs from a clean checkout.

## 1. Environment

Recommended platform: Windows 10/11 or Linux with Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

For Linux/macOS, replace `.\.venv\Scripts\python.exe` with `./.venv/bin/python`.

## 2. Included Data and Weights

The public GitHub tree includes code, generated outputs, synthetic generators,
public/example county data, and model weights where redistribution is permitted.
It does not include the Chongqing raw geospatial inputs or building-level UHI
analysis sample.

Restricted Chongqing inputs are expected only in a local approved workspace:

- Chongqing DEM 2020
- Chongqing CLCD 2020
- Chongqing central building footprints with floor attributes, 2021
- `chongqing_uhi_analysis_sample.csv`, an analysis-ready building-level table

World-model weights are stored in:

- `data_agent/weights/latent_dynamics_v1.pt`
- `data_agent/weights/latent_dynamics_val.pt`
- `data_agent/weights/lulc_decoder_v1.pkl`
- `data_agent/weights/local_alphaearth_encoder.pth`
- `data_agent/weights/alphaearth_local_*.pt`

Runtime-generated AlphaEarth caches under `data_agent/weights/raw_data/` are intentionally not tracked.

## 3. Test Suite

Run the focused Paper6 tests:

```powershell
.\.venv\Scripts\python.exe -m pytest data_agent/test_causal_inference.py
.\.venv\Scripts\python.exe -m pytest data_agent/test_causal_world_model.py
.\.venv\Scripts\python.exe -m pytest data_agent/test_llm_causal.py
.\.venv\Scripts\python.exe -m pytest data_agent/test_world_model.py
```

The LLM causal tests use mocks for Gemini calls. The world-model tests mock remote Earth Engine-dependent calls where needed.

## 4. Synthetic Experiments

Run the six synthetic causal-validation scenarios:

```powershell
.\.venv\Scripts\python.exe -m data_agent.experiments.run_causal --synthetic-only
```

Expected output:

- `data_agent/experiments/output/synthetic_results.json`
- diagnostic files under `data_agent/uploads/anonymous/`

Note: the GCCM synthetic scenario is included to exercise the spatial-geometry pipeline. The compact grid example can show bidirectional convergence because rainfall and NDVI share a strong spatial gradient; use the dedicated tests and the review-required multi-seed benchmark for directional claims.

## 5. Real Chongqing Experiments

Run high-rise building to UHI:

```powershell
.\.venv\Scripts\python.exe -m data_agent.experiments.run_causal --uhi
```

The strengthened IJGIS-required Chongqing UHI ablation and robustness outputs
can be regenerated from a local, permission-controlled analysis sample without
re-querying Earth Engine:

```powershell
.\.venv\Scripts\python.exe -c "import pandas as pd; from data_agent.experiments.chongqing_uhi_analysis import run_chongqing_uhi_analysis; df = pd.read_csv(r'D:\path\to\local\chongqing_uhi_analysis_sample.csv'); run_chongqing_uhi_analysis(df, n_bootstrap=500, n_spatial_bootstrap=500)"
```

Expected outputs:

- `paper/ijgis_submission_20260605/07_results/chongqing_uhi_ablation.csv`
- `paper/ijgis_submission_20260605/07_results/chongqing_uhi_balance.csv`
- `paper/ijgis_submission_20260605/07_results/chongqing_uhi_matched_counts.csv`
- `paper/ijgis_submission_20260605/07_results/chongqing_spatial_bootstrap.csv`
- `paper/ijgis_submission_20260605/07_results/chongqing_placebo_thresholds.csv`
- `paper/ijgis_submission_20260605/07_results/chongqing_residual_spatial_diagnostics.csv`

Run built-up land to LST:

```powershell
.\.venv\Scripts\python.exe -m data_agent.experiments.run_causal --lulc
```

These experiments use local Chongqing building, DEM, and CLCD files that are not
tracked in GitHub. If Google Earth Engine is authenticated, MODIS LST is sampled
remotely. If GEE is unavailable, the current scripts generate synthetic LST
values so the pipeline remains executable as a smoke reproduction. For final
IJGIS submission, the GEE-authenticated real-data run should be reported.

## 6. Figure Generation

Regenerate manuscript figures:

```powershell
.\.venv\Scripts\python.exe -m data_agent.experiments.fig_causal
```

Expected outputs are PNG and PDF files under `data_agent/experiments/output/`.

## 7. Manuscript Build

The compiled PDF is already included:

`paper/ijgis_submission_20260605/06_build/01_manuscript_ijgis.pdf`

To rebuild the LaTeX manuscript from source:

```powershell
cd paper\ijgis_submission_20260605\01_manuscript
pdflatex -interaction=nonstopmode -output-directory=..\06_build 01_manuscript_ijgis.tex
```

The local build may require a TeX distribution with common packages such as `natbib`, `graphicx`, `amsmath`, `booktabs`, and `hyperref`.

## 8. Known Review-Critical Experiments

The current IJGIS readiness notes identify additional experiments that should be completed before formal submission:

- synthetic multi-seed benchmark
- Chongqing UHI ablation
- spatial robustness and sensitivity
- direct GeoFM/AlphaEarth ablation
- LLM DAG validation
- world-model holdout validation

See `paper/ijgis_submission_20260605/05_internal_review/ijgis_required_experiments.md`.
