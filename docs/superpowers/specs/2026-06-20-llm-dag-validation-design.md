# LLM DAG Validation Design

Date: 2026-06-20

## Goal

Strengthen Paper 6 Angle B by adding a reproducible DAG validation benchmark
instead of relying on a single illustrative LLM-generated causal graph.

## Scope

Included:

- A reference DAG suite with at least 20 geographic causal prompts.
- Edge-level metrics against manually specified reference DAGs:
  - precision,
  - recall,
  - F1,
  - structural Hamming distance,
  - repeated-run Jaccard stability.
- A simple template baseline.
- A structured prompt proxy generator for offline reproducible validation.
- Optional live Gemini runner support for later use when API/network access and
  cost are explicitly acceptable.
- Output files required by the IJGIS internal review note:
  - `llm_dag_validation.csv`
  - `llm_dag_examples.md`

Excluded:

- Manuscript prose edits.
- Claims that the offline proxy results are live LLM performance.
- Any network-dependent live model run by default.

## Design

Create `data_agent/experiments/llm_dag_validation.py`.

The module should:

1. Define reference cases from:
   - the six synthetic causal scenarios,
   - the Chongqing UHI case,
   - representative geographic causal examples used in the paper narrative.
2. Store reference graphs as canonical node names and directed edges.
3. Normalize generated node/edge names with alias maps before scoring.
4. Run every selected generator for each case and repeat index.
5. Score each run independently and then compute repeated-run stability per
   case/generator group.
6. Write a CSV table and Markdown example report.

## Generators

Default offline generators:

- `structured_prompt_proxy`: a deterministic proxy for a domain-aware prompt
  that mostly follows the reference DAG but introduces controlled omissions and
  extra edges across repeats. This validates the evaluation workflow without
  making live LLM claims.
- `minimal_template_baseline`: a deliberately weak baseline that usually emits
  only a direct exposure-to-outcome edge.

Optional live generator:

- `live_gemini_flash`: calls Gemini at low temperature and parses the same JSON
  DAG shape used by `data_agent.llm_causal.construct_causal_dag`. This is not
  used by default because it depends on external API access and cost.

## Output Interpretation

The experiment should be conservative:

- Offline proxy rows show the evaluation harness and baseline comparison.
- Live Gemini rows, if later run, can be used as Angle B validation evidence.
- If only offline rows exist, the paper should say the validation harness is in
  place but not claim live LLM DAG accuracy.

## Acceptance Criteria

This task is complete when:

- focused tests pass,
- `llm_dag_validation.csv` and `llm_dag_examples.md` exist,
- the validation CSV contains at least 20 prompt IDs, two generator labels, and
  the required metrics,
- manifest/report text clearly labels whether the run is offline-only or
  includes live LLM calls.
