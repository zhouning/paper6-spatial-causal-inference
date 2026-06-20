from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from data_agent.scca.context import build_context_features
from data_agent.scca.design import select_design
from data_agent.scca.diagnostics import audit_effects
from data_agent.scca.estimators import estimate_effects
from data_agent.scca.profiling import profile_table
from data_agent.scca.reporting import write_report
from data_agent.scca.specs import SCCAPaths, StudySpec


NUMERIC_COLUMNS = (
    "OBJECTID",
    "CountyCode",
    "FIPS",
    "AveAgeDeath",
    "SocialAssoc",
    "UnemployRate",
    "pHHinPoverty",
    "pNoHealthInsur",
    "MentalHealth",
    "pAdultSmoking",
    "pAdultObesity",
    "FastFood",
    "pInsufficientSleep",
    "pAlcohol",
    "pSuicideDeaths",
    "AirPollution",
    "Shape_Length",
    "Shape_Area",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results" / "scca_county_social_capital"
DEFAULT_SHEET_NAME = "CountyData"


def prepare_county_social_capital_table(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    for column in NUMERIC_COLUMNS:
        if column in prepared.columns:
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    for column in ("STATE_NAME", "County"):
        if column in prepared.columns:
            prepared[column] = prepared[column].map(str).astype(object)
    return prepared


def load_county_social_capital_workbook(
    workbook_path: str | Path,
    sheet_name: str = DEFAULT_SHEET_NAME,
) -> pd.DataFrame:
    return pd.read_excel(workbook_path, sheet_name=sheet_name)


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={PROJECT_ROOT.as_posix()}", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _current_git_commit() -> str:
    try:
        commit = _run_git("rev-parse", "HEAD")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return commit or "unknown"


def _git_status_path(status_line: str) -> str:
    path = status_line[3:].strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1].strip()
    return path.replace("\\", "/")


def _relative_git_path(path: Path) -> str | None:
    try:
        relative = path.resolve().relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return None
    return relative.as_posix().rstrip("/") + "/"


def _git_dirty(ignored_paths: Iterable[Path] = ()) -> bool | None:
    try:
        status = _run_git("status", "--short")
    except (OSError, subprocess.CalledProcessError):
        return None
    ignored_prefixes = tuple(
        prefix for path in ignored_paths if (prefix := _relative_git_path(path)) is not None
    )
    for line in status.splitlines():
        git_path = _git_status_path(line)
        if ignored_prefixes and any(git_path.startswith(prefix) for prefix in ignored_prefixes):
            continue
        return True
    return False


def run_county_social_capital_scca(
    workbook_path: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    sheet_name: str = DEFAULT_SHEET_NAME,
) -> dict[str, object]:
    spec = StudySpec.county_social_capital_default()
    paths = SCCAPaths(output_dir=Path(output_dir))
    paths.ensure()
    source_path = Path(workbook_path)
    raw = load_county_social_capital_workbook(source_path, sheet_name=sheet_name)
    df = prepare_county_social_capital_table(raw)
    profile_table(df, spec, paths)
    features, _ = build_context_features(df, spec, paths)
    select_design(features, spec, paths)
    estimate_effects(features, spec, paths)
    credibility = audit_effects(features, spec, paths)
    metadata = {
        "source_workbook": str(source_path),
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "sheet_name": sheet_name,
        "command": (
            "run_county_social_capital_scca("
            f"workbook_path={source_path}, output_dir={paths.output_dir}, sheet_name={sheet_name})"
        ),
        "code_commit": _current_git_commit(),
        "code_commit_role": "source_commit_used_to_generate_outputs",
        "git_dirty": _git_dirty(ignored_paths=(paths.output_dir,)),
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
    parser = argparse.ArgumentParser(description="Run SCCA on the county social-capital dataset.")
    parser.add_argument("--workbook-path", required=True, help="Path to CountyData_TableToExcel.xlsx")
    parser.add_argument("--sheet-name", default=DEFAULT_SHEET_NAME, help="Workbook sheet name")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for SCCA outputs")
    args = parser.parse_args()
    manifest = run_county_social_capital_scca(args.workbook_path, args.output_dir, args.sheet_name)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
