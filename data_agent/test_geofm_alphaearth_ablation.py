import json
from pathlib import Path

import numpy as np
import pandas as pd


def _phase0_fixture(path: Path) -> Path:
    payload = {
        "verdict": {
            "overall": "PASS",
            "recommendation": "Phase 0 supports bounded AlphaEarth feasibility.",
            "criteria": {
                "interannual_signal": {"avg_cosine_similarity": 0.953},
                "change_separation": {"avg_separation_ratio": 2.44},
                "decodability": {"avg_accuracy": 0.837},
            },
        }
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _geofm_fixture(column_style: str = "A") -> pd.DataFrame:
    rows = []
    identifier = 0
    treated_floors = [10, 11, 12, 13]
    control_floors = [6, 7, 8, 9]
    for block in range(8):
        for pair in range(4):
            base_x = 106.30 + 0.015 * block + 0.001 * pair
            base_y = 29.30 + 0.010 * block + 0.0015 * pair
            area_m2 = 90.0 + 3.0 * block + 2.0 * pair
            elevation = 220.0 + 7.0 * block + 1.5 * pair
            slope = 4.0 + 0.3 * pair
            bands = {
                "B2": 0.12 + 0.002 * block + 0.0005 * pair,
                "B3": 0.14 + 0.002 * block + 0.0005 * pair,
                "B4": 0.16 + 0.002 * block + 0.0005 * pair,
                "B8": 0.20 + 0.001 * block + 0.0004 * pair,
                "B11": 0.24 + 0.001 * block + 0.0004 * pair,
                "B12": 0.28 + 0.001 * block + 0.0004 * pair,
                "NDVI": 0.48 - 0.010 * block + 0.001 * pair,
                "NDBI": 0.08 + 0.005 * block + 0.001 * pair,
                "MNDWI": -0.04 + 0.002 * block + 0.001 * pair,
                "BSI": 0.06 + 0.003 * block + 0.001 * pair,
            }
            geofm = {}
            for dim in range(64):
                value = (
                    0.01 * dim
                    + 0.003 * block
                    + 0.0007 * pair
                    + 0.002 * np.sin(dim / 7.0)
                )
                if column_style == "A":
                    key = f"A{dim:02d}"
                elif column_style == "geofm_unpadded":
                    key = f"geofm_{dim}"
                else:
                    key = f"geofm_{dim:02d}"
                geofm[key] = value
            for treated, floor in [(1, treated_floors[pair]), (0, control_floors[pair])]:
                identifier += 1
                lst = 31.0 - 0.004 * elevation + 0.35 * bands["NDBI"] + 0.55 * treated
                rows.append(
                    {
                        "building_id": f"g{identifier}",
                        "floor": floor,
                        "treatment": treated,
                        "LST": lst,
                        "centroid_x": base_x,
                        "centroid_y": base_y,
                        "area_m2": area_m2,
                        "elevation": elevation,
                        "slope": slope,
                        **bands,
                        **geofm,
                    }
                )
    return pd.DataFrame(rows)


def test_resolve_geofm_columns_accepts_multiple_naming_schemes():
    from data_agent.experiments.geofm_alphaearth_ablation import resolve_geofm_columns

    a_columns = resolve_geofm_columns(_geofm_fixture("A"))
    assert a_columns[0] == "A00"
    assert a_columns[-1] == "A63"

    unpadded = resolve_geofm_columns(_geofm_fixture("geofm_unpadded"))
    assert unpadded[0] == "geofm_0"
    assert unpadded[-1] == "geofm_63"


def test_run_geofm_analysis_writes_contract_files(tmp_path):
    from data_agent.experiments.geofm_alphaearth_ablation import (
        run_geofm_alphaearth_analysis,
    )

    phase0_path = _phase0_fixture(tmp_path / "phase0_results.json")
    manifest = run_geofm_alphaearth_analysis(
        frame=_geofm_fixture("A"),
        output_dir=tmp_path,
        phase0_report_path=phase0_path,
        coverage_loader=lambda: {"total_embeddings": 123, "areas": [{"name": "yangtze_delta"}]},
        attempt_gee_sampling=False,
        probe_runtime=False,
        n_bootstrap=30,
        random_state=0,
    )

    expected_files = {
        "availability_report_json": tmp_path / "geofm_availability_report.json",
        "causal_ablation_csv": tmp_path / "geofm_causal_ablation.csv",
        "balance_diagnostics_csv": tmp_path / "geofm_balance_diagnostics.csv",
        "manifest_json": tmp_path / "geofm_alphaearth_ablation_manifest.json",
        "report_md": tmp_path / "geofm_alphaearth_ablation_report.md",
        "analysis_sample_csv": tmp_path / "geofm_alphaearth_analysis_sample.csv",
    }
    for key, path in expected_files.items():
        assert manifest[key] == str(path)
        assert path.exists()

    ablation = pd.read_csv(expected_files["causal_ablation_csv"])
    assert {
        "geometry_only",
        "geometry_rs_context",
        "geometry_alphaearth_64d",
        "geometry_rs_alphaearth_64d",
        "geometry_alphaearth_pca",
        "geometry_rs_alphaearth_pca",
    }.issubset(set(ablation["variant"]))
    assert {"att", "ci_lower", "ci_upper", "max_post_smd", "matched_treated_n"}.issubset(
        ablation.columns
    )

    balance = pd.read_csv(expected_files["balance_diagnostics_csv"])
    assert {"variant", "covariate", "pre_smd", "post_smd", "balance_pass_0_1"}.issubset(
        balance.columns
    )

    availability = json.loads(expected_files["availability_report_json"].read_text(encoding="utf-8"))
    assert availability["phase0_validation"]["available"] is True
    assert availability["input_geofm_columns"]["available"] is True
    assert availability["embedding_store_coverage"]["total_embeddings"] == 123


def test_missing_geofm_columns_keep_observed_variants_and_skip_geofm():
    from data_agent.experiments.geofm_alphaearth_ablation import run_geofm_causal_ablation

    frame = _geofm_fixture("A").drop(columns=[f"A{idx:02d}" for idx in range(64)])
    ablation, balance = run_geofm_causal_ablation(
        frame,
        threshold=10,
        caliper=0.2,
        n_bootstrap=20,
        random_state=0,
    )

    statuses = dict(zip(ablation["variant"], ablation["status"]))
    assert statuses["geometry_only"] == "ok"
    assert statuses["geometry_rs_context"] == "ok"
    assert statuses["geometry_alphaearth_64d"].startswith("skipped")
    assert statuses["geometry_rs_alphaearth_64d"].startswith("skipped")
    assert statuses["geometry_alphaearth_pca"].startswith("skipped")
    assert statuses["geometry_rs_alphaearth_pca"].startswith("skipped")

    assert {"geometry_only", "geometry_rs_context"}.issubset(set(balance["variant"]))


def test_analysis_can_attach_geofm_columns_from_injected_sampler(tmp_path):
    from data_agent.experiments.geofm_alphaearth_ablation import (
        run_geofm_alphaearth_analysis,
    )

    base = _geofm_fixture("A").drop(columns=[f"A{idx:02d}" for idx in range(64)])

    def sampler(frame, *, year, random_state):
        attached = pd.DataFrame(index=frame.index)
        for dim in range(64):
            attached[f"A{dim:02d}"] = 0.01 * dim + 0.001 * np.arange(len(frame))
        return attached, {"status": "ok", "year": year, "n_rows": len(frame)}

    manifest = run_geofm_alphaearth_analysis(
        frame=base,
        output_dir=tmp_path,
        geofm_sampler=sampler,
        attempt_gee_sampling=True,
        probe_runtime=False,
        n_bootstrap=20,
        random_state=0,
    )

    ablation = pd.read_csv(manifest["causal_ablation_csv"])
    statuses = dict(zip(ablation["variant"], ablation["status"]))
    assert statuses["geometry_alphaearth_64d"] == "ok"

    availability = json.loads(
        Path(manifest["availability_report_json"]).read_text(encoding="utf-8")
    )
    assert availability["runtime_sampling"]["status"] == "ok"
    assert availability["input_geofm_columns"]["n_columns"] == 64
