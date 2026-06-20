from __future__ import annotations

import sys
from pathlib import Path


TOOLBOX_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLBOX_DIR.parent
DEFAULT_OUTPUT_FOLDER = REPO_ROOT / "paper" / "ijgis_submission_20260605" / "07_results"
for candidate in (str(TOOLBOX_DIR), str(REPO_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from geocausal.adapters import AnalysisRequest, run_scca_analysis  # noqa: E402
from geocausal.errors import GeoCausalError  # noqa: E402
from arcgis_toolbox.geocausal_arcgis_support import (  # noqa: E402
    build_analysis_joined_table,
    copy_csv_to_arcgis_table,
    export_input_dataset,
    parse_multivalue_floats,
    parse_multivalue_text,
    summarize_manifest_messages,
)


PARAM_INPUT_DATASET = 0
PARAM_CASE_NAME = 1
PARAM_UNIT_ID = 2
PARAM_EXPOSURE = 3
PARAM_OUTCOME = 4
PARAM_BASELINE = 5
PARAM_POPULATION = 6
PARAM_CONFOUNDERS = 7
PARAM_CONTEXT = 8
PARAM_X_FIELD = 9
PARAM_Y_FIELD = 10
PARAM_BOOTSTRAP_GROUP = 11
PARAM_PLACEBO = 12
PARAM_LOWER_Q = 13
PARAM_UPPER_Q = 14
PARAM_TARGET_OUTCOMES = 15
PARAM_BOOTSTRAP_REPS = 16
PARAM_OUTPUT_FOLDER = 17
PARAM_OUTPUT_ANALYSIS_TABLE = 18
PARAM_OUTPUT_ERF_TABLE = 19
PARAM_OUTPUT_TARGET_TABLE = 20
PARAM_OUTPUT_EFFECT_TABLE = 21


class Toolbox:
    def __init__(self):
        self.label = "GeoCausal SCCA Toolbox"
        self.alias = "geocausal_scca"
        self.tools = [GeoCausalSCCATool]


class GeoCausalSCCATool:
    def __init__(self):
        self.label = "GeoCausal SCCA Analysis"
        self.description = (
            "Generic geospatial causal analysis with exposure trimming, ERF estimation, "
            "robustness outputs, and target-outcome exposure tables."
        )
        self.canRunInBackground = False

    def getParameterInfo(self):
        import arcpy

        params = []

        def param(name, display_name, datatype, parameter_type="Required", direction="Input"):
            p = arcpy.Parameter(
                displayName=display_name,
                name=name,
                datatype=datatype,
                parameterType=parameter_type,
                direction=direction,
            )
            params.append(p)
            return p

        input_dataset = param("input_dataset", "Input Features or Table", ["GPFeatureLayer", "GPTableView"])
        case_name = param("case_name", "Case Name", "GPString")
        unit_id = param("unit_id_field", "Unit ID Field", "Field", "Optional")
        unit_id.parameterDependencies = [input_dataset.name]
        exposure = param("exposure_field", "Exposure Field", "Field")
        exposure.parameterDependencies = [input_dataset.name]
        outcome = param("outcome_field", "Outcome Field", "Field")
        outcome.parameterDependencies = [input_dataset.name]
        baseline = param("baseline_outcome_field", "Baseline Outcome Field", "Field", "Optional")
        baseline.parameterDependencies = [input_dataset.name]
        population = param("population_field", "Population Field", "Field", "Optional")
        population.parameterDependencies = [input_dataset.name]
        confounders = param("confounder_fields", "Confounding Variables", "Field", "Optional")
        confounders.parameterDependencies = [input_dataset.name]
        confounders.multiValue = True
        context_fields = param("context_fields", "Context Fields", "Field", "Optional")
        context_fields.parameterDependencies = [input_dataset.name]
        context_fields.multiValue = True
        x_field = param("x_field", "X Coordinate Field", "Field", "Optional")
        x_field.parameterDependencies = [input_dataset.name]
        y_field = param("y_field", "Y Coordinate Field", "Field", "Optional")
        y_field.parameterDependencies = [input_dataset.name]
        bootstrap_group = param("bootstrap_group_field", "Bootstrap Group Field", "Field", "Optional")
        bootstrap_group.parameterDependencies = [input_dataset.name]
        placebo_fields = param("placebo_exposure_fields", "Placebo Exposure Fields", "Field", "Optional")
        placebo_fields.parameterDependencies = [input_dataset.name]
        placebo_fields.multiValue = True
        lower_q = param("lower_exposure_quantile", "Lower Exposure Quantile", "GPDouble", "Optional")
        lower_q.value = 0.01
        upper_q = param("upper_exposure_quantile", "Upper Exposure Quantile", "GPDouble", "Optional")
        upper_q.value = 0.99
        target_outcomes = param("target_outcome_values", "Target Outcome Values", "GPDouble", "Optional")
        target_outcomes.multiValue = True
        bootstrap_reps = param("bootstrap_replicates", "Bootstrap Replicates", "GPLong", "Optional")
        bootstrap_reps.value = 200
        output_folder = param("output_folder", "Output Report Folder", "DEFolder")
        output_folder.value = str(DEFAULT_OUTPUT_FOLDER)
        output_analysis = param(
            "output_analysis_table",
            "Output Analysis Joined Table",
            "DETable",
            "Optional",
            "Output",
        )
        output_erf = param("output_erf_table", "Output ERF Table", "DETable", "Optional", "Output")
        output_target = param(
            "output_target_exposure_table",
            "Output Target Exposure Table",
            "DETable",
            "Optional",
            "Output",
        )
        output_effects = param(
            "output_effect_estimates_table",
            "Output Effect Estimates Table",
            "DETable",
            "Optional",
            "Output",
        )

        return params

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        import arcpy

        lower = parameters[PARAM_LOWER_Q].value
        upper = parameters[PARAM_UPPER_Q].value
        if lower is not None and upper is not None:
            try:
                lower_value = float(lower)
                upper_value = float(upper)
            except Exception:
                return
            if not (0.0 <= lower_value < upper_value <= 1.0):
                parameters[PARAM_LOWER_Q].setErrorMessage("Quantiles must satisfy 0 <= lower < upper <= 1.")
                parameters[PARAM_UPPER_Q].setErrorMessage("Quantiles must satisfy 0 <= lower < upper <= 1.")

        if bool(parameters[PARAM_X_FIELD].valueAsText) ^ bool(parameters[PARAM_Y_FIELD].valueAsText):
            parameters[PARAM_X_FIELD].setErrorMessage("Provide both X and Y coordinate fields, or neither.")
            parameters[PARAM_Y_FIELD].setErrorMessage("Provide both X and Y coordinate fields, or neither.")

    def execute(self, parameters, messages):
        import arcpy

        input_dataset = parameters[PARAM_INPUT_DATASET].valueAsText
        case_name = parameters[PARAM_CASE_NAME].valueAsText
        unit_id = parameters[PARAM_UNIT_ID].valueAsText or None
        exposure = parameters[PARAM_EXPOSURE].valueAsText
        outcome = parameters[PARAM_OUTCOME].valueAsText
        baseline = parameters[PARAM_BASELINE].valueAsText or None
        population = parameters[PARAM_POPULATION].valueAsText or None
        confounders = parse_multivalue_text(parameters[PARAM_CONFOUNDERS])
        context_fields = parse_multivalue_text(parameters[PARAM_CONTEXT])
        x_field = parameters[PARAM_X_FIELD].valueAsText or None
        y_field = parameters[PARAM_Y_FIELD].valueAsText or None
        bootstrap_group = parameters[PARAM_BOOTSTRAP_GROUP].valueAsText or None
        placebo_fields = parse_multivalue_text(parameters[PARAM_PLACEBO])
        lower_q = float(parameters[PARAM_LOWER_Q].value) if parameters[PARAM_LOWER_Q].value is not None else None
        upper_q = float(parameters[PARAM_UPPER_Q].value) if parameters[PARAM_UPPER_Q].value is not None else None
        target_outcomes = parse_multivalue_floats(parameters[PARAM_TARGET_OUTCOMES])
        bootstrap_replicates = (
            int(parameters[PARAM_BOOTSTRAP_REPS].value)
            if parameters[PARAM_BOOTSTRAP_REPS].value is not None
            else 200
        )
        output_folder = Path(parameters[PARAM_OUTPUT_FOLDER].valueAsText)
        working_dir = output_folder / case_name
        working_dir.mkdir(parents=True, exist_ok=True)
        csv_path = working_dir / "input.csv"

        required_fields = tuple(
            field
            for field in (
                unit_id,
                exposure,
                outcome,
                baseline,
                population,
                bootstrap_group,
                *confounders,
                *context_fields,
                *placebo_fields,
            )
            if field
        )

        export_summary = export_input_dataset(
            input_dataset,
            csv_path,
            fields=required_fields,
            x_field=x_field,
            y_field=y_field,
        )
        coordinate_columns = export_summary["coordinate_columns"]
        request = AnalysisRequest(
            case_name=case_name,
            input_path=csv_path,
            output_dir=working_dir,
            unit_id=unit_id,
            exposure=exposure,
            outcome=outcome,
            baseline_outcome=baseline,
            population=population,
            confounders=tuple(confounders),
            context_columns=tuple(context_fields),
            coordinate_columns=coordinate_columns if isinstance(coordinate_columns, tuple) else None,
            bootstrap_group=bootstrap_group,
            placebo_exposures=tuple(placebo_fields),
            lower_exposure_quantile=lower_q,
            upper_exposure_quantile=upper_q,
            target_outcomes=tuple(target_outcomes),
            bootstrap_replicates=bootstrap_replicates,
        )

        try:
            manifest = run_scca_analysis(request)
        except GeoCausalError as exc:
            raise arcpy.ExecuteError(str(exc))

        for line in summarize_manifest_messages(manifest):
            messages.addMessage(line)
        copy_csv_to_arcgis_table(
            working_dir / manifest["files"]["erf_curve"],
            parameters[PARAM_OUTPUT_ERF_TABLE].valueAsText,
        )
        if "target_exposures" in manifest["files"]:
            analysis_table = build_analysis_joined_table(
                input_csv=csv_path,
                target_exposures_csv=working_dir / manifest["files"]["target_exposures"],
                output_csv=working_dir / "analysis_joined.csv",
                unit_id_field=unit_id,
                method="erf_delta_anchor",
            )
            copy_csv_to_arcgis_table(
                analysis_table,
                parameters[PARAM_OUTPUT_ANALYSIS_TABLE].valueAsText,
            )
            copy_csv_to_arcgis_table(
                working_dir / manifest["files"]["target_exposures"],
                parameters[PARAM_OUTPUT_TARGET_TABLE].valueAsText,
            )
        copy_csv_to_arcgis_table(
            working_dir / manifest["files"]["effect_estimates"],
            parameters[PARAM_OUTPUT_EFFECT_TABLE].valueAsText,
        )
        messages.addMessage(f"Output folder: {working_dir}")

    def postExecute(self, parameters):
        return
