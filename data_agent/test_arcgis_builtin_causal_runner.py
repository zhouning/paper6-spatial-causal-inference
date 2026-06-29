from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


class _FakeValueTable:
    def __init__(self, column_count: int) -> None:
        self.column_count = column_count
        self.rows: list[str] = []

    def addRow(self, row: str) -> None:  # noqa: N802 - mirrors ArcPy
        self.rows.append(row)

    def exportToString(self) -> str:  # noqa: N802 - mirrors ArcPy
        return ";".join(self.rows)


class _FakeArcpy:
    def __init__(self) -> None:
        self.env = SimpleNamespace(overwriteOutput=False)
        self.created_gdbs: list[tuple[str, str]] = []
        self.imported_tables: list[tuple[str, str, str]] = []
        self.causal_calls: list[dict[str, object]] = []
        self._existing: set[str] = set()
        self.management = SimpleNamespace(CreateFileGDB=self._create_file_gdb)
        self.conversion = SimpleNamespace(TableToTable=self._table_to_table)
        self.stats = SimpleNamespace(CausalInferenceAnalysis=self._causal_inference)

    def ValueTable(self, column_count: int) -> _FakeValueTable:  # noqa: N802 - mirrors ArcPy
        return _FakeValueTable(column_count)

    def Exists(self, path: str) -> bool:  # noqa: N802 - mirrors ArcPy
        return path in self._existing

    def GetInstallInfo(self) -> dict[str, str]:  # noqa: N802 - mirrors ArcPy
        return {"Version": "3.7"}

    def ProductInfo(self) -> str:  # noqa: N802 - mirrors ArcPy
        return "ArcInfo"

    def GetMessages(self) -> str:  # noqa: N802 - mirrors ArcPy
        return "ArcGIS causal inference completed"

    def _create_file_gdb(self, out_folder_path: str, out_name: str) -> None:
        self.created_gdbs.append((out_folder_path, out_name))
        self._existing.add(str(Path(out_folder_path) / out_name))

    def _table_to_table(self, in_rows: str, out_path: str, out_name: str) -> None:
        self.imported_tables.append((in_rows, out_path, out_name))
        self._existing.add(str(Path(out_path) / out_name))

    def _causal_inference(self, **kwargs: object) -> str:
        self.causal_calls.append(kwargs)
        return "fake-result"


def test_parse_arcgis_confounder_specs_defaults_numeric_and_accepts_categories():
    from geocausal.arcgis_causal import parse_arcgis_confounder_specs

    assert parse_arcgis_confounder_specs(
        ("UnemployRate", "STATE_NAME:CATEGORICAL", "AirPollution:NUMERIC")
    ) == [
        ["UnemployRate", "NUMERIC"],
        ["STATE_NAME", "CATEGORICAL"],
        ["AirPollution", "NUMERIC"],
    ]


def test_run_arcgis_causal_inference_calls_builtin_tool(tmp_path):
    from geocausal.arcgis_causal import ArcGISCausalInferenceRequest, run_arcgis_causal_inference

    input_csv = tmp_path / "county.csv"
    input_csv.write_text("FIPS,SocialAssoc,AveAgeDeath,UnemployRate\n", encoding="utf-8")
    fake_arcpy = _FakeArcpy()

    manifest = run_arcgis_causal_inference(
        ArcGISCausalInferenceRequest(
            in_features=str(input_csv),
            outcome_field="AveAgeDeath",
            exposure_field="SocialAssoc",
            confounders=("UnemployRate", "STATE_NAME:CATEGORICAL"),
            output_workspace=str(tmp_path / "arcgis_builtin.gdb"),
            output_stem="county_arcgis_builtin",
            target_outcomes=(70.0,),
            lower_exp_trim=0.01,
            upper_exp_trim=0.99,
        ),
        arcpy_module=fake_arcpy,
    )

    assert fake_arcpy.env.overwriteOutput is True
    assert fake_arcpy.created_gdbs == [(str(tmp_path), "arcgis_builtin.gdb")]
    assert fake_arcpy.imported_tables == [
        (str(input_csv), str(tmp_path / "arcgis_builtin.gdb"), "county_arcgis_builtin_input")
    ]
    assert len(fake_arcpy.causal_calls) == 1
    call = fake_arcpy.causal_calls[0]
    assert call["in_features"] == str(tmp_path / "arcgis_builtin.gdb" / "county_arcgis_builtin_input")
    assert call["out_features"] == str(tmp_path / "arcgis_builtin.gdb" / "county_arcgis_builtin_features")
    assert call["out_erf_table"] == str(tmp_path / "arcgis_builtin.gdb" / "county_arcgis_builtin_erf")
    assert call["confounding_variables"].column_count == 2
    assert call["confounding_variables"].exportToString() == (
        "UnemployRate NUMERIC;STATE_NAME CATEGORICAL"
    )
    assert call["target_outcomes"] == [70.0]
    assert call["lower_exp_trim"] == 0.01
    assert call["upper_exp_trim"] == 0.99
    assert manifest["tool"] == "arcpy.stats.CausalInferenceAnalysis"
    assert manifest["arcgis_version"] == "3.7"
    assert manifest["product"] == "ArcInfo"


def test_cli_arcgis_causal_builds_request_and_prints_manifest(tmp_path, monkeypatch, capsys):
    from geocausal import cli

    captured = {}

    def fake_run(request, *, arcpy_module=None, manifest_path=None):
        captured["request"] = request
        captured["manifest_path"] = manifest_path
        return {"tool": "arcpy.stats.CausalInferenceAnalysis", "out_features": "features"}

    monkeypatch.setattr(cli, "run_arcgis_causal_inference", fake_run)

    status = cli.main(
        [
            "arcgis-causal",
            "--input-features",
            "county.csv",
            "--output-workspace",
            str(tmp_path / "arcgis.gdb"),
            "--outcome-field",
            "AveAgeDeath",
            "--exposure-field",
            "SocialAssoc",
            "--confounders",
            "UnemployRate,pHHinPoverty",
            "--target-outcomes",
            "70",
            "--manifest",
            str(tmp_path / "arcgis_manifest.json"),
        ]
    )

    assert status == 0
    request = captured["request"]
    assert request.in_features == "county.csv"
    assert request.output_workspace == str(tmp_path / "arcgis.gdb")
    assert request.confounders == ("UnemployRate", "pHHinPoverty")
    assert request.target_outcomes == (70.0,)
    assert captured["manifest_path"] == tmp_path / "arcgis_manifest.json"
    assert "CausalInferenceAnalysis" in capsys.readouterr().out


def test_summarize_arcgis_causal_messages_extracts_benchmark_metrics():
    from geocausal.arcgis_causal import summarize_arcgis_causal_messages

    summary = summarize_arcgis_causal_messages(
        """
Original number of records                               3108
Number of records removed by exposure trimming             64
Number of records removed by propensity score trimming      0
Final number of records                                  3044
Number of exposure bins                               25
Relative weight of propensity score to exposure   0.8000
[Mean]                               0.1898                 0.0559
Bandwidth (Plug-in): 2.4415
"""
    )

    assert summary == {
        "original_n": 3108,
        "exposure_trimmed_n": 64,
        "propensity_score_trimmed_n": 0,
        "final_n": 3044,
        "selected_num_bins": 25,
        "selected_propensity_exposure_scale": 0.8,
        "mean_original_correlation": 0.1898,
        "mean_weighted_correlation": 0.0559,
        "bandwidth": 2.4415,
    }