from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from data_agent.experiments.run_scca_soho import prepare_soho_table
from data_agent.scca.context import build_context_features
from data_agent.scca.profiling import load_table
from data_agent.scca.robustness import (
    make_quantile_grid_groups,
    run_context_ablation,
    run_group_bootstrap,
    run_placebo_tests,
    summarize_erf_stability,
    write_robustness_outputs,
)
from data_agent.scca.specs import SCCAPaths, StudySpec


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results" / "scca_soho"


def _read_json(path: Path, default: dict[str, object]) -> dict[str, object]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _main_coef(output_dir: Path) -> float:
    path = output_dir / "effect_estimates.csv"
    if not path.exists():
        return float("nan")
    estimates = pd.read_csv(path)
    rows = estimates.loc[estimates["estimator"] == "baseline_adjusted_ols", "coef"]
    return float(rows.iloc[0]) if not rows.empty else float("nan")


def run_soho_robustness(
    csv_path: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    n_replicates: int = 200,
) -> dict[str, object]:
    spec = StudySpec.soho_default()
    paths = SCCAPaths(output_dir=Path(output_dir))
    paths.ensure()
    raw = load_table(csv_path)
    df = prepare_soho_table(raw)
    df["pestfield_proximity"] = -np.log1p(pd.to_numeric(df["dis_pestf"], errors="coerce"))
    df["sewer_proximity"] = -np.log1p(pd.to_numeric(df["dis_sewers"], errors="coerce"))
    features, _ = build_context_features(df, spec, paths)
    features["pestfield_proximity"] = df["pestfield_proximity"]
    features["sewer_proximity"] = df["sewer_proximity"]
    features["grid_block"] = make_quantile_grid_groups(features, "COORD_X", "COORD_Y", bins=4)
    credibility = _read_json(paths.credibility_report, {"decision": "unknown", "reasons": []})
    ablation = run_context_ablation(features, spec, "soho")
    placebo = run_placebo_tests(
        features,
        spec,
        "soho",
        [
            {
                "test_name": "pestfield_proximity",
                "exposure": "pestfield_proximity",
                "role": "competing_exposure",
                "expected_relation": "weaker_than_bspump_proximity",
            },
            {
                "test_name": "sewer_proximity",
                "exposure": "sewer_proximity",
                "role": "competing_exposure",
                "expected_relation": "weaker_than_bspump_proximity",
            },
        ],
    )
    bootstrap_rows, bootstrap_summary = run_group_bootstrap(
        features,
        spec,
        "soho",
        "grid_block",
        n_replicates=n_replicates,
        random_state=0,
    )
    erf_path = paths.erf_curve
    erf_summary = summarize_erf_stability(pd.read_csv(erf_path), "soho") if erf_path.exists() else {}
    reasons = credibility.get("reasons", [])
    main_limitation = str(reasons[0]) if isinstance(reasons, list) and reasons else "No original limitation recorded."
    return write_robustness_outputs(
        output_dir=paths.output_dir,
        case_name="soho",
        original_decision=str(credibility.get("decision", "unknown")),
        main_coef=_main_coef(paths.output_dir),
        main_limitation=main_limitation,
        ablation=ablation,
        placebo=placebo,
        bootstrap_rows=bootstrap_rows,
        bootstrap_summary=bootstrap_summary,
        erf_summary=erf_summary,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SCCA robustness checks for Soho.")
    parser.add_argument("--csv-path", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--n-replicates", type=int, default=200)
    args = parser.parse_args()
    manifest = run_soho_robustness(args.csv_path, args.output_dir, args.n_replicates)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
