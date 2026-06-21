# Manifest

Repository name: `paper6-spatial-causal-inference`

Created from the author's local Paper6 workspace on 2026-06-07 for Paper6 review and reproduction.

## Included

- IJGIS submission package: `paper/ijgis_submission_20260605/`
- manuscript figures: `paper/figures/`
- Paper6 code subset: `data_agent/`
- Paper6 tests: `data_agent/test_causal_inference.py`, `data_agent/test_causal_world_model.py`, `data_agent/test_llm_causal.py`, `data_agent/test_world_model.py`
- experiment scripts and outputs: `data_agent/experiments/`
- historical diagnostic outputs referenced by JSON files: `data_agent/uploads/anonymous/`
- raw Chongqing sample data required by current real-data experiments: `data/raw/01数据样例/`
- case-study, AlphaEarth validation, and local AlphaEarth encoder helper scripts: `scripts/`
- supporting technical notes: `docs/background/`
- small demos: `demos/`
- model weights required by the included world-model code: `data_agent/weights/`

## Excluded

- `.env` files, cookies, credentials, tokens, and internal remote URLs
- unrelated NL2SQL/Paper1/Paper2/Paper5/Paper7/Paper9 work, including Paper9-specific `world_model_v2*` and `world_model_v21*` adapters
- large user-upload caches from the parent project
- Python caches, local test scratch directories, and LaTeX intermediate files
- Earth Engine raw AlphaEarth cache directory `data_agent/weights/raw_data/`

## Current Main Paper Files

- `paper/ijgis_submission_20260605/01_manuscript/01_manuscript_ijgis.tex`
- `paper/ijgis_submission_20260605/06_build/01_manuscript_ijgis.pdf`
- `paper/ijgis_submission_20260605/05_internal_review/ijgis_required_experiments.md`
