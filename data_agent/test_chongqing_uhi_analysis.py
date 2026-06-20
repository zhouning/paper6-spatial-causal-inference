import json
import importlib.util
import inspect
from pathlib import Path

import pandas as pd


def _uhi_fixture(use_rs_prefix: bool = False) -> pd.DataFrame:
    rows = []
    for idx in range(12):
        treated = 1 if idx < 6 else 0
        suffix = "rs_" if use_rs_prefix else ""
        rows.append(
            {
                "building_id": f"b{idx + 1}",
                "floor": 12 if treated else 6,
                "treatment": treated,
                "LST": 30.0 + 0.3 * treated + 0.1 * idx,
                "centroid_x": 106.30 + 0.01 * idx,
                "centroid_y": 29.30 + 0.005 * idx,
                "area_m2": 80.0 + 5.0 * idx,
                "elevation": 240.0 + 2.0 * idx,
                "slope": 4.0 + 0.2 * idx,
                f"{suffix}B2": 0.12 + 0.001 * idx,
                f"{suffix}B3": 0.13 + 0.001 * idx,
                f"{suffix}B4": 0.14 + 0.001 * idx,
                f"{suffix}B8": 0.20 + 0.001 * idx,
                f"{suffix}B11": 0.24 + 0.001 * idx,
                f"{suffix}B12": 0.26 + 0.001 * idx,
                f"{suffix}NDVI": 0.40 - 0.005 * idx,
                f"{suffix}NDBI": 0.10 + 0.004 * idx,
                f"{suffix}MNDWI": -0.05 + 0.003 * idx,
                f"{suffix}BSI": 0.08 + 0.002 * idx,
            }
        )
    return pd.DataFrame(rows)


def _matched_uhi_fixture() -> pd.DataFrame:
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
            for treated, floor in [(1, treated_floors[pair]), (0, control_floors[pair])]:
                identifier += 1
                lst = 31.0 - 0.004 * elevation + 0.35 * bands["NDBI"] + 0.55 * treated
                rows.append(
                    {
                        "building_id": f"m{identifier}",
                        "floor": floor,
                        "treatment": treated,
                        "LST": lst,
                        "centroid_x": base_x,
                        "centroid_y": base_y,
                        "area_m2": area_m2,
                        "elevation": elevation,
                        "slope": slope,
                        **bands,
                    }
                )
    return pd.DataFrame(rows)


def test_chongqing_feature_specs_and_writer_contract(tmp_path):
    from data_agent.experiments.chongqing_uhi_analysis import (
        FEATURE_SPECS,
        resolve_feature_columns,
        write_chongqing_outputs,
    )

    frame = _uhi_fixture(use_rs_prefix=True)
    required_specs = {
        "raw",
        "coordinates_only",
        "geometry",
        "terrain",
        "sentinel_indices",
        "sentinel_bands",
        "full_rs_context",
        "pca_context",
    }
    assert required_specs.issubset(FEATURE_SPECS)

    resolved = resolve_feature_columns(frame, ["NDVI", "NDBI", "B2", "B12"])
    assert resolved == ["rs_NDVI", "rs_NDBI", "rs_B2", "rs_B12"]

    ablation = pd.DataFrame(
        [
            {"variant": "raw", "att": 0.2, "max_post_smd": None},
            {"variant": "terrain", "att": 0.1, "max_post_smd": 0.08},
        ]
    )
    balance = pd.DataFrame(
        [
            {"variant": "terrain", "covariate": "elevation", "pre_smd": 0.4, "post_smd": 0.08},
        ]
    )
    matched_counts = pd.DataFrame(
        [
            {
                "variant": "terrain",
                "threshold": 10,
                "n_total": 12,
                "n_common_support": 10,
                "matched_treated_n": 5,
                "matched_control_n": 5,
            }
        ]
    )
    bootstrap = pd.DataFrame([{"variant": "terrain", "replicate": 0, "att": 0.1, "status": "ok"}])
    placebos = pd.DataFrame([{"threshold": 8, "variant": "terrain", "att": 0.1}])
    residuals = pd.DataFrame([{"variant": "terrain", "moran_i": 0.02, "permutation_p_value": 0.4}])

    manifest = write_chongqing_outputs(
        output_dir=tmp_path,
        ablation=ablation,
        balance=balance,
        matched_counts=matched_counts,
        bootstrap=bootstrap,
        placebos=placebos,
        residual_diagnostics=residuals,
        metadata={"sample_size": 12, "treatment_threshold": 10},
    )

    expected_files = {
        "ablation_csv": tmp_path / "chongqing_uhi_ablation.csv",
        "balance_csv": tmp_path / "chongqing_uhi_balance.csv",
        "matched_counts_csv": tmp_path / "chongqing_uhi_matched_counts.csv",
        "bootstrap_csv": tmp_path / "chongqing_spatial_bootstrap.csv",
        "placebo_csv": tmp_path / "chongqing_placebo_thresholds.csv",
        "residual_csv": tmp_path / "chongqing_residual_spatial_diagnostics.csv",
        "manifest_json": tmp_path / "chongqing_uhi_analysis_manifest.json",
        "report_md": tmp_path / "chongqing_uhi_analysis_report.md",
    }
    for key, path in expected_files.items():
        assert manifest[key] == str(path)
        assert path.exists()

    saved_manifest = json.loads(expected_files["manifest_json"].read_text(encoding="utf-8"))
    assert saved_manifest["metadata"]["sample_size"] == 12
    assert saved_manifest["metadata"]["treatment_threshold"] == 10


def test_run_psm_ablation_reports_balance_and_counts():
    from data_agent.experiments.chongqing_uhi_analysis import run_psm_ablation

    ablation, balance, matched_counts = run_psm_ablation(
        _matched_uhi_fixture(),
        threshold=10,
        caliper=0.2,
        n_bootstrap=30,
        random_state=0,
    )

    assert {"raw", "coordinates_only", "full_rs_context"}.issubset(set(ablation["variant"]))
    substantive = ablation[ablation["variant"] != "raw"]
    assert {"common_support_n", "matched_treated_n", "matched_control_n", "caliper_abs", "max_post_smd"}.issubset(
        substantive.columns
    )
    assert substantive["matched_treated_n"].gt(0).all()
    assert substantive["matched_control_n"].gt(0).all()
    assert substantive["max_post_smd"].lt(0.1).any()

    assert {"variant", "covariate", "pre_smd", "post_smd", "balance_pass_0_1"}.issubset(balance.columns)
    assert balance["balance_pass_0_1"].any()

    assert {"variant", "threshold", "n_total", "n_common_support", "matched_treated_n", "matched_control_n", "drop_rate"}.issubset(
        matched_counts.columns
    )
    assert matched_counts["drop_rate"].between(0, 1).all()


def test_spatial_robustness_helpers_return_expected_rows():
    from data_agent.experiments.chongqing_uhi_analysis import (
        run_psm_ablation,
        run_residual_spatial_diagnostics,
        run_spatial_block_bootstrap,
        run_threshold_placebos,
    )

    frame = _matched_uhi_fixture()
    ablation, _, _ = run_psm_ablation(
        frame,
        threshold=10,
        caliper=0.2,
        n_bootstrap=20,
        random_state=0,
    )
    placebos = run_threshold_placebos(
        frame,
        thresholds=(8, 10, 12),
        variants=("terrain", "full_rs_context"),
        caliper=0.2,
        n_bootstrap=10,
        random_state=0,
    )
    assert set(placebos["threshold"]) == {8, 10, 12}
    assert {"terrain", "full_rs_context"}.issubset(set(placebos["variant"]))

    bootstrap = run_spatial_block_bootstrap(
        frame,
        variants=("terrain",),
        threshold=10,
        n_replicates=8,
        caliper=0.2,
        random_state=0,
        block_size_m=2000,
    )
    assert len(bootstrap) == 8
    assert {"variant", "replicate", "block_count", "att", "status"}.issubset(bootstrap.columns)

    diagnostics = run_residual_spatial_diagnostics(
        frame,
        variants=("terrain", "full_rs_context"),
        threshold=10,
        caliper=0.2,
        random_state=0,
        n_permutations=20,
    )
    assert {"variant", "moran_i", "permutation_p_value", "n", "distance_band"}.issubset(
        diagnostics.columns
    )
    assert diagnostics["moran_i"].notna().all()
    assert diagnostics["permutation_p_value"].between(0, 1).all()


def test_causal_case_study_script_exposes_wrapper_entrypoint():
    script_path = Path(__file__).resolve().parent.parent / "scripts" / "causal_case_study.py"
    spec = importlib.util.spec_from_file_location("paper6_causal_case_study", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert hasattr(module, "run_chongqing_uhi_case_study")
    signature = inspect.signature(module.run_chongqing_uhi_case_study)
    assert "analysis_sample_csv" in signature.parameters


def test_run_full_analysis_writes_default_bootstrap_variants(tmp_path):
    from data_agent.experiments.chongqing_uhi_analysis import run_chongqing_uhi_analysis

    manifest = run_chongqing_uhi_analysis(
        _matched_uhi_fixture(),
        output_dir=tmp_path,
        n_bootstrap=20,
        n_spatial_bootstrap=6,
        random_state=0,
    )
    bootstrap = pd.read_csv(manifest["bootstrap_csv"])
    assert {"terrain", "full_rs_context"}.issubset(set(bootstrap["variant"]))
