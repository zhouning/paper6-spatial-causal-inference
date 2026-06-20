from __future__ import annotations

import importlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROVIDER_PATH = REPO_ROOT / "qgis_provider" / "geocausal_scca_algorithm.py"


def test_qgis_provider_skeleton_exists_and_avoids_case_specific_fields():
    text = PROVIDER_PATH.read_text(encoding="utf-8")
    assert "AnalysisRequest" in text
    assert "build_analysis_joined_table" in text
    assert "run_scca_analysis" in text
    assert "SocialAssoc" not in text
    assert "AveAgeDeath" not in text
    assert "STATE_NAME" not in text
    assert "CountyData" not in text


def test_qgis_provider_skeleton_imports_without_qgis_runtime():
    module = importlib.import_module("qgis_provider.geocausal_scca_algorithm")

    assert hasattr(module, "GeoCausalSCCAAlgorithm")
    assert module.GeoCausalSCCAAlgorithm.PARAM_EXPOSURE == "EXPOSURE_FIELD"
    assert module.GeoCausalSCCAAlgorithm.PARAM_OUTCOME == "OUTCOME_FIELD"
    assert module.GeoCausalSCCAAlgorithm.PARAM_OUTPUT_JOINED == "OUTPUT_ANALYSIS_TABLE"
