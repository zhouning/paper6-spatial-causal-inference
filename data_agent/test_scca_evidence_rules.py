import json


def test_assess_scca_evidence_grade_requires_all_strong_checks_for_core_support():
    from data_agent.scca.evidence_rules import assess_scca_evidence_grade

    assessment = assess_scca_evidence_grade(
        credibility_decision="strong_support",
        robustness_interpretation="robust_support",
        spatial_summary={
            "residual_moran_i": 0.12,
            "residual_moran_p_value": 0.20,
            "neighbor_exposure_p_value": 0.20,
            "neighbor_adjusted_relative_change_max": 0.12,
            "neighbor_adjusted_sign_stability": True,
        },
    )

    assert assessment["evidence_grade"] == "core_support"
    assert assessment["material_spatial_caution"] is False
    assert assessment["triggered_rules"] == []


def test_assess_scca_evidence_grade_downgrades_material_residual_moran():
    from data_agent.scca.evidence_rules import assess_scca_evidence_grade

    assessment = assess_scca_evidence_grade(
        credibility_decision="strong_support",
        robustness_interpretation="robust_support",
        spatial_summary={
            "residual_moran_i": 0.313,
            "residual_moran_p_value": 0.01,
            "neighbor_exposure_p_value": 0.20,
            "neighbor_adjusted_relative_change_max": 0.12,
            "neighbor_adjusted_sign_stability": True,
        },
    )

    assert assessment["evidence_grade"] == "bounded_support"
    assert assessment["material_spatial_caution"] is True
    assert "material_residual_moran" in assessment["triggered_rules"]


def test_assess_scca_evidence_grade_reports_balance_and_overlap_rules():
    from data_agent.scca.evidence_rules import assess_scca_evidence_grade

    assessment = assess_scca_evidence_grade(
        credibility_decision="moderate_support",
        robustness_interpretation="bounded_support",
        max_balance_corr=0.62,
        overlap_boundary_mass=0.33,
    )

    assert assessment["evidence_grade"] == "bounded_support"
    assert "high_exposure_balance_correlation" in assessment["triggered_rules"]
    assert "high_overlap_boundary_mass" in assessment["triggered_rules"]


def test_write_evidence_rule_outputs_creates_json_and_markdown(tmp_path):
    from data_agent.scca.evidence_rules import write_evidence_rule_outputs

    manifest = write_evidence_rule_outputs(tmp_path)

    json_path = tmp_path / "scca_evidence_grade_rules.json"
    md_path = tmp_path / "scca_evidence_grade_rules.md"
    assert manifest["rules_json"] == str(json_path)
    assert manifest["rules_md"] == str(md_path)
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["rule_version"]
    assert any(rule["rule_id"] == "material_residual_moran" for rule in payload["rules"])
    assert "core_support" in md_path.read_text(encoding="utf-8")
