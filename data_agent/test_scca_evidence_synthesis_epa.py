from __future__ import annotations

import json


def test_scca_evidence_synthesis_includes_epa_airdata_when_available(tmp_path):
    from data_agent.experiments.scca_evidence_synthesis import build_scca_evidence_table

    epa_dir = tmp_path / "epa_nonattainment_airdata"
    epa_dir.mkdir(parents=True)
    (epa_dir / "benchmark_summary.json").write_text(
        json.dumps(
            {
                "real_data": {
                    "effect_estimate": -0.42,
                    "evidence_grade": "bounded_support",
                    "grade_rule_ids": ["significant_neighbor_exposure"],
                    "grade_reasons": [
                        "Neighboring exposure remains associated with the outcome."
                    ],
                    "row_count": 1200,
                    "panel_year_min": 2000,
                    "panel_year_max": 2024,
                },
                "semi_synthetic": {
                    "scenario_count": 3,
                    "median_absolute_error": 0.18,
                    "spatial_caution_scenarios": ["spillover"],
                },
            }
        ),
        encoding="utf-8",
    )

    table = build_scca_evidence_table(tmp_path)

    row = table.loc[table["case"] == "epa_nonattainment_airdata"].iloc[0]
    assert row["data_type"] == "public spatiotemporal policy benchmark"
    assert row["evidence_grade"] == "bounded_support"
    assert "policy-structure semi-synthetic coefficient" in row["effect_estimate"]
    assert "real-data coefficient" not in row["effect_estimate"]
    assert "not an observational causal policy estimate" in row["limitation"]
    assert "semi-synthetic known-effect layer" in row["manuscript_use"]
