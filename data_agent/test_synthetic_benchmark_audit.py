import json

import pandas as pd


def test_synthetic_benchmark_audit_writes_contract_files(tmp_path):
    from data_agent.experiments.synthetic_benchmark_audit import (
        run_synthetic_benchmark_audit,
    )

    manifest = run_synthetic_benchmark_audit(
        output_dir=tmp_path,
        seeds=[0],
        scenario_names=["PSM", "GCCM"],
        setting_names=["baseline"],
    )

    expected_files = {
        "summary_csv": tmp_path / "synthetic_benchmark_audit_summary.csv",
        "details_json": tmp_path / "synthetic_benchmark_audit_details.json",
        "manifest_json": tmp_path / "synthetic_benchmark_audit_manifest.json",
        "report_md": tmp_path / "synthetic_benchmark_audit_report.md",
        "scenario_summary_csv": tmp_path / "scenario_fragility_summary.csv",
    }

    for key, path in expected_files.items():
        assert manifest[key] == str(path)
        assert path.exists()

    summary = pd.read_csv(expected_files["summary_csv"])
    required_columns = {
        "scenario",
        "setting",
        "stress_level",
        "variant",
        "method",
        "metric_name",
        "n_seeds",
        "n_success",
        "failure_count",
        "true_value",
        "estimate_mean",
        "estimate_std",
        "bias",
        "rmse",
        "mae",
        "coverage_rate",
        "fragility",
        "fragility_reason",
        "score",
    }
    assert required_columns.issubset(summary.columns)
    assert set(summary["scenario"]) == {"PSM", "GCCM"}
    assert set(summary["setting"]) == {"baseline"}
    assert summary["fragility"].isin({"robust", "bounded", "fragile"}).all()

    details = json.loads(expected_files["details_json"].read_text(encoding="utf-8"))
    assert details
    assert {"setting", "stress_level"}.issubset(details[0])


def test_synthetic_benchmark_audit_includes_settings_variants_and_report(tmp_path):
    from data_agent.experiments.synthetic_benchmark_audit import (
        run_synthetic_benchmark_audit,
    )

    manifest = run_synthetic_benchmark_audit(
        output_dir=tmp_path,
        seeds=[0],
        scenario_names=["PSM", "GCCM", "DiD"],
        setting_names=["baseline", "small_sample"],
    )

    summary = pd.read_csv(manifest["summary_csv"])
    scenario_summary = pd.read_csv(manifest["scenario_summary_csv"])
    report = (tmp_path / "synthetic_benchmark_audit_report.md").read_text(
        encoding="utf-8"
    )

    assert {"baseline", "small_sample"}.issubset(set(summary["setting"]))
    assert {"standard", "ols_adjusted"}.issubset(
        set(summary.loc[summary["scenario"] == "PSM", "variant"])
    )
    assert {"standard", "queen"}.issubset(
        set(summary.loc[summary["scenario"] == "GCCM", "variant"])
    )
    assert {"scenario", "n_summary_rows", "n_fragile", "n_robust"}.issubset(
        scenario_summary.columns
    )
    assert set(scenario_summary["scenario"]) == {"PSM", "GCCM", "DiD"}
    assert "Most Fragile Rows" in report
    assert "Strongest Rows" in report
    assert "PSM" in report
    assert "GCCM" in report
