from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from geocausal.adapters import AnalysisRequest, build_analysis_joined_table, run_scca_analysis
from geocausal.spatial_outputs import (
    build_spatial_analysis_outputs,
    prepare_county_analysis_table_from_shapefile,
)


OUTPUT_DIR = (
    REPO_ROOT
    / "paper"
    / "ijgis_submission_20260605"
    / "07_results"
    / "examples"
    / "county_social_capital_notebook_demo"
)
CASE_NAME = "county_social_capital_notebook_demo"


def run_demo(output_dir: Path = OUTPUT_DIR) -> dict[str, object]:
    county_path = REPO_ROOT / "data" / "CountyData.shp"
    states_path = REPO_ROOT / "data" / "States.shp"
    output_dir.mkdir(parents=True, exist_ok=True)
    analysis_input_csv = output_dir / "county_analysis_input.csv"
    prepare_county_analysis_table_from_shapefile(
        county_path=county_path,
        output_csv=analysis_input_csv,
    )

    request = AnalysisRequest(
        case_name=CASE_NAME,
        input_path=analysis_input_csv,
        output_dir=output_dir,
        unit_id="FIPS",
        exposure="SocialAssoc",
        outcome="AveAgeDeath",
        confounders=(
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
        ),
        context_columns=("Shape_Length", "Shape_Area"),
        coordinate_columns=("_gc_x", "_gc_y"),
        bootstrap_group="STATE_NAME",
        lower_exposure_quantile=0.01,
        upper_exposure_quantile=0.99,
        target_outcomes=(70.0,),
        bootstrap_replicates=50,
    )
    manifest = run_scca_analysis(request)

    target_csv = output_dir / str(manifest["files"]["target_exposures"])
    analysis_joined_csv = output_dir / "analysis_joined.csv"
    build_analysis_joined_table(
        input_csv=analysis_input_csv,
        target_exposures_csv=target_csv,
        output_csv=analysis_joined_csv,
        unit_id_field="FIPS",
    )

    spatial_manifest = build_spatial_analysis_outputs(
        boundary_path=county_path,
        analysis_joined_csv=analysis_joined_csv,
        analysis_dir=output_dir,
        output_dir=output_dir / "spatial_outputs",
        states_path=states_path,
        output_stem="county_social_capital_analysis",
    )
    result_summary_path = output_dir / str(manifest["files"]["result_summary_markdown"])
    notebook_summary_path = output_dir / "notebook_result_summary.md"
    notebook_summary_path.write_text(result_summary_path.read_text(encoding="utf-8"), encoding="utf-8")

    summary = {
        "analysis_manifest": manifest,
        "result_summary": manifest.get("result_summary", {}),
        "narrative_summary_markdown": str(notebook_summary_path),
        "analysis_joined_csv": str(analysis_joined_csv),
        "analysis_input_csv": str(analysis_input_csv),
        "analysis_joined_rows": int(len(pd.read_csv(analysis_joined_csv, dtype={"FIPS": "string"}))),
        "spatial_manifest": spatial_manifest,
    }
    summary_path = output_dir / "notebook_demo_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main() -> None:
    print(json.dumps(run_demo(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
