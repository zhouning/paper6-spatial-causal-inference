"""OLS-vs-GBM GPS balance benchmark for ArcGIS replacement evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from geocausal.arcgis_style_matching import arcgis_style_matching_search


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "paper"
    / "ijgis_submission_20260605"
    / "07_results"
    / "arcgis_gps_balance_benchmark"
)
OUTPUT_CSV = "arcgis_gps_balance_benchmark.csv"
OUTPUT_JSON = "arcgis_gps_balance_benchmark.json"


def nonlinear_gps_fixture(seed: int = 0, n: int = 220) -> pd.DataFrame:
    """Return a deterministic fixture where exposure assignment is nonlinear in confounders."""

    rng = np.random.default_rng(seed)
    confounder_a = rng.uniform(-3.0, 3.0, n)
    confounder_b = rng.uniform(-3.0, 3.0, n)
    exposure = (
        np.where(confounder_a * confounder_b > 0.0, 2.0, -2.0)
        + 0.3 * confounder_a
        + rng.normal(0.0, 0.2, n)
    )
    outcome = 5.0 + 0.7 * exposure + 0.8 * confounder_a - 0.4 * confounder_b
    return pd.DataFrame(
        {
            "unit_id": [f"nl{i:03d}" for i in range(n)],
            "exposure": exposure,
            "outcome": outcome,
            "confounder_a": confounder_a,
            "confounder_b": confounder_b,
        }
    )


def _balance_metrics(result: Any, method: str) -> dict[str, Any]:
    abs_values = pd.to_numeric(
        result.balance_summary.get("absolute_weighted_correlation", pd.Series(dtype=float)),
        errors="coerce",
    ).replace([np.inf, -np.inf], np.nan).dropna()
    mean_value = float(abs_values.mean()) if not abs_values.empty else np.nan
    median_value = float(abs_values.median()) if not abs_values.empty else np.nan
    max_value = float(abs_values.max()) if not abs_values.empty else np.nan
    return {
        "gps_method": method,
        "selected_gps_method": result.selected_gps_method,
        "selected_num_bins": result.selected_num_bins,
        "selected_scale": result.selected_scale,
        "mean_abs_weighted_correlation": mean_value,
        "median_abs_weighted_correlation": median_value,
        "max_abs_weighted_correlation": max_value,
        "balanced_at_0_1": bool(not abs_values.empty and max_value <= 0.1),
        "nonzero_weight_n": int((result.weights > 0).sum()),
        "candidate_count": int(len(result.grid)),
    }


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        return numeric if np.isfinite(numeric) else None
    return value


def build_arcgis_gps_balance_benchmark() -> pd.DataFrame:
    frame = nonlinear_gps_fixture()
    search_kwargs = {
        "exposure": "exposure",
        "confounders": ("confounder_a", "confounder_b"),
        "num_bins": (4, 6, 8, 10),
        "scales": (0.5, 0.8, 1.0),
    }
    rows: list[dict[str, Any]] = []
    for method in ("ols", "gbm"):
        result = arcgis_style_matching_search(frame, **search_kwargs, gps_methods=(method,))
        rows.append(_balance_metrics(result, method))
    return pd.DataFrame(rows)


def write_arcgis_gps_balance_benchmark(*, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    benchmark = build_arcgis_gps_balance_benchmark()
    csv_path = target / OUTPUT_CSV
    json_path = target / OUTPUT_JSON
    benchmark.to_csv(csv_path, index=False)

    ols = benchmark.loc[benchmark["gps_method"] == "ols"].iloc[0]
    gbm = benchmark.loc[benchmark["gps_method"] == "gbm"].iloc[0]
    gbm_beats_ols = bool(
        float(gbm["mean_abs_weighted_correlation"])
        < float(ols["mean_abs_weighted_correlation"])
    )
    selected_method = "gbm" if gbm_beats_ols else "ols"
    manifest: dict[str, Any] = {
        "benchmark_csv": str(csv_path),
        "manifest_json": str(json_path),
        "benchmark_role": "nonlinear_gps_balance_positive_control",
        "row_count": int(nonlinear_gps_fixture().shape[0]),
        "candidate_count": int(len(benchmark)),
        "selected_gps_method": selected_method,
        "gbm_beats_ols": gbm_beats_ols,
        "ols_mean_abs_weighted_correlation": float(ols["mean_abs_weighted_correlation"]),
        "gbm_mean_abs_weighted_correlation": float(gbm["mean_abs_weighted_correlation"]),
        "ols_max_abs_weighted_correlation": float(ols["max_abs_weighted_correlation"]),
        "gbm_max_abs_weighted_correlation": float(gbm["max_abs_weighted_correlation"]),
    }
    json_path.write_text(json.dumps(_json_ready(manifest), indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the ArcGIS GPS balance benchmark.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    manifest = write_arcgis_gps_balance_benchmark(output_dir=args.output_dir)
    print(json.dumps(_json_ready(manifest), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
