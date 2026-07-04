import pytest
import pandas as pd

from data_agent.scca.arcgis_sci_plus import (
    arcgis_documented_causal_analysis,
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


def test_arcgis_quantile_trim_missing_exposure_returns_skipped():
    frame = pd.DataFrame({"outcome": [1, 2, 3]})

    trimmed, summary = arcgis_quantile_trim(frame, "exposure")

    assert trimmed.empty
    assert list(trimmed.columns) == ["outcome"]
    assert summary["status"] == "skipped"
    assert summary["input_rows"] == 3
    assert summary["trimmed_rows"] == 0
    assert summary["removed_rows"] == 3
    assert summary["lower_q"] == 0.01
    assert summary["upper_q"] == 0.99
    assert summary["lower_quantile"] is None
    assert summary["upper_quantile"] is None
    assert any("missing exposure" in warning for warning in summary["warnings"])


def test_arcgis_quantile_trim_rejects_invalid_quantile_order():
    frame = pd.DataFrame({"exposure": [1, 2, 3]})

    with pytest.raises(ValueError, match="lower_q must be <= upper_q"):
        arcgis_quantile_trim(frame, "exposure", lower_q=0.8, upper_q=0.2)


def test_arcgis_quantile_trim_all_nan_returns_skipped():
    frame = pd.DataFrame(
        {"exposure": [float("nan"), None, "bad"], "outcome": [1, 2, 3]}
    )

    trimmed, summary = arcgis_quantile_trim(frame, "exposure")

    assert trimmed.empty
    assert list(trimmed.columns) == ["exposure", "outcome"]
    assert summary["status"] == "skipped"
    assert summary["input_rows"] == 3
    assert summary["trimmed_rows"] == 0
    assert summary["removed_rows"] == 3
    assert summary["lower_quantile"] is None
    assert summary["upper_quantile"] is None
    assert any("no finite" in warning for warning in summary["warnings"])


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


def test_solve_target_exposure_warns_when_target_outside_erf_response_range():
    erf = pd.DataFrame(
        {
            "exposure": [1.8, 15.0, 38.0],
            "response": [74.3, 77.0, 81.1],
        }
    )

    result = solve_target_exposure(erf, target_response=70.0)

    assert result["status"] == "ok"
    assert result["target_within_response_range"] is False
    assert result["response_min"] == 74.3
    assert result["response_max"] == 81.1
    assert result["target_exposure"] == 1.8
    assert any(
        "outside the ERF response range" in warning
        for warning in result["warnings"]
    )


def test_solve_target_exposure_skips_nonfinite_target_response():
    erf = pd.DataFrame({"exposure": [1.0, 2.0], "response": [3.0, 4.0]})

    result = solve_target_exposure(erf, target_response=float("nan"))

    assert result["status"] == "skipped"
    assert result["target_response"] is None
    assert result["target_exposure"] is None
    assert result["target_prediction"] is None
    assert any("finite target_response" in warning for warning in result["warnings"])


def test_solve_target_exposure_skips_missing_erf_columns():
    erf = pd.DataFrame({"exposure": [1.0, 2.0]})

    result = solve_target_exposure(erf, target_response=3.0)

    assert result["status"] == "skipped"
    assert result["target_response"] == 3.0
    assert result["target_exposure"] is None
    assert result["target_prediction"] is None
    assert any("missing column" in warning for warning in result["warnings"])


def test_solve_target_exposure_skips_all_nonfinite_erf_rows():
    erf = pd.DataFrame(
        {"exposure": [float("nan"), "bad"], "response": [float("inf"), None]}
    )

    result = solve_target_exposure(erf, target_response=3.0)

    assert result["status"] == "skipped"
    assert result["target_response"] == 3.0
    assert result["target_exposure"] is None
    assert result["target_prediction"] is None
    assert any("no finite" in warning for warning in result["warnings"])


def test_solve_target_exposure_breaks_ties_by_smallest_exposure_with_warning():
    erf = pd.DataFrame(
        {
            "exposure": [20.0, 10.0, 30.0],
            "response": [68.0, 72.0, 72.0],
        }
    )

    result = solve_target_exposure(erf, target_response=70.0)

    assert result["status"] == "ok"
    assert result["target_exposure"] == 10.0
    assert result["target_prediction"] == 72.0
    assert result["tie_count"] == 3
    assert any("tie" in warning for warning in result["warnings"])


def test_arcgis_documented_causal_analysis_builds_matching_erf_and_balance():
    frame = pd.DataFrame(
        {
            "exposure": [float(i) for i in range(3, 63)],
            "outcome": [70.0 + 0.2 * i + 0.03 * (i % 5) for i in range(3, 63)],
            "x1": [0.5 * i + (i % 4) for i in range(3, 63)],
            "x2": [10.0 + (i % 7) for i in range(3, 63)],
        }
    )

    result = arcgis_documented_causal_analysis(
        frame,
        exposure="exposure",
        outcome="outcome",
        confounders=["x1", "x2"],
        balance_threshold=0.1,
    )

    assert result["status"] == "ok"
    assert result["matching_summary"]["ps_method"] == "REGRESSION"
    assert result["matching_summary"]["balancing_method"] == "MATCHING"
    assert result["matching_summary"]["selected_num_bins"] >= 2
    assert result["matching_summary"]["selected_scale"] in {
        0.0,
        0.2,
        0.4,
        0.6,
        0.8,
        1.0,
    }
    assert result["matching_summary"]["weight_sum"] == len(frame) * result["matching_summary"]["selected_num_bins"]
    assert result["erf_summary"]["n_grid"] == 200
    assert len(result["erf_curve"]) == 200
    assert result["balance_summary"]["aggregate_weighted_correlation"] >= 0.0
    assert {
        "variable",
        "original_correlation",
        "weighted_correlation",
    }.issubset(result["balance_table"].columns)

def test_build_arcgis_sci_plus_report_combines_arcgis_and_extra_risk():
    report = build_arcgis_sci_plus_report(
        study="county_social_capital_longevity_validation",
        arcgis_trim_summary={"trimmed_rows": 3044, "removed_rows": 64},
        erf_summary={"range_effect": 6.85, "monotonic_direction": "increasing"},
        target_summary={"status": "ok", "target_exposure": 34.6},
        spatial_risk={"residual_moran": 0.313, "neighbor_exposure_p": 0.001},
        role_risk={"post_treatment_warnings": []},
        scale_risk={"scale_status": "same_support"},
        bias_bound={
            "status": "ok",
            "bias_bound": 0.08,
            "bias_bound_ratio": 0.12,
        },
        data_provenance={
            "status": "ok",
            "file": "county_variable_provenance.csv",
            "field_count": 18,
            "unresolved_fields": ["UnemployRate"],
        },
    )

    assert report["study"] == "county_social_capital_longevity_validation"
    assert report["arcgis_sci_parity"]["trimmed_rows"] == 3044
    assert report["geo_causal_extensions"]["spatial_risk"]["residual_moran"] == 0.313
    assert report["geo_causal_extensions"]["bias_bound"]["bias_bound"] == 0.08
    assert report["data_provenance"]["file"] == "county_variable_provenance.csv"
    assert report["data_provenance"]["unresolved_fields"] == ["UnemployRate"]
    assert report["replacement_assessment"]["arcgis_platform_replacement"] is False
    assert report["replacement_assessment"]["causal_inference_task_replacement"] == "tested_algorithmic_replacement"
    assert report["replacement_assessment"]["supported_arcgis_mode"] == (
        "Continuous exposure/outcome with REGRESSION propensity scores, "
        "MATCHING balance, ArcGIS-style quantile trimming, and weighted "
        "kernel ERF outputs."
    )
    assert "ArcGIS SCI Plus" in report["claim"]
    assert "implements the documented ArcGIS continuous-exposure" in report["claim"]
