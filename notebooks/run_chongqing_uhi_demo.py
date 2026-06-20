from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data_agent.experiments.chongqing_uhi_analysis import run_chongqing_uhi_analysis


OUTPUT_DIR = (
    REPO_ROOT
    / "paper"
    / "ijgis_submission_20260605"
    / "07_results"
    / "examples"
    / "chongqing_uhi_notebook_demo"
)
INPUT_CSV = (
    REPO_ROOT
    / "paper"
    / "ijgis_submission_20260605"
    / "07_results"
    / "chongqing_uhi_analysis_sample.csv"
)
CASE_NAME = "chongqing_uhi_notebook_demo"


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    return value


def _read_manifest_csv(manifest: dict[str, Any], key: str) -> pd.DataFrame:
    path = Path(str(manifest[key]))
    return pd.read_csv(path)


def _build_analysis_points(frame: pd.DataFrame, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "chongqing_uhi_points.csv"
    selected_columns = [
        "Id",
        "floor",
        "treatment",
        "centroid_x",
        "centroid_y",
        "area_m2",
        "LST",
        "rs_NDVI",
        "rs_NDBI",
        "rs_MNDWI",
        "rs_BSI",
        "rs_elevation",
        "rs_slope",
    ]
    available = [column for column in selected_columns if column in frame.columns]
    points = frame.loc[:, available].copy()
    points["high_rise_threshold"] = (pd.to_numeric(points["floor"], errors="coerce") >= 10).astype(int)
    points.to_csv(csv_path, index=False)

    outputs: dict[str, Any] = {
        "points_csv": str(csv_path),
        "point_count": int(len(points)),
    }
    try:
        import geopandas as gpd

        geometry = gpd.points_from_xy(points["centroid_x"], points["centroid_y"], crs="EPSG:4326")
        gdf = gpd.GeoDataFrame(points, geometry=geometry)
        gpkg_path = output_dir / "chongqing_uhi_points.gpkg"
        geojson_path = output_dir / "chongqing_uhi_points.geojson"
        gdf.to_file(gpkg_path, layer="chongqing_uhi_points", driver="GPKG")
        gdf.to_file(geojson_path, driver="GeoJSON")
        outputs.update(
            {
                "gpkg": str(gpkg_path),
                "geojson": str(geojson_path),
            }
        )
    except Exception as exc:
        outputs["spatial_output_warning"] = str(exc)
    return outputs


def _write_visualizations(
    *,
    frame: pd.DataFrame,
    ablation: pd.DataFrame,
    balance: pd.DataFrame,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, str] = {}

    import matplotlib.pyplot as plt

    valid_ablation = ablation.loc[ablation.get("status", "ok").astype(str) == "ok"].copy()
    valid_ablation["att"] = pd.to_numeric(valid_ablation["att"], errors="coerce")
    valid_ablation["ci_lower"] = pd.to_numeric(valid_ablation["ci_lower"], errors="coerce")
    valid_ablation["ci_upper"] = pd.to_numeric(valid_ablation["ci_upper"], errors="coerce")
    valid_ablation = valid_ablation.dropna(subset=["att"])
    if not valid_ablation.empty:
        fig, ax = plt.subplots(figsize=(9, 4.8))
        x = list(range(len(valid_ablation)))
        att = pd.to_numeric(valid_ablation["att"], errors="coerce").to_numpy(dtype=float)
        ci_lower = pd.to_numeric(valid_ablation["ci_lower"], errors="coerce").to_numpy(dtype=float)
        ci_upper = pd.to_numeric(valid_ablation["ci_upper"], errors="coerce").to_numpy(dtype=float)
        yerr = [
            pd.Series(att - ci_lower).clip(lower=0).to_numpy(dtype=float),
            pd.Series(ci_upper - att).clip(lower=0).to_numpy(dtype=float),
        ]
        ax.errorbar(x, att, yerr=yerr, fmt="o", capsize=4, color="#2F5D8C")
        ax.axhline(0, color="#777777", linewidth=1)
        ax.set_xticks(list(x))
        ax.set_xticklabels(valid_ablation["variant"], rotation=35, ha="right")
        ax.set_ylabel("ATT (deg C)")
        ax.set_title("Chongqing UHI SCCA Adjustment Variants")
        fig.tight_layout()
        path = output_dir / "chongqing_uhi_att_variants.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)
        outputs["att_variants_png"] = str(path)

    balance_plot = balance.copy()
    balance_plot["post_smd"] = pd.to_numeric(balance_plot.get("post_smd"), errors="coerce")
    balance_plot = balance_plot.dropna(subset=["post_smd"])
    if not balance_plot.empty:
        summary = balance_plot.groupby("variant", as_index=False)["post_smd"].max()
        fig, ax = plt.subplots(figsize=(9, 4.8))
        ax.bar(summary["variant"], summary["post_smd"], color="#577A4D")
        ax.axhline(0.1, color="#9A3E3E", linewidth=1.2, linestyle="--")
        ax.set_ylabel("Max post-match absolute SMD")
        ax.set_title("Post-Match Balance by Adjustment Variant")
        ax.tick_params(axis="x", rotation=35)
        fig.tight_layout()
        path = output_dir / "chongqing_uhi_balance.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)
        outputs["balance_png"] = str(path)

    if {"centroid_x", "centroid_y", "LST", "treatment"}.issubset(frame.columns):
        sample = frame.sample(n=min(len(frame), 2500), random_state=0)
        fig, ax = plt.subplots(figsize=(7, 6))
        scatter = ax.scatter(
            sample["centroid_x"],
            sample["centroid_y"],
            c=sample["LST"],
            s=8,
            cmap="inferno",
            alpha=0.72,
            linewidths=0,
        )
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_title("Sampled Building LST")
        fig.colorbar(scatter, ax=ax, label="LST (deg C)")
        fig.tight_layout()
        path = output_dir / "chongqing_uhi_lst_points.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)
        outputs["lst_points_png"] = str(path)

    try:
        import folium
        import branca.colormap as cm

        sample = frame.sample(n=min(len(frame), 2500), random_state=1).copy()
        center = [float(sample["centroid_y"].mean()), float(sample["centroid_x"].mean())]
        fmap = folium.Map(location=center, zoom_start=10, tiles="CartoDB positron")
        lst_min = float(sample["LST"].min())
        lst_max = float(sample["LST"].max())
        colormap = cm.linear.YlOrRd_09.scale(lst_min, lst_max)
        colormap.caption = "LST (deg C)"
        for _, row in sample.iterrows():
            folium.CircleMarker(
                location=[float(row["centroid_y"]), float(row["centroid_x"])],
                radius=2.0,
                color=colormap(float(row["LST"])),
                fill=True,
                fill_color=colormap(float(row["LST"])),
                fill_opacity=0.75,
                weight=0,
                tooltip=(
                    f"LST={float(row['LST']):.2f}; "
                    f"floor={float(row['floor']):.0f}; "
                    f"treatment={int(row['treatment'])}"
                ),
            ).add_to(fmap)
        colormap.add_to(fmap)
        path = output_dir / "chongqing_uhi_lst_points.html"
        fmap.save(path)
        outputs["lst_points_html"] = str(path)
    except Exception as exc:
        outputs["interactive_map_warning"] = str(exc)

    return outputs


def _write_notebook_summary(
    *,
    output_dir: Path,
    ablation: pd.DataFrame,
    residuals: pd.DataFrame,
    manifest: dict[str, Any],
    visualization_manifest: dict[str, str],
    spatial_manifest: dict[str, Any],
) -> Path:
    full = ablation.loc[ablation["variant"] == "full_rs_context"].head(1)
    raw = ablation.loc[ablation["variant"] == "raw"].head(1)
    residual = residuals.loc[residuals["variant"] == "full_rs_context"].head(1)

    def value(row: pd.DataFrame, column: str, default: str = "NA") -> str:
        if row.empty or column not in row:
            return default
        item = row.iloc[0][column]
        return "NA" if pd.isna(item) else str(item)

    lines = [
        "# Chongqing UHI Notebook Demo Summary",
        "",
        f"- Case: `{CASE_NAME}`",
        f"- Input rows: `{manifest.get('metadata', {}).get('sample_size', 'unknown')}`",
        f"- Treatment threshold: `{manifest.get('metadata', {}).get('treatment_threshold', 'unknown')}` floors",
        f"- Raw difference ATT: `{value(raw, 'att')}`",
        f"- Full RS context ATT: `{value(full, 'att')}`",
        f"- Full RS context 95% CI: `[{value(full, 'ci_lower')}, {value(full, 'ci_upper')}]`",
        f"- Full RS context max post-match SMD: `{value(full, 'max_post_smd')}`",
        f"- Full RS residual Moran I: `{value(residual, 'moran_i')}`",
        f"- Full RS residual Moran p-value: `{value(residual, 'permutation_p_value')}`",
        "",
        "## Files",
        "",
        f"- Analysis report: `{manifest.get('report_md')}`",
        f"- Points CSV: `{spatial_manifest.get('points_csv')}`",
        f"- GeoPackage: `{spatial_manifest.get('gpkg', 'not written')}`",
        f"- GeoJSON: `{spatial_manifest.get('geojson', 'not written')}`",
        f"- ATT plot: `{visualization_manifest.get('att_variants_png', 'not written')}`",
        f"- Balance plot: `{visualization_manifest.get('balance_png', 'not written')}`",
        f"- LST map PNG: `{visualization_manifest.get('lst_points_png', 'not written')}`",
        f"- LST map HTML: `{visualization_manifest.get('lst_points_html', 'not written')}`",
        "",
    ]
    path = output_dir / "notebook_result_summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_demo(
    output_dir: Path = OUTPUT_DIR,
    *,
    input_csv: Path = INPUT_CSV,
    n_bootstrap: int = 200,
    n_spatial_bootstrap: int = 200,
    random_state: int = 0,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    input_csv = Path(input_csv)
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(input_csv)

    analysis_manifest = run_chongqing_uhi_analysis(
        frame,
        output_dir=output_dir,
        n_bootstrap=n_bootstrap,
        n_spatial_bootstrap=n_spatial_bootstrap,
        random_state=random_state,
        metadata={
            "case_name": CASE_NAME,
            "input_csv": str(input_csv),
            "notebook_runner": "notebooks/run_chongqing_uhi_demo.py",
        },
    )
    ablation = _read_manifest_csv(analysis_manifest, "ablation_csv")
    balance = _read_manifest_csv(analysis_manifest, "balance_csv")
    matched_counts = _read_manifest_csv(analysis_manifest, "matched_counts_csv")
    bootstrap = _read_manifest_csv(analysis_manifest, "bootstrap_csv")
    placebos = _read_manifest_csv(analysis_manifest, "placebo_csv")
    residuals = _read_manifest_csv(analysis_manifest, "residual_csv")

    spatial_manifest = _build_analysis_points(frame, output_dir / "spatial_outputs")
    visualization_manifest = _write_visualizations(
        frame=frame,
        ablation=ablation,
        balance=balance,
        output_dir=output_dir / "visualizations",
    )
    notebook_summary_path = _write_notebook_summary(
        output_dir=output_dir,
        ablation=ablation,
        residuals=residuals,
        manifest=analysis_manifest,
        visualization_manifest=visualization_manifest,
        spatial_manifest=spatial_manifest,
    )

    full = ablation.loc[ablation["variant"] == "full_rs_context"].head(1)
    raw = ablation.loc[ablation["variant"] == "raw"].head(1)
    result_summary = {
        "row_count": int(len(frame)),
        "treatment_count": int(pd.to_numeric(frame["treatment"], errors="coerce").sum()),
        "control_count": int((pd.to_numeric(frame["treatment"], errors="coerce") == 0).sum()),
        "raw_att": None if raw.empty else float(raw.iloc[0]["att"]),
        "full_rs_context_att": None if full.empty else float(full.iloc[0]["att"]),
        "full_rs_context_ci_lower": None if full.empty else float(full.iloc[0]["ci_lower"]),
        "full_rs_context_ci_upper": None if full.empty else float(full.iloc[0]["ci_upper"]),
        "full_rs_context_max_post_smd": None if full.empty else float(full.iloc[0]["max_post_smd"]),
        "balance_interpretation": analysis_manifest.get("balance_interpretation"),
        "ablation_rows": int(len(ablation)),
        "balance_rows": int(len(balance)),
        "matched_count_rows": int(len(matched_counts)),
        "bootstrap_rows": int(len(bootstrap)),
        "placebo_rows": int(len(placebos)),
        "residual_rows": int(len(residuals)),
    }

    summary = {
        "case_name": CASE_NAME,
        "output_dir": str(output_dir),
        "input_csv": str(input_csv),
        "analysis_manifest": analysis_manifest,
        "result_summary": result_summary,
        "narrative_summary_markdown": str(notebook_summary_path),
        "spatial_manifest": spatial_manifest,
        "visualization_manifest": visualization_manifest,
    }
    summary_path = output_dir / "notebook_demo_summary.json"
    summary_path.write_text(
        json.dumps(_json_ready(summary), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    print(json.dumps(_json_ready(run_demo()), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
