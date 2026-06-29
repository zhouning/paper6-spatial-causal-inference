from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace


def _write_comparison_manifest(
    tmp_path: Path,
    name: str,
    *,
    arcgis_balance: float,
    geocausal_balance: float,
) -> Path:
    arcgis_run_manifest = tmp_path / f"{name}_arcgis_manifest.json"
    arcgis_run_manifest.write_text(
        json.dumps({"parameters": {"output_stem": name}}),
        encoding="utf-8",
    )
    comparison_manifest = tmp_path / f"{name}_comparison_manifest.json"
    comparison_manifest.write_text(
        json.dumps(
            {
                "arcgis_manifest_path": str(arcgis_run_manifest),
                "metrics": {
                    "arcgis_mean_weighted_correlation": arcgis_balance,
                    "geocausal_arcgis_style_calibrated_confounder_mean_abs_weighted_correlation": geocausal_balance,
                },
            }
        ),
        encoding="utf-8",
    )
    return comparison_manifest


def test_arcgis_runtime_audit_records_tool_metadata_and_manifest_wins(tmp_path):
    from data_agent.experiments.arcgis_runtime_audit import build_arcgis_runtime_audit

    class FakeArcpy:
        def __init__(self) -> None:
            self.stats = SimpleNamespace(CausalInferenceAnalysis=self._causal_inference)

        def GetInstallInfo(self):  # noqa: N802 - mirrors ArcPy
            return {"Version": "3.7"}

        def ProductInfo(self):  # noqa: N802 - mirrors ArcPy
            return "ArcInfo"

        def _causal_inference(self, in_features=None, outcome_field=None):
            """Fake Causal Inference Analysis."""
            return None

    first = _write_comparison_manifest(
        tmp_path,
        "county_arcgis_builtin",
        arcgis_balance=0.0559,
        geocausal_balance=0.0453,
    )
    second = _write_comparison_manifest(
        tmp_path,
        "soho_arcgis_builtin_relaxed",
        arcgis_balance=0.1778,
        geocausal_balance=0.1109,
    )

    audit = build_arcgis_runtime_audit(
        comparison_manifests=[first, second],
        arcpy_module=FakeArcpy(),
    )

    assert audit["runtime_available"] is True
    assert audit["arcgis_version"] == "3.7"
    assert audit["product"] == "ArcInfo"
    assert "outcome_field" in audit["tool_signature"]
    assert audit["n_direct_comparison_manifests"] == 2
    assert audit["n_calibrated_balance_wins"] == 2
    assert audit["comparison_case_ids"] == [
        "county_arcgis_builtin",
        "soho_arcgis_builtin_relaxed",
    ]
