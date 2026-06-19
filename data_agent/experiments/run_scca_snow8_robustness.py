from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from data_agent.scca.context import build_context_features
from data_agent.scca.profiling import load_table
from data_agent.scca.robustness import (
    run_context_ablation,
    run_group_bootstrap,
    run_placebo_tests,
    summarize_erf_stability,
    write_robustness_outputs,
)
from data_agent.scca.specs import SCCAPaths, StudySpec


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results" / "scca_snow8"


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


def run_snow8_robustness(
    csv_path: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    n_replicates: int = 200,
) -> dict[str, object]:
    spec = StudySpec.snow8_default()
    paths = SCCAPaths(output_dir=Path(output_dir))
    paths.ensure()
    df = load_table(csv_path)
    features, _ = build_context_features(df, spec, paths)
    credibility = _read_json(paths.credibility_report, {"decision": "unknown", "reasons": []})
    ablation = run_context_ablation(features, spec, "snow8")
    placebo_tests = []
    if "perc_lam" in df.columns:
        features["perc_lam"] = pd.to_numeric(df["perc_lam"], errors="coerce")
        placebo_tests.append(
            {
                "test_name": "lambeth_supplier_share",
                "exposure": "perc_lam",
                "role": "competing_supplier",
                "expected_relation": "weaker_or_opposite_than_perc_sou",
            }
        )
    placebo = run_placebo_tests(features, spec, "snow8", placebo_tests)
    bootstrap_rows, bootstrap_summary = run_group_bootstrap(
        features,
        spec,
        "snow8",
        "district",
        n_replicates=n_replicates,
        random_state=0,
    )
    erf_path = paths.erf_curve
    erf_summary = summarize_erf_stability(pd.read_csv(erf_path), "snow8") if erf_path.exists() else {}
    reasons = credibility.get("reasons", [])
    main_limitation = str(reasons[0]) if isinstance(reasons, list) and reasons else "No original limitation recorded."
    return write_robustness_outputs(
        output_dir=paths.output_dir,
        case_name="snow8",
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
    parser = argparse.ArgumentParser(description="Run SCCA robustness checks for Snow8.")
    parser.add_argument("--csv-path", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--n-replicates", type=int, default=200)
    args = parser.parse_args()
    manifest = run_snow8_robustness(args.csv_path, args.output_dir, args.n_replicates)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
