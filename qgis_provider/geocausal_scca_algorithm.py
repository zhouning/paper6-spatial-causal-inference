from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    """Runtime-independent QGIS-facing adapter over the shared GeoCausal core."""

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
    OUTPUT_FOLDER = "OUTPUT_FOLDER_PATH"
    OUTPUT_MANIFEST = "OUTPUT_MANIFEST"
    OUTPUT_REPORT = "OUTPUT_REPORT"
    OUTPUT_RESULT_SUMMARY = "OUTPUT_RESULT_SUMMARY"
    OUTPUT_OPEN_GIS_PACKAGE = "OUTPUT_OPEN_GIS_PACKAGE"
    OUTPUT_OPEN_GIS_JOINED = "OUTPUT_OPEN_GIS_ANALYSIS_JOINED"
    OUTPUT_OPEN_GIS_BALANCE = "OUTPUT_OPEN_GIS_BALANCE_SUMMARY"
    OUTPUT_OPEN_GIS_ERF_200 = "OUTPUT_OPEN_GIS_ERF_200"
    OUTPUT_OPEN_GIS_ARCGIS_STYLE_GRID = "OUTPUT_OPEN_GIS_ARCGIS_STYLE_GRID"
    OUTPUT_OPEN_GIS_ARCGIS_STYLE_BALANCE = "OUTPUT_OPEN_GIS_ARCGIS_STYLE_BALANCE"
    OUTPUT_OPEN_GIS_ARCGIS_STYLE_CALIBRATED_BALANCE = "OUTPUT_OPEN_GIS_ARCGIS_STYLE_CALIBRATED_BALANCE"
    OUTPUT_OPEN_GIS_SUMMARY_JSON = "OUTPUT_OPEN_GIS_SUMMARY_JSON"
    OUTPUT_OPEN_GIS_SUMMARY_MD = "OUTPUT_OPEN_GIS_SUMMARY_MD"

    def name(self) -> str:
        return "geocausal_scca"

    def displayName(self) -> str:
        return "GeoCausal SCCA Analysis"

    def group(self) -> str:
        return "GeoCausal"

    def groupId(self) -> str:
        return "geocausal"

    @staticmethod
    def normalize_multivalue(value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            return tuple(part.strip() for part in value.split(",") if part.strip())
        return tuple(str(part).strip() for part in value if str(part).strip())

    @staticmethod
    def normalize_float_multivalue(value: Any) -> tuple[float, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            return tuple(float(part.strip()) for part in value.split(",") if part.strip())
        return tuple(float(part) for part in value if str(part).strip())

    @staticmethod
    def required_fields_for_request(run_request: QGISRunRequest) -> tuple[str, ...]:
        fields = (
            run_request.unit_id_field,
            run_request.exposure_field,
            run_request.outcome_field,
            run_request.baseline_outcome_field,
            run_request.population_field,
            run_request.bootstrap_group_field,
            *run_request.confounder_fields,
            *run_request.context_fields,
            *run_request.placebo_exposure_fields,
            *(run_request.coordinate_fields or ()),
        )
        ordered: list[str] = []
        for field in fields:
            if field and field not in ordered:
                ordered.append(field)
        return tuple(ordered)

    @staticmethod
    def export_delimited_dataset(
        input_path: Path,
        output_csv: Path,
        *,
        selected_fields: tuple[str, ...],
    ) -> Path:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with input_path.open("r", encoding="utf-8-sig", newline="") as src:
            reader = csv.DictReader(src)
            missing = [field for field in selected_fields if field not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(f"Input CSV is missing fields: {', '.join(missing)}")
            with output_csv.open("w", encoding="utf-8-sig", newline="") as dst:
                writer = csv.DictWriter(dst, fieldnames=list(selected_fields))
                writer.writeheader()
                for row in reader:
                    writer.writerow({field: row.get(field) for field in selected_fields})
        return output_csv

    @staticmethod
    def export_qgis_source_to_csv(
        source: Any,
        output_csv: Path,
        *,
        selected_fields: tuple[str, ...],
        derive_coordinates: bool = True,
    ) -> tuple[Path, tuple[str, str] | None]:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        source_fields = {field.name() for field in source.fields()}
        missing = [field for field in selected_fields if field not in source_fields]
        if missing:
            raise ValueError(f"Input layer/table is missing fields: {', '.join(missing)}")

        coordinate_columns = None
        output_fields = list(selected_fields)
        if derive_coordinates:
            output_fields.extend(["_gc_x", "_gc_y"])
            coordinate_columns = ("_gc_x", "_gc_y")

        with output_csv.open("w", encoding="utf-8-sig", newline="") as dst:
            writer = csv.DictWriter(dst, fieldnames=output_fields)
            writer.writeheader()
            for feature in source.getFeatures():
                row = {field: feature.attribute(field) for field in selected_fields}
                if derive_coordinates:
                    point = None
                    if feature.hasGeometry():
                        geometry = feature.geometry()
                        if not geometry.isNull() and not geometry.isEmpty():
                            point_geometry = geometry.pointOnSurface()
                            if point_geometry.isNull() or point_geometry.isEmpty():
                                point_geometry = geometry.centroid()
                            if not point_geometry.isNull() and not point_geometry.isEmpty():
                                point = point_geometry.asPoint()
                    row["_gc_x"] = point.x() if point is not None else None
                    row["_gc_y"] = point.y() if point is not None else None
                writer.writerow(row)
        return output_csv, coordinate_columns

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

    @classmethod
    def open_gis_package_outputs(cls, output_dir: Path, manifest: dict[str, object]) -> dict[str, str]:
        package = manifest.get("open_gis_package")
        package_data = package if isinstance(package, dict) else {}
        generated = package_data.get("generated_files")
        generated_files = generated if isinstance(generated, dict) else {}
        package_dir = output_dir / str(package_data.get("package_dir") or "open_gis_analysis_package")

        def generated_path(key: str, default_name: str) -> str:
            return str(package_dir / str(generated_files.get(key) or default_name))

        return {
            cls.OUTPUT_OPEN_GIS_PACKAGE: str(package_dir),
            cls.OUTPUT_OPEN_GIS_JOINED: generated_path("analysis_joined", "analysis_joined.csv"),
            cls.OUTPUT_OPEN_GIS_BALANCE: generated_path("gis_balance_summary", "gis_balance_summary.csv"),
            cls.OUTPUT_OPEN_GIS_ERF_200: generated_path("gis_erf_curve_200", "gis_erf_curve_200.csv"),
            cls.OUTPUT_OPEN_GIS_ARCGIS_STYLE_GRID: generated_path(
                "arcgis_style_matching_grid", "arcgis_style_matching_grid.csv"
            ),
            cls.OUTPUT_OPEN_GIS_ARCGIS_STYLE_BALANCE: generated_path(
                "arcgis_style_balance_summary", "arcgis_style_balance_summary.csv"
            ),
            cls.OUTPUT_OPEN_GIS_ARCGIS_STYLE_CALIBRATED_BALANCE: generated_path(
                "arcgis_style_calibrated_balance_summary",
                "arcgis_style_calibrated_balance_summary.csv",
            ),
            cls.OUTPUT_OPEN_GIS_SUMMARY_JSON: generated_path("gis_run_summary_json", "gis_run_summary.json"),
            cls.OUTPUT_OPEN_GIS_SUMMARY_MD: generated_path("gis_run_summary_markdown", "gis_run_summary.md"),
        }

    def run_from_parameters(self, parameters: dict[str, Any]) -> dict[str, object]:
        output_dir = Path(str(parameters[self.PARAM_OUTPUT_FOLDER]))
        case_name = str(parameters[self.PARAM_CASE_NAME])
        run_request = QGISRunRequest(
            case_name=case_name,
            input_csv=Path(str(parameters[self.PARAM_INPUT])),
            output_dir=output_dir / case_name,
            exposure_field=str(parameters[self.PARAM_EXPOSURE]),
            outcome_field=str(parameters[self.PARAM_OUTCOME]),
            unit_id_field=parameters.get(self.PARAM_UNIT_ID) or None,
            baseline_outcome_field=parameters.get(self.PARAM_BASELINE) or None,
            population_field=parameters.get(self.PARAM_POPULATION) or None,
            confounder_fields=self.normalize_multivalue(parameters.get(self.PARAM_CONFOUNDERS)),
            context_fields=self.normalize_multivalue(parameters.get(self.PARAM_CONTEXT)),
            coordinate_fields=tuple(parameters[self.PARAM_COORDINATES])
            if parameters.get(self.PARAM_COORDINATES)
            else None,
            bootstrap_group_field=parameters.get(self.PARAM_BOOTSTRAP_GROUP) or None,
            placebo_exposure_fields=self.normalize_multivalue(parameters.get(self.PARAM_PLACEBO)),
            lower_exposure_quantile=float(parameters[self.PARAM_LOWER_Q])
            if parameters.get(self.PARAM_LOWER_Q) is not None
            else None,
            upper_exposure_quantile=float(parameters[self.PARAM_UPPER_Q])
            if parameters.get(self.PARAM_UPPER_Q) is not None
            else None,
            target_outcomes=self.normalize_float_multivalue(parameters.get(self.PARAM_TARGET_OUTCOMES)),
            bootstrap_replicates=int(parameters.get(self.PARAM_BOOTSTRAP_REPS, 200)),
        )
        return self.run_from_csv(run_request)

    @classmethod
    def create_qgis_algorithm(cls) -> Any:
        try:
            from qgis.core import (  # type: ignore
                QgsProcessingAlgorithm,
                QgsProcessingOutputFile,
                QgsProcessingOutputFolder,
                QgsProcessingParameterField,
                QgsProcessingParameterFeatureSource,
                QgsProcessingParameterFolderDestination,
                QgsProcessingParameterNumber,
                QgsProcessingParameterString,
                Qgis,
            )
        except ImportError:
            return cls()

        algorithm = cls()

        class QGISGeoCausalAlgorithm(QgsProcessingAlgorithm):  # type: ignore[misc]
            def name(self) -> str:
                return algorithm.name()

            def displayName(self) -> str:
                return algorithm.displayName()

            def group(self) -> str:
                return algorithm.group()

            def groupId(self) -> str:
                return algorithm.groupId()

            def createInstance(self):
                return QGISGeoCausalAlgorithm()

            def initAlgorithm(self, config=None) -> None:
                self.addParameter(
                    QgsProcessingParameterFeatureSource(
                        cls.PARAM_INPUT,
                        "Input layer or table",
                        [Qgis.ProcessingSourceType.Vector],
                    )
                )
                self.addParameter(QgsProcessingParameterString(cls.PARAM_CASE_NAME, "Case Name"))
                self.addParameter(QgsProcessingParameterField(cls.PARAM_UNIT_ID, "Unit ID Field", parentLayerParameterName=cls.PARAM_INPUT, optional=True))
                self.addParameter(QgsProcessingParameterField(cls.PARAM_EXPOSURE, "Exposure Field", parentLayerParameterName=cls.PARAM_INPUT, type=Qgis.ProcessingFieldParameterDataType.Numeric))
                self.addParameter(QgsProcessingParameterField(cls.PARAM_OUTCOME, "Outcome Field", parentLayerParameterName=cls.PARAM_INPUT, type=Qgis.ProcessingFieldParameterDataType.Numeric))
                self.addParameter(QgsProcessingParameterField(cls.PARAM_BASELINE, "Baseline Outcome Field", parentLayerParameterName=cls.PARAM_INPUT, type=Qgis.ProcessingFieldParameterDataType.Numeric, optional=True))
                self.addParameter(QgsProcessingParameterField(cls.PARAM_POPULATION, "Population Field", parentLayerParameterName=cls.PARAM_INPUT, type=Qgis.ProcessingFieldParameterDataType.Numeric, optional=True))
                self.addParameter(QgsProcessingParameterField(cls.PARAM_CONFOUNDERS, "Confounder Fields", parentLayerParameterName=cls.PARAM_INPUT, type=Qgis.ProcessingFieldParameterDataType.Numeric, allowMultiple=True, optional=True))
                self.addParameter(QgsProcessingParameterField(cls.PARAM_CONTEXT, "Context Fields", parentLayerParameterName=cls.PARAM_INPUT, type=Qgis.ProcessingFieldParameterDataType.Numeric, allowMultiple=True, optional=True))
                self.addParameter(QgsProcessingParameterField(cls.PARAM_COORDINATES, "X/Y Coordinate Fields", parentLayerParameterName=cls.PARAM_INPUT, type=Qgis.ProcessingFieldParameterDataType.Numeric, allowMultiple=True, optional=True))
                self.addParameter(QgsProcessingParameterField(cls.PARAM_BOOTSTRAP_GROUP, "Bootstrap Group Field", parentLayerParameterName=cls.PARAM_INPUT, optional=True))
                self.addParameter(QgsProcessingParameterField(cls.PARAM_PLACEBO, "Placebo Exposure Fields", parentLayerParameterName=cls.PARAM_INPUT, type=Qgis.ProcessingFieldParameterDataType.Numeric, allowMultiple=True, optional=True))
                self.addParameter(QgsProcessingParameterNumber(cls.PARAM_LOWER_Q, "Lower Exposure Quantile", type=QgsProcessingParameterNumber.Double, defaultValue=0.01, optional=True))
                self.addParameter(QgsProcessingParameterNumber(cls.PARAM_UPPER_Q, "Upper Exposure Quantile", type=QgsProcessingParameterNumber.Double, defaultValue=0.99, optional=True))
                self.addParameter(QgsProcessingParameterString(cls.PARAM_TARGET_OUTCOMES, "Target Outcome Values (comma-separated)", optional=True))
                self.addParameter(QgsProcessingParameterNumber(cls.PARAM_BOOTSTRAP_REPS, "Bootstrap Replicates", type=QgsProcessingParameterNumber.Integer, defaultValue=200, optional=True))
                self.addParameter(
                    QgsProcessingParameterFolderDestination(
                        cls.PARAM_OUTPUT_FOLDER,
                        "Output Folder",
                    )
                )
                self.addOutput(QgsProcessingOutputFolder(cls.OUTPUT_FOLDER, "Case Output Folder"))
                self.addOutput(QgsProcessingOutputFile(cls.OUTPUT_MANIFEST, "Manifest JSON"))
                self.addOutput(QgsProcessingOutputFile(cls.OUTPUT_REPORT, "Analysis Report"))
                self.addOutput(QgsProcessingOutputFile(cls.OUTPUT_RESULT_SUMMARY, "Result Summary"))
                self.addOutput(QgsProcessingOutputFile(cls.PARAM_OUTPUT_JOINED, "Analysis Joined CSV"))
                self.addOutput(QgsProcessingOutputFolder(cls.OUTPUT_OPEN_GIS_PACKAGE, "Open GIS Package Folder"))
                self.addOutput(QgsProcessingOutputFile(cls.OUTPUT_OPEN_GIS_JOINED, "Open GIS Analysis Joined CSV"))
                self.addOutput(QgsProcessingOutputFile(cls.OUTPUT_OPEN_GIS_BALANCE, "Open GIS Balance Summary CSV"))
                self.addOutput(QgsProcessingOutputFile(cls.OUTPUT_OPEN_GIS_ERF_200, "Open GIS ERF 200 CSV"))
                self.addOutput(QgsProcessingOutputFile(cls.OUTPUT_OPEN_GIS_ARCGIS_STYLE_GRID, "Open GIS ArcGIS-style Matching Grid CSV"))
                self.addOutput(QgsProcessingOutputFile(cls.OUTPUT_OPEN_GIS_ARCGIS_STYLE_BALANCE, "Open GIS ArcGIS-style Balance CSV"))
                self.addOutput(QgsProcessingOutputFile(cls.OUTPUT_OPEN_GIS_ARCGIS_STYLE_CALIBRATED_BALANCE, "Open GIS Calibrated Balance CSV"))
                self.addOutput(QgsProcessingOutputFile(cls.OUTPUT_OPEN_GIS_SUMMARY_JSON, "Open GIS Summary JSON"))
                self.addOutput(QgsProcessingOutputFile(cls.OUTPUT_OPEN_GIS_SUMMARY_MD, "Open GIS Summary Markdown"))

            def processAlgorithm(self, parameters, context, feedback):
                source = self.parameterAsSource(parameters, cls.PARAM_INPUT, context)
                if source is None:
                    raise ValueError("Input layer or table could not be resolved.")

                output_root = Path(self.parameterAsString(parameters, cls.PARAM_OUTPUT_FOLDER, context))
                case_name = self.parameterAsString(parameters, cls.PARAM_CASE_NAME, context)
                output_dir = output_root / case_name

                coordinate_fields = tuple(self.parameterAsFields(parameters, cls.PARAM_COORDINATES, context))
                if coordinate_fields and len(coordinate_fields) != 2:
                    raise ValueError("Provide exactly two coordinate fields: X and Y.")

                run_request = QGISRunRequest(
                    case_name=case_name,
                    input_csv=output_dir / "input.csv",
                    output_dir=output_dir,
                    exposure_field=self.parameterAsString(parameters, cls.PARAM_EXPOSURE, context),
                    outcome_field=self.parameterAsString(parameters, cls.PARAM_OUTCOME, context),
                    unit_id_field=self.parameterAsString(parameters, cls.PARAM_UNIT_ID, context) or None,
                    baseline_outcome_field=self.parameterAsString(parameters, cls.PARAM_BASELINE, context) or None,
                    population_field=self.parameterAsString(parameters, cls.PARAM_POPULATION, context) or None,
                    confounder_fields=tuple(self.parameterAsFields(parameters, cls.PARAM_CONFOUNDERS, context)),
                    context_fields=tuple(self.parameterAsFields(parameters, cls.PARAM_CONTEXT, context)),
                    coordinate_fields=coordinate_fields if coordinate_fields else None,
                    bootstrap_group_field=self.parameterAsString(parameters, cls.PARAM_BOOTSTRAP_GROUP, context) or None,
                    placebo_exposure_fields=tuple(self.parameterAsFields(parameters, cls.PARAM_PLACEBO, context)),
                    lower_exposure_quantile=self.parameterAsDouble(parameters, cls.PARAM_LOWER_Q, context),
                    upper_exposure_quantile=self.parameterAsDouble(parameters, cls.PARAM_UPPER_Q, context),
                    target_outcomes=cls.normalize_float_multivalue(
                        self.parameterAsString(parameters, cls.PARAM_TARGET_OUTCOMES, context)
                    ),
                    bootstrap_replicates=self.parameterAsInt(parameters, cls.PARAM_BOOTSTRAP_REPS, context),
                )
                selected_fields = cls.required_fields_for_request(run_request)
                _, derived_coordinates = cls.export_qgis_source_to_csv(
                    source,
                    run_request.input_csv,
                    selected_fields=selected_fields,
                    derive_coordinates=run_request.coordinate_fields is None,
                )
                if run_request.coordinate_fields is None and derived_coordinates is not None:
                    run_request = QGISRunRequest(
                        **{
                            **run_request.__dict__,
                            "coordinate_fields": derived_coordinates,
                        }
                    )

                manifest = algorithm.run_from_csv(run_request)
                result = {
                    cls.OUTPUT_FOLDER: str(output_dir),
                    cls.OUTPUT_MANIFEST: str(output_dir / manifest["files"]["manifest"]),
                    cls.OUTPUT_REPORT: str(output_dir / manifest["files"]["analysis_report"]),
                    cls.OUTPUT_RESULT_SUMMARY: str(output_dir / manifest["files"]["result_summary_markdown"]),
                }
                result.update(cls.open_gis_package_outputs(output_dir, manifest))
                joined_path = output_dir / "analysis_joined.csv"
                result[cls.PARAM_OUTPUT_JOINED] = str(joined_path) if joined_path.exists() else ""
                return result

        return QGISGeoCausalAlgorithm()
