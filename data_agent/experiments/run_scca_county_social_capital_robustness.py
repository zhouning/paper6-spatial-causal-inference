from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from data_agent.experiments.run_scca_county_social_capital import (
    DEFAULT_SHEET_NAME,
    load_county_social_capital_workbook,
    prepare_county_social_capital_table,
)
from data_agent.scca.context import build_context_features
from data_agent.scca.robustness import (
    run_context_ablation,
    run_group_bootstrap,
    run_placebo_tests,
    summarize_erf_stability,
    write_robustness_outputs,
)
from data_agent.scca.specs import SCCAPaths, StudySpec


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results" / "scca_county_social_capital"


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


def run_county_social_capital_robustness(
    workbook_path: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    sheet_name: str = DEFAULT_SHEET_NAME,
    n_replicates: int = 200,
) -> dict[str, object]:
    spec = StudySpec.county_social_capital_default()
    paths = SCCAPaths(output_dir=Path(output_dir))
    paths.ensure()
    raw = load_county_social_capital_workbook(workbook_path, sheet_name=sheet_name)
    df = prepare_county_social_capital_table(raw)
    features, _ = build_context_features(df, spec, paths)
    credibility = _read_json(paths.credibility_report, {"decision": "unknown", "reasons": []})
    ablation = run_context_ablation(features, spec, "county_social_capital")
    placebo = run_placebo_tests(
        features,
        spec,
        "county_social_capital",
        [
            {
                "test_name": "shape_length",
                "exposure": "Shape_Length",
                "role": "shape_placebo",
                "expected_relation": "weaker_than_social_assoc",
            },
            {
                "test_name": "shape_area",
                "exposure": "Shape_Area",
                "role": "shape_placebo",
                "expected_relation": "weaker_than_social_assoc",
            },
        ],
    )
    bootstrap_rows, bootstrap_summary = run_group_bootstrap(
        features,
        spec,
        "county_social_capital",
        "STATE_NAME",
        n_replicates=n_replicates,
        random_state=0,
    )
    erf_path = paths.erf_curve
    erf_summary = summarize_erf_stability(pd.read_csv(erf_path), "county_social_capital") if erf_path.exists() else {}
    reasons = credibility.get("reasons", [])
    main_limitation = str(reasons[0]) if isinstance(reasons, list) and reasons else "No original limitation recorded."
    return write_robustness_outputs(
        output_dir=paths.output_dir,
        case_name="county_social_capital",
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
    parser = argparse.ArgumentParser(description="Run SCCA robustness checks for county social capital.")
    parser.add_argument("--workbook-path", required=True)
    parser.add_argument("--sheet-name", default=DEFAULT_SHEET_NAME)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--n-replicates", type=int, default=200)
    args = parser.parse_args()
    manifest = run_county_social_capital_robustness(
        args.workbook_path,
        args.output_dir,
        args.sheet_name,
        args.n_replicates,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
