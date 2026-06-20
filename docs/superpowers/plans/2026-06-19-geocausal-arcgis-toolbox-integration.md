# GeoCausal ArcGIS Toolbox Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a generic ArcGIS Pro toolbox wrapper for GeoCausal SCCA without hard-coding Paper 6 fields, while preserving a reusable core API for future QGIS and notebook integrations.

**Architecture:** Keep `geocausal` as the tool-agnostic execution core. Add a small adapter layer that translates generic user-supplied field names and options into GeoCausal YAML/config, then add an ArcGIS `.pyt` wrapper that exports ArcGIS inputs to CSV, invokes the shared adapter, and exposes output files/tables back to ArcGIS users.

**Tech Stack:** Python, PyYAML, pandas, statsmodels, ArcPy (toolbox layer only), pytest

---

### Task 1: Stabilize the generic GeoCausal adapter

**Files:**
- Create: `geocausal/adapters.py`
- Modify: `data_agent/test_geocausal_adapters.py`

- [ ] Adapter test exists for generic field names only
- [ ] Adapter writes YAML from `AnalysisRequest`
- [ ] Adapter runs `run_analysis()` without importing ArcPy

### Task 2: Preserve tool-agnostic target/trimming behavior

**Files:**
- Modify: `geocausal/config.py`
- Modify: `geocausal/io.py`
- Modify: `geocausal/pipeline.py`
- Modify: `data_agent/test_geocausal_config.py`
- Modify: `data_agent/test_geocausal_pipeline.py`

- [ ] Preprocessing config parses exposure trimming generically
- [ ] Target outcome config parses without case-specific names
- [ ] Pipeline writes target outputs with both adjusted and ERF-anchored methods
- [ ] GeoCausal tests stay green

### Task 3: Add ArcGIS toolbox wrapper

**Files:**
- Create: `arcgis_toolbox/GeoCausalSCCA.pyt`
- Create: `arcgis_toolbox/README.md`
- Create: `data_agent/test_arcgis_toolbox_structure.py`

- [ ] Python toolbox exposes generic parameters
- [ ] Toolbox imports repo root dynamically
- [ ] Toolbox exports input rows to CSV
- [ ] Toolbox calls `geocausal.adapters.run_scca_analysis`
- [ ] Toolbox returns output file paths without case-specific fields
- [ ] Static structure test confirms no hard-coded Paper 6 field names

### Task 4: Add cross-surface usage notes

**Files:**
- Modify: `README.md`
- Create: `docs/geocausal_integration_surfaces.md`

- [ ] Document notebook usage via `AnalysisRequest`
- [ ] Document ArcGIS toolbox usage
- [ ] Document future QGIS integration boundary

### Task 5: Verify in current and ArcGIS Python environments

**Files:**
- No code changes required unless verification fails

- [ ] Run `pytest data_agent\test_geocausal_config.py data_agent\test_geocausal_io.py data_agent\test_geocausal_pipeline.py data_agent\test_geocausal_adapters.py data_agent\test_arcgis_toolbox_structure.py`
- [ ] Run ArcGIS Pro clone import check against `D:\Users\zn198\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone3`
- [ ] Report any ArcPy-specific import or packaging gap explicitly
