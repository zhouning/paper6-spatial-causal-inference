import pandas as pd

from data_agent.experiments.run_scca_soho import (
    PROJECT_ROOT,
    _run_git,
    prepare_soho_table,
    run_soho_scca,
)
from data_agent.scca.specs import StudySpec


def _soho_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ID": ["1", "2", "3", "4"],
            "deaths": [0, 1, 2, 0],
            "death_dum": [0, 1, 1, 0],
            "dis_bspump": [120.0, 80.0, 20.0, 200.0],
            "dis_pestf": [10.0, 15.0, 30.0, 80.0],
            "dis_sewers": [12.0, 14.0, 22.0, 90.0],
            "pestfield": [1, 1, 0, 0],
            "COORD_X": [529286.0, 529290.0, 529350.0, 529500.0],
            "COORD_Y": [181084.0, 181080.0, 181030.0, 180980.0],
        }
    )


def test_soho_study_spec_defaults():
    spec = StudySpec.soho_default()
    assert spec.name == "soho_broad_street_pump_mechanism"
    assert spec.unit_id == "ID"
    assert spec.exposure == "bspump_proximity"
    assert spec.outcome == "deaths"
    assert "dis_pestf" in spec.confounders
    assert "COORD_X" in spec.context_columns


def test_prepare_soho_table_creates_bspump_proximity():
    prepared = prepare_soho_table(_soho_fixture())
    assert "bspump_proximity" in prepared.columns
    assert prepared.loc[2, "bspump_proximity"] > prepared.loc[0, "bspump_proximity"]
    assert prepared["deaths"].dtype.kind in {"f", "i"}


def test_run_soho_scca_end_to_end_on_fixture(tmp_path):
    csv_path = tmp_path / "soho_fixture.csv"
    _soho_fixture().to_csv(csv_path, index=False)
    output_dir = tmp_path / "outputs"
    manifest = run_soho_scca(csv_path=csv_path, output_dir=output_dir)
    assert manifest["decision"] in {"strong_support", "moderate_support", "weak_or_failed_support"}
    assert manifest["metadata"]["input_rows"] == 4
    assert manifest["metadata"]["source_sha256"]
    for file_name in manifest["files"].values():
        assert (output_dir / file_name).exists()


def test_git_runner_marks_worktree_safe(monkeypatch):
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

        class Result:
            stdout = "abc123\n"

        return Result()

    monkeypatch.setattr("data_agent.experiments.run_scca_soho.subprocess.run", fake_run)
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
