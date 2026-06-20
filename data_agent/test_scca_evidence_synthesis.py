import json

import pandas as pd


def test_scca_evidence_synthesis_writes_contract_files(tmp_path):
    from data_agent.experiments.scca_evidence_synthesis import (
        run_scca_evidence_synthesis,
    )

    manifest = run_scca_evidence_synthesis(output_dir=tmp_path)

    expected = {
        "synthesis_csv": tmp_path / "scca_evidence_synthesis.csv",
        "report_md": tmp_path / "scca_evidence_synthesis_report.md",
        "manifest_json": tmp_path / "scca_evidence_synthesis_manifest.json",
    }
    for key, path in expected.items():
        assert manifest[key] == str(path)
        assert path.exists()

    synthesis = pd.read_csv(expected["synthesis_csv"])
    required_columns = {
        "case",
        "data_type",
        "exposure",
        "outcome",
        "context_source",
        "best_adjustment",
        "effect_estimate",
        "balance_status",
        "robustness_status",
        "evidence_grade",
        "limitation",
        "manuscript_use",
    }
    assert required_columns.issubset(synthesis.columns)
    assert {
        "chongqing_uhi",
        "geofm_alphaearth_ablation",
        "snow8",
        "soho",
        "county_social_capital",
    }.issubset(set(synthesis["case"]))
    assert "negative_ablation" in set(synthesis["evidence_grade"])
    assert synthesis.loc[
        synthesis["case"] == "geofm_alphaearth_ablation", "manuscript_use"
    ].str.contains("no clear gain").any()

    payload = json.loads(expected["manifest_json"].read_text(encoding="utf-8"))
    assert payload["n_rows"] == len(synthesis)

