from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from data_agent.scca.context import build_context_features
from data_agent.scca.design import select_design
from data_agent.scca.diagnostics import audit_effects
from data_agent.scca.estimators import estimate_effects
from data_agent.scca.profiling import load_table, profile_table
from data_agent.scca.reporting import write_report
from data_agent.scca.specs import SCCAPaths, StudySpec


NUMERIC_COLUMNS = (
    "deaths",
    "death_dum",
    "dis_bspump",
    "dis_pestf",
    "dis_sewers",
    "pestfield",
    "COORD_X",
    "COORD_Y",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results" / "scca_soho"


def prepare_soho_table(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    for column in NUMERIC_COLUMNS:
        if column in prepared.columns:
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    prepared["bspump_proximity"] = -np.log1p(prepared["dis_bspump"])
    return prepared


def _current_git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def _git_dirty() -> bool | None:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return bool(result.stdout.strip())


def run_soho_scca(csv_path: str | Path, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    """Run the SCCA Soho Broad Street pump mechanism workflow."""

    spec = StudySpec.soho_default()
    paths = SCCAPaths(output_dir=Path(output_dir))
    paths.ensure()
    source_path = Path(csv_path)
    raw = load_table(source_path)
    df = prepare_soho_table(raw)
    profile_table(df, spec, paths)
    features, _ = build_context_features(df, spec, paths)
    select_design(features, spec, paths)
    estimate_effects(features, spec, paths)
    credibility = audit_effects(features, spec, paths)
    metadata = {
        "source_csv": str(source_path),
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "command": f"run_soho_scca(csv_path={source_path}, output_dir={paths.output_dir})",
        "code_commit": _current_git_commit(),
        "code_commit_role": "source_commit_used_to_generate_outputs",
        "git_dirty": _git_dirty(),
        "artifact_commit_note": (
            "The final artifact commit is represented by repository history and is not "
            "self-recorded in this manifest because doing so would be self-referential."
        ),
        "input_rows": int(raw.shape[0]),
        "input_columns": int(raw.shape[1]),
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    write_report(spec, paths, credibility, metadata=metadata)
    return json.loads(paths.manifest.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SCCA on Soho Broad Street pump data.")
    parser.add_argument("--csv-path", required=True, help="Path to snow1/deaths_nd_by_house.csv")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for SCCA outputs")
    args = parser.parse_args()
    manifest = run_soho_scca(args.csv_path, args.output_dir)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
