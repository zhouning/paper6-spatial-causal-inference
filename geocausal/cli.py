from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .config import load_config
from .errors import GeoCausalError
from .pipeline import diagnose_config, rebuild_report, run_analysis
from .spatial_outputs import build_spatial_analysis_outputs


SCCA_TEMPLATE = """case_name: example_case
input:
  path: data.csv
  x: x
  y: y
variables:
  unit_id: unit_id
  exposure: exposure
  outcome: outcome
  baseline_outcome: baseline_outcome
  confounders:
    - confounder_1
context:
  columns:
    - context_1
robustness:
  placebo_exposures:
    - name: placebo_check
      column: placebo_exposure
      role: negative_control
      expected_relation: weaker_than_main
  bootstrap:
    group_column: group
    n_replicates: 200
output:
  directory: results/example_case
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="geocausal")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="write an analysis template")
    init_parser.add_argument("--template", choices=["scca"], default="scca")
    init_parser.add_argument("--output", default="analysis.yaml")

    diagnose_parser = subparsers.add_parser("diagnose", help="diagnose an analysis config")
    diagnose_parser.add_argument("config")

    run_parser = subparsers.add_parser("run", help="run an analysis config")
    run_parser.add_argument("config")

    report_parser = subparsers.add_parser("report", help="rebuild a markdown report")
    report_parser.add_argument("output_dir")

    spatial_parser = subparsers.add_parser(
        "spatial-package",
        help="build open spatial GIS outputs from a GeoCausal joined analysis table",
    )
    spatial_parser.add_argument(
        "--boundary",
        required=True,
        help="boundary layer path, e.g. a Shapefile or GeoPackage",
    )
    spatial_parser.add_argument(
        "--analysis-joined",
        required=True,
        help="analysis_joined.csv from the Open GIS package",
    )
    spatial_parser.add_argument(
        "--output-dir",
        required=True,
        help="directory for GeoPackage/GeoJSON/QGIS/HTML outputs",
    )
    spatial_parser.add_argument(
        "--analysis-dir",
        help="GeoCausal run output directory; inferred from Open GIS package path when omitted",
    )
    spatial_parser.add_argument("--boundary-key", default="FIPS", help="join field in the boundary layer")
    spatial_parser.add_argument("--analysis-key", default="gc_unit_id", help="join field in analysis_joined.csv")
    spatial_parser.add_argument(
        "--output-stem",
        default="geocausal_spatial_analysis",
        help="base filename for spatial outputs",
    )
    spatial_parser.add_argument("--formats", default="gpkg,geojson,shp", help="comma-separated spatial formats")
    spatial_parser.add_argument("--states", help="optional state/outline layer for static maps")
    spatial_parser.add_argument(
        "--map-field",
        default="gc_target_70_exposure_change",
        help="numeric field to map and style",
    )

    return parser


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _parse_formats(value: str) -> tuple[str, ...]:
    return tuple(
        item.strip().lower().lstrip(".")
        for item in value.split(",")
        if item.strip()
    )


def _infer_analysis_dir(analysis_joined_csv: Path) -> Path:
    parent = analysis_joined_csv.parent
    if parent.name == "open_gis_analysis_package":
        return parent.parent
    return parent


def _write_template(output: str) -> dict[str, str]:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(SCCA_TEMPLATE, encoding="utf-8")
    return {"template": "scca", "path": str(output_path)}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            _print_json(_write_template(args.output))
        elif args.command == "diagnose":
            _print_json(diagnose_config(load_config(args.config)))
        elif args.command == "run":
            _print_json(run_analysis(load_config(args.config)))
        elif args.command == "report":
            _print_json(rebuild_report(args.output_dir))
        elif args.command == "spatial-package":
            analysis_joined_csv = Path(args.analysis_joined)
            formats = _parse_formats(args.formats)
            if not formats:
                parser.error("--formats must contain at least one format")
            _print_json(
                build_spatial_analysis_outputs(
                    boundary_path=Path(args.boundary),
                    analysis_joined_csv=analysis_joined_csv,
                    output_dir=Path(args.output_dir),
                    analysis_dir=Path(args.analysis_dir)
                    if args.analysis_dir
                    else _infer_analysis_dir(analysis_joined_csv),
                    boundary_key=args.boundary_key,
                    analysis_key=args.analysis_key,
                    output_stem=args.output_stem,
                    formats=formats,
                    states_path=Path(args.states) if args.states else None,
                    map_field=args.map_field,
                )
            )
        else:
            parser.error(f"unknown command: {args.command}")
        return 0
    except GeoCausalError as exc:
        print(f"GeoCausal error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
