from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from geocausal.adapters import (
    AnalysisRequest,
    build_analysis_joined_table,
    run_scca_analysis,
)


@dataclass(frozen=True)
class QGISRunRequest:
    case_name: str
    input_csv: Path
    output_dir: Path
    exposure_field: str
    outcome_field: str
    unit_id_field: str | None = None
    baseline_outcome_field: str | None = None
    population_field: str | None = None
    confounder_fields: tuple[str, ...] = ()
    context_fields: tuple[str, ...] = ()
    coordinate_fields: tuple[str, str] | None = None
    bootstrap_group_field: str | None = None
    placebo_exposure_fields: tuple[str, ...] = ()
    lower_exposure_quantile: float | None = 0.01
    upper_exposure_quantile: float | None = 0.99
    target_outcomes: tuple[float, ...] = ()
    bootstrap_replicates: int = 200


class GeoCausalSCCAAlgorithm:
    """Runtime-independent skeleton for a future QGIS Processing algorithm."""

    PARAM_INPUT = "INPUT"
    PARAM_CASE_NAME = "CASE_NAME"
    PARAM_UNIT_ID = "UNIT_ID_FIELD"
    PARAM_EXPOSURE = "EXPOSURE_FIELD"
    PARAM_OUTCOME = "OUTCOME_FIELD"
    PARAM_BASELINE = "BASELINE_OUTCOME_FIELD"
    PARAM_POPULATION = "POPULATION_FIELD"
    PARAM_CONFOUNDERS = "CONFOUNDER_FIELDS"
    PARAM_CONTEXT = "CONTEXT_FIELDS"
    PARAM_COORDINATES = "COORDINATE_FIELDS"
    PARAM_BOOTSTRAP_GROUP = "BOOTSTRAP_GROUP_FIELD"
    PARAM_PLACEBO = "PLACEBO_EXPOSURE_FIELDS"
    PARAM_LOWER_Q = "LOWER_EXPOSURE_QUANTILE"
    PARAM_UPPER_Q = "UPPER_EXPOSURE_QUANTILE"
    PARAM_TARGET_OUTCOMES = "TARGET_OUTCOME_VALUES"
    PARAM_BOOTSTRAP_REPS = "BOOTSTRAP_REPLICATES"
    PARAM_OUTPUT_FOLDER = "OUTPUT_FOLDER"
    PARAM_OUTPUT_JOINED = "OUTPUT_ANALYSIS_TABLE"

    def name(self) -> str:
        return "geocausal_scca"

    def displayName(self) -> str:
        return "GeoCausal SCCA Analysis"

    def group(self) -> str:
        return "GeoCausal"

    def groupId(self) -> str:
        return "geocausal"

    def create_request(self, run_request: QGISRunRequest) -> AnalysisRequest:
        return AnalysisRequest(
            case_name=run_request.case_name,
            input_path=run_request.input_csv,
            output_dir=run_request.output_dir,
            unit_id=run_request.unit_id_field,
            exposure=run_request.exposure_field,
            outcome=run_request.outcome_field,
            baseline_outcome=run_request.baseline_outcome_field,
            population=run_request.population_field,
            confounders=run_request.confounder_fields,
            context_columns=run_request.context_fields,
            coordinate_columns=run_request.coordinate_fields,
            bootstrap_group=run_request.bootstrap_group_field,
            placebo_exposures=run_request.placebo_exposure_fields,
            lower_exposure_quantile=run_request.lower_exposure_quantile,
            upper_exposure_quantile=run_request.upper_exposure_quantile,
            target_outcomes=run_request.target_outcomes,
            bootstrap_replicates=run_request.bootstrap_replicates,
        )

    def run_from_csv(self, run_request: QGISRunRequest) -> dict[str, object]:
        request = self.create_request(run_request)
        manifest = run_scca_analysis(request)
        target_file = manifest.get("files", {}).get("target_exposures")
        if target_file:
            build_analysis_joined_table(
                input_csv=run_request.input_csv,
                target_exposures_csv=run_request.output_dir / str(target_file),
                output_csv=run_request.output_dir / "analysis_joined.csv",
                unit_id_field=run_request.unit_id_field,
            )
        return manifest

