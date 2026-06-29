from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .arcgis_causal import ArcGISCausalInferenceRequest, run_arcgis_causal_inference
from .arcgis_comparison import build_arcgis_geocausal_comparison
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

    arcgis_parser = subparsers.add_parser(
        "arcgis-causal",
        help="run ArcGIS Pro's built-in Causal Inference Analysis tool via ArcPy",
    )
    arcgis_parser.add_argument("--input-features", required=True, help="ArcGIS table/features or CSV input")
    arcgis_parser.add_argument("--output-workspace", required=True, help="output file geodatabase path")
    arcgis_parser.add_argument("--outcome-field", required=True)
    arcgis_parser.add_argument("--exposure-field", required=True)
    arcgis_parser.add_argument(
        "--confounders",
        required=True,
        help="comma-separated fields; append :CATEGORICAL when needed",
    )
    arcgis_parser.add_argument("--output-stem", default="arcgis_causal")
    arcgis_parser.add_argument("--ps-method", default="REGRESSION", choices=["REGRESSION", "GRADIENT_BOOSTING"])
    arcgis_parser.add_argument("--balancing-method", default="MATCHING", choices=["MATCHING", "WEIGHTING"])
    arcgis_parser.add_argument("--enable-erf-popups", default="NO_POPUP", choices=["NO_POPUP", "CREATE_POPUP"])
    arcgis_parser.add_argument("--target-outcomes", default="", help="comma-separated target outcome values")
    arcgis_parser.add_argument("--target-exposures", default="", help="comma-separated target exposure values")
    arcgis_parser.add_argument("--lower-exp-trim", type=float, default=0.01)
    arcgis_parser.add_argument("--upper-exp-trim", type=float, default=0.99)
    arcgis_parser.add_argument("--lower-ps-trim", type=float, default=0.0)
    arcgis_parser.add_argument("--upper-ps-trim", type=float, default=1.0)
    arcgis_parser.add_argument("--num-bins", type=int)
    arcgis_parser.add_argument("--scale", type=float)
    arcgis_parser.add_argument("--balance-type", default="MEAN", choices=["MEAN", "MEDIAN", "MAXIMUM"])
    arcgis_parser.add_argument("--balance-threshold", type=float, default=0.1)
    arcgis_parser.add_argument("--bw-method", default="PLUG_IN", choices=["PLUG_IN", "CV", "MANUAL"])
    arcgis_parser.add_argument("--bandwidth", type=float)
    arcgis_parser.add_argument("--create-bootstrap-ci", default="NO_CI", choices=["NO_CI", "CREATE_CI"])
    arcgis_parser.add_argument("--output-csv-dir", help="optional directory for CSV exports of ArcGIS outputs")
    arcgis_parser.add_argument("--manifest", help="optional JSON manifest path")

    compare_parser = subparsers.add_parser(
        "arcgis-compare",
        help="compare ArcGIS built-in Causal Inference outputs with a GeoCausal Open GIS package",
    )
    compare_parser.add_argument("--arcgis-manifest", required=True)
    compare_parser.add_argument("--open-gis-dir", required=True)
    compare_parser.add_argument("--output-dir", required=True)

    return parser


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _parse_formats(value: str) -> tuple[str, ...]:
    return tuple(
        item.strip().lower().lstrip(".")
        for item in value.split(",")
        if item.strip()
    )


def _parse_comma_values(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _parse_comma_floats(value: str) -> tuple[float, ...]:
    return tuple(float(item.strip()) for item in value.split(",") if item.strip())


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
        elif args.command == "arcgis-causal":
            _print_json(
                run_arcgis_causal_inference(
                    ArcGISCausalInferenceRequest(
                        in_features=args.input_features,
                        outcome_field=args.outcome_field,
                        exposure_field=args.exposure_field,
                        confounders=_parse_comma_values(args.confounders),
                        output_workspace=args.output_workspace,
                        output_stem=args.output_stem,
                        ps_method=args.ps_method,
                        balancing_method=args.balancing_method,
                        enable_erf_popups=args.enable_erf_popups,
                        target_outcomes=_parse_comma_floats(args.target_outcomes),
                        target_exposures=_parse_comma_floats(args.target_exposures),
                        lower_exp_trim=args.lower_exp_trim,
                        upper_exp_trim=args.upper_exp_trim,
                        lower_ps_trim=args.lower_ps_trim,
                        upper_ps_trim=args.upper_ps_trim,
                        num_bins=args.num_bins,
                        scale=args.scale,
                        balance_type=args.balance_type,
                        balance_threshold=args.balance_threshold,
                        bw_method=args.bw_method,
                        bandwidth=args.bandwidth,
                        create_bootstrap_ci=args.create_bootstrap_ci,
                        output_csv_dir=args.output_csv_dir,
                    ),
                    manifest_path=Path(args.manifest) if args.manifest else None,
                )
            )
        elif args.command == "arcgis-compare":
            _print_json(
                build_arcgis_geocausal_comparison(
                    arcgis_manifest_path=Path(args.arcgis_manifest),
                    open_gis_dir=Path(args.open_gis_dir),
                    output_dir=Path(args.output_dir),
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
