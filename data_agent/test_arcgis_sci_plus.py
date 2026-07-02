import pandas as pd

from data_agent.scca.arcgis_sci_plus import (
    arcgis_quantile_trim,
    build_arcgis_sci_plus_report,
    solve_target_exposure,
)


def test_arcgis_quantile_trim_matches_tail_rule():
    frame = pd.DataFrame({"exposure": list(range(100)), "outcome": list(range(100))})

    trimmed, summary = arcgis_quantile_trim(
        frame, "exposure", lower_q=0.01, upper_q=0.99
    )

    assert len(trimmed) == 98
    assert summary["input_rows"] == 100
    assert summary["trimmed_rows"] == 98
    assert summary["removed_rows"] == 2
    assert summary["lower_quantile"] == 0.99
    assert summary["upper_quantile"] == 98.01


def test_solve_target_exposure_uses_nearest_erf_point():
    erf = pd.DataFrame(
        {
            "exposure": [4.6, 15.0, 34.6],
            "response": [64.1, 67.0, 70.2],
        }
    )

    result = solve_target_exposure(erf, target_response=70.0)

    assert result["status"] == "ok"
    assert result["target_response"] == 70.0
    assert result["target_exposure"] == 34.6
    assert result["target_prediction"] == 70.2


def test_build_arcgis_sci_plus_report_combines_arcgis_and_extra_risk():
    report = build_arcgis_sci_plus_report(
        study="county_social_capital_longevity_validation",
        arcgis_trim_summary={"trimmed_rows": 3044, "removed_rows": 64},
        erf_summary={"range_effect": 6.85, "monotonic_direction": "increasing"},
        target_summary={"status": "ok", "target_exposure": 34.6},
        spatial_risk={"residual_moran": 0.313, "neighbor_exposure_p": 0.001},
        role_risk={"post_treatment_warnings": []},
        scale_risk={"scale_status": "same_support"},
    )

    assert report["study"] == "county_social_capital_longevity_validation"
    assert report["arcgis_sci_parity"]["trimmed_rows"] == 3044
    assert report["geo_causal_extensions"]["spatial_risk"]["residual_moran"] == 0.313
    assert "ArcGIS SCI Plus" in report["claim"]
