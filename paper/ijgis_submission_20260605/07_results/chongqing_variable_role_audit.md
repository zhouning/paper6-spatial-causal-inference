# Chongqing Context Variable Role Audit

This table separates context variables by their assumed causal role and by the
observed Chongqing ablation result. It is intended to keep post-treatment
proxy risk explicit in the manuscript.

| Context group | Causal role | Risk | Variant | ATT (C) | Max post SMD | Balance pass |
|---|---|---|---|---:|---:|---|
| Coordinates | spatial proxy confounder | low | coordinates_only | 0.267 | 0.080 | True |
| Building geometry | proxy confounder or pre-treatment morphology | medium | geometry | 0.252 | 0.125 | False |
| Terrain | pre-treatment confounder | low | terrain | 0.303 | 0.104 | False |
| Pre-treatment set | confounder-only adjustment set | low | pre_treatment | 0.303 | 0.104 | False |
| Sentinel indices | ambiguous proxy or mediator | high | sentinel_indices | 0.157 | 0.083 | True |
| Sentinel bands | ambiguous proxy or mediator | medium | sentinel_bands | 0.121 | 0.051 | True |
| Full RS context | over-adjusted mixed set (possible mediators) | medium | full_rs_context | 0.244 | 0.061 | True |
