from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from data_agent.scca.robustness import write_cross_case_summary


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_ROOT = PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results"
DEFAULT_OUTPUT_DIR = RESULTS_ROOT / "scca_robustness_summary"
DEFAULT_MANIFEST_PATHS = (
    RESULTS_ROOT / "scca_snow8" / "robustness_manifest.json",
    RESULTS_ROOT / "scca_soho" / "robustness_manifest.json",
    RESULTS_ROOT / "scca_county_social_capital" / "robustness_manifest.json",
)


def _load_manifest(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_robustness_summary(
    manifest_paths: Iterable[str | Path] = DEFAULT_MANIFEST_PATHS,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, object]:
    manifests = [_load_manifest(Path(path)) for path in manifest_paths]
    return write_cross_case_summary(manifests, output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the cross-case SCCA robustness summary.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--manifest-path", action="append", dest="manifest_paths")
    args = parser.parse_args()
    paths = args.manifest_paths if args.manifest_paths else DEFAULT_MANIFEST_PATHS
    manifest = run_robustness_summary(paths, args.output_dir)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
