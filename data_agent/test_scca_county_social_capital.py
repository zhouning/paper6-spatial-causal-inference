import json
import subprocess

import pandas as pd

from data_agent.experiments.run_scca_county_social_capital import (
    DEFAULT_OUTPUT_DIR,
    PROJECT_ROOT,
    _git_dirty,
    _run_git,
    prepare_county_social_capital_table,
    run_county_social_capital_scca,
)
from data_agent.scca.specs import StudySpec


def _county_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "OBJECTID": [1, 2, 3, 4, 5, 6],
            "STATE_NAME": ["Alpha", "Alpha", "Beta", "Beta", "Gamma", "Gamma"],
            "CountyCode": [1001, 1003, 2001, 2003, 3001, 3003],
            "County": [
                "A County, AA",
                "B County, AA",
                "C County, BB",
                "D County, BB",
                "E County, CC",
                "F County, CC",
            ],
            "FIPS": [1001, 1003, 2001, 2003, 3001, 3003],
            "AveAgeDeath": [70.2, 72.7, 71.8, 73.1, 69.5, 74.0],
            "SocialAssoc": [12.6, 10.7, 8.5, 14.0, 7.2, 15.3],
            "UnemployRate": [3.8, 3.2, 7.9, 4.4, 6.1, 3.9],
            "pHHinPoverty": [13.25, 12.1, 25.78, 11.2, 18.4, 9.8],
            "pNoHealthInsur": [8.8, 10.9, 12.4, 7.3, 11.1, 6.9],
            "MentalHealth": [4.3, 4.2, 4.6, 4.0, 4.8, 3.9],
            "pAdultSmoking": [19.1, 16.8, 21.5, 15.0, 22.1, 14.2],
            "pAdultObesity": [37.5, 31.0, 44.3, 28.4, 39.1, 27.9],
            "FastFood": [3.47, 2.90, 2.71, 3.80, 2.50, 4.10],
            "pInsufficientSleep": [35.9, 33.3, 38.6, 31.0, 39.4, 30.5],
            "pAlcohol": [4.9, 8.8, 5.2, 9.0, 4.2, 10.1],
            "pSuicideDeaths": [16.8, 17.7, 10.8, 14.2, 12.4, 15.6],
            "AirPollution": [11.7, 10.3, 11.5, 8.8, 9.6, 7.9],
            "Shape_Length": [192945.1, 380525.4, 226532.8, 210000.0, 260000.0, 240000.0],
            "Shape_Area": [1.55e9, 4.31e9, 2.33e9, 1.80e9, 2.10e9, 1.70e9],
        }
    )


def test_county_social_capital_study_spec_defaults():
    spec = StudySpec.county_social_capital_default()
    assert spec.name == "county_social_capital_longevity_validation"
    assert spec.unit_id == "FIPS"
    assert spec.exposure == "SocialAssoc"
    assert spec.outcome == "AveAgeDeath"
    assert "pHHinPoverty" in spec.confounders
    assert "AirPollution" in spec.confounders
    assert spec.context_columns == ("Shape_Length", "Shape_Area")
    assert spec.subgroup_column == "STATE_NAME"


def test_prepare_county_social_capital_table_coerces_numeric_and_preserves_text():
    raw = _county_fixture()
    raw["SocialAssoc"] = raw["SocialAssoc"].astype(object)
    raw["FIPS"] = raw["FIPS"].astype(object)
    raw.loc[0, "SocialAssoc"] = "12.6"
    raw.loc[1, "FIPS"] = "1003"
    prepared = prepare_county_social_capital_table(raw)
    assert len(prepared) == len(raw)
    assert prepared["SocialAssoc"].dtype.kind in {"f", "i"}
    assert prepared["FIPS"].dtype.kind in {"f", "i"}
    assert prepared["STATE_NAME"].dtype == object
    assert prepared.loc[0, "STATE_NAME"] == "Alpha"


def test_run_county_social_capital_scca_end_to_end_on_fixture(tmp_path):
    workbook_path = tmp_path / "county_fixture.xlsx"
    _county_fixture().to_excel(workbook_path, sheet_name="CountyData", index=False)
    output_dir = tmp_path / "outputs"
    manifest = run_county_social_capital_scca(workbook_path=workbook_path, output_dir=output_dir)
    assert manifest["study"] == "county_social_capital_longevity_validation"
    assert manifest["decision"] in {"strong_support", "moderate_support", "weak_or_failed_support"}
    assert manifest["metadata"]["sheet_name"] == "CountyData"
    assert manifest["metadata"]["input_rows"] == 6
    assert manifest["metadata"]["source_sha256"]
    for file_name in manifest["files"].values():
        assert (output_dir / file_name).exists()


def test_county_social_capital_cli_prints_manifest_json(tmp_path):
    workbook_path = tmp_path / "county_fixture.xlsx"
    _county_fixture().to_excel(workbook_path, sheet_name="CountyData", index=False)
    output_dir = tmp_path / "outputs"
    result = subprocess.run(
        [
            "D:\\adk\\.venv\\Scripts\\python.exe",
            "-m",
            "data_agent.experiments.run_scca_county_social_capital",
            "--workbook-path",
            str(workbook_path),
            "--output-dir",
            str(output_dir),
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads(result.stdout)
    assert manifest["study"] == "county_social_capital_longevity_validation"
    assert manifest["metadata"]["input_rows"] == 6


def test_county_git_runner_marks_worktree_safe(monkeypatch):
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

        class Result:
            stdout = "abc123\n"

        return Result()

    monkeypatch.setattr(
        "data_agent.experiments.run_scca_county_social_capital.subprocess.run",
        fake_run,
    )
    result = _run_git("rev-parse", "HEAD")
    assert result == "abc123"
    assert captured["args"] == [
        "git",
        "-c",
        f"safe.directory={PROJECT_ROOT.as_posix()}",
        "rev-parse",
        "HEAD",
    ]
    assert captured["kwargs"]["cwd"] == PROJECT_ROOT


def test_county_git_dirty_can_ignore_generated_output_dir(monkeypatch):
    monkeypatch.setattr(
        "data_agent.experiments.run_scca_county_social_capital._run_git",
        lambda *args: "\n".join(
            [
                "?? paper/ijgis_submission_20260605/07_results/scca_county_social_capital/manifest.json",
                "?? paper/ijgis_submission_20260605/07_results/scca_county_social_capital/effect_estimates.csv",
            ]
        ),
    )
    assert _git_dirty(ignored_paths=(DEFAULT_OUTPUT_DIR,)) is False


def test_county_git_dirty_reports_source_changes_outside_generated_output_dir(monkeypatch):
    monkeypatch.setattr(
        "data_agent.experiments.run_scca_county_social_capital._run_git",
        lambda *args: "\n".join(
            [
                " M data_agent/experiments/run_scca_county_social_capital.py",
                "?? paper/ijgis_submission_20260605/07_results/scca_county_social_capital/manifest.json",
            ]
        ),
    )
    assert _git_dirty(ignored_paths=(DEFAULT_OUTPUT_DIR,)) is True
