# Paper6 Spatial Causal Inference

This repository is the standalone reproduction package for Paper6:

**A three-angle framework for geospatial causal inference with statistical identification, LLM causal reasoning, and AlphaEarth/World-Model counterfactual simulation.**

The repository is organized for IJGIS-style peer review. It contains the IJGIS submission package, original manuscript sources, Paper6 code, tests, experiment scripts, generated outputs, selected raw Chongqing sample data, and model weights required by the world-model examples.

## Repository Map

- `paper/ijgis_submission_20260605/` - IJGIS-oriented submission package, including manuscript source, figures, internal review notes, checklist, and compiled PDF.
- `paper/source_docs/` - earlier Paper6 source drafts and Chinese/English document exports.
- `paper/figures/` - publication figure PDFs generated for the manuscript.
- `data_agent/` - Paper6 reproduction subset of the GIS Data Agent codebase.
- `data_agent/experiments/` - causal and world-model experiment runners plus generated outputs.
- `data_agent/uploads/anonymous/` - diagnostic files referenced by historical experiment JSON outputs.
- `data/raw/01数据样例/` - raw Chongqing DEM, CLCD, and building-footprint sample data used by Paper6 real-data experiments.
- `scripts/` - case-study, AlphaEarth feasibility, and manuscript-generation helper scripts.
- `demos/` - small causal and world-model demos.
- `docs/background/` - supporting technical notes for AlphaEarth and world-model design.
- `checksums/` - machine-readable SHA-256 file inventory.

## Quick Start

Use Python 3.11+ from the repository root.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest data_agent/test_causal_inference.py data_agent/test_causal_world_model.py data_agent/test_llm_causal.py data_agent/test_world_model.py
.\.venv\Scripts\python.exe -m data_agent.experiments.run_causal --synthetic-only
.\.venv\Scripts\python.exe -m data_agent.experiments.fig_causal
```

The real-data UHI and LULC/LST experiments can be run with:

```powershell
.\.venv\Scripts\python.exe -m data_agent.experiments.run_causal --uhi
.\.venv\Scripts\python.exe -m data_agent.experiments.run_causal --lulc
```

Those commands use local Chongqing sample data and will try Google Earth Engine for MODIS LST. If Earth Engine is not authenticated, the scripts fall back to synthetic LST for a runnable smoke reproduction; see `REPRODUCIBILITY.md` for details.

## Paper Entry Points

- Main IJGIS TeX: `paper/ijgis_submission_20260605/01_manuscript/01_manuscript_ijgis.tex`
- Compiled IJGIS PDF: `paper/ijgis_submission_20260605/06_build/01_manuscript_ijgis.pdf`
- Required experiment plan before formal submission: `paper/ijgis_submission_20260605/05_internal_review/ijgis_required_experiments.md`

## Review Note

This repository is intended as a private reviewer reproduction package. It deliberately includes selected raw geospatial sample files and model weights. Before making the repository public, confirm the redistribution permissions for all raw data under `data/raw/`.
