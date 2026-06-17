from __future__ import annotations

import argparse
import json
from pathlib import Path

from data_agent.scca.context import build_context_features
from data_agent.scca.design import select_design
from data_agent.scca.diagnostics import audit_effects
from data_agent.scca.estimators import estimate_effects
from data_agent.scca.profiling import load_table, profile_table
from data_agent.scca.reporting import write_report
from data_agent.scca.specs import SCCAPaths, StudySpec


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results" / "scca_snow8"


def run_snow8_scca(csv_path: str | Path, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    """Run the SCCA snow8 workflow and return the output manifest."""

    spec = StudySpec.snow8_default()
    paths = SCCAPaths(output_dir=Path(output_dir))
    paths.ensure()
    df = load_table(csv_path)
    profile_table(df, spec, paths)
    features, _ = build_context_features(df, spec, paths)
    select_design(features, spec, paths)
    estimate_effects(features, spec, paths)
    credibility = audit_effects(features, spec, paths)
    write_report(spec, paths, credibility)
    return json.loads(paths.manifest.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SCCA on South London snow8 data.")
    parser.add_argument("--csv-path", required=True, help="Path to snow8/subdistricts.csv")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for SCCA outputs")
    args = parser.parse_args()
    manifest = run_snow8_scca(args.csv_path, args.output_dir)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
