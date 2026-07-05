"""Generate submission-quality IJGIS manuscript figures.

The figures are deliberately matplotlib-only so they can be rerun from the
review repository without proprietary GIS dependencies.
"""
from __future__ import annotations

from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "paper" / "ijgis_submission_20260605" / "07_results"
FIG = ROOT / "paper" / "ijgis_submission_20260605" / "01_manuscript" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

BLUE = "#2f5f8f"
RED = "#b85b5b"
GREEN = "#5e8f64"
PURPLE = "#8b6aa8"
GOLD = "#b08a3c"
GREY = "#7a7a7a"
LIGHT_GREY = "#d8d8d8"
TEXT = "#222222"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "font.size": 8,
    "axes.titlesize": 9,
    "axes.labelsize": 8,
    "axes.linewidth": 0.7,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "legend.frameon": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


def save_pub(fig: plt.Figure, stem: str) -> None:
    fig.savefig(FIG / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(FIG / f"{stem}.png", bbox_inches="tight", dpi=300)
    plt.close(fig)


def draw_dag() -> None:
    """Figure 1: causal-role logic without crossing arrows."""
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    nodes = {
        "context": (2.0, 4.6, "Observed spatial\ncontext C", "#fff3c4"),
        "latent": (5.6, 4.8, "Latent spatial\nprocess U", "#f6d4d4"),
        "treat": (2.6, 2.4, "Treatment T\n(high-rise share)", "#d9ead3"),
        "outcome": (7.2, 2.4, "Outcome Y\n(summer LST)", "#d9ead3"),
        "mediator": (5.0, 0.9, "Same-period vegetation\npossible mediator", "#ead8ed"),
    }

    def node(name: str, width: float = 1.9, height: float = 0.78) -> None:
        x, y, label, color = nodes[name]
        patch = FancyBboxPatch(
            (x - width / 2, y - height / 2),
            width,
            height,
            boxstyle="round,pad=0.12,rounding_size=0.06",
            facecolor=color,
            edgecolor="#333333",
            linewidth=0.8,
        )
        ax.add_patch(patch)
        ax.text(x, y, label, ha="center", va="center", fontsize=8.2, color=TEXT)

    for name in nodes:
        node(name)

    def arrow(start, end, *, color="#333333", dashed=False, rad=0.0) -> None:
        patch = FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=0.9,
            color=color,
            linestyle="--" if dashed else "-",
            connectionstyle=f"arc3,rad={rad}",
            shrinkA=7,
            shrinkB=7,
        )
        ax.add_patch(patch)

    arrow((2.0, 4.2), (2.6, 2.8), color=GOLD)
    arrow((2.6, 4.35), (7.0, 2.8), color=GOLD, rad=-0.12)
    arrow((5.25, 4.45), (3.0, 2.8), color=GREY, dashed=True, rad=0.12)
    arrow((5.95, 4.45), (7.0, 2.8), color=GREY, dashed=True, rad=-0.08)
    arrow((3.45, 2.4), (6.35, 2.4), color="#333333")
    arrow((3.2, 2.0), (4.45, 1.25), color=PURPLE, rad=0.08)
    arrow((5.55, 1.25), (6.75, 2.0), color=PURPLE, rad=0.08)

    ax.text(0.3, 0.22,
            "Solid arrows: observed causal or candidate adjustment paths. Dashed arrows: unobserved spatial process.\n"
            "Vegetation is drawn below the treatment because same-period surfaces may be mediators, not automatic controls.",
            fontsize=7.2, color="#444444")
    ax.set_title("SCCA candidate adjustment DAG for the Chongqing UHI case", pad=8)
    save_pub(fig, "fig_scca_dag")


def draw_loveplot() -> None:
    """Figure 3: pre/post balance, sorted to avoid crossing and label clutter."""
    df = pd.read_csv(RES / "chongqing_uhi_balance.csv")
    full = df[df["variant"] == "pre_treatment"].copy()
    if full.empty:
        raise RuntimeError("pre_treatment balance rows not found")
    full = full.assign(max_smd=full[["pre_smd", "post_smd"]].max(axis=1))
    full = full.sort_values("max_smd", ascending=True)
    y = np.arange(len(full))

    fig_h = max(3.6, 0.38 * len(full) + 1.0)
    fig, ax = plt.subplots(figsize=(6.6, fig_h))
    ax.hlines(y, full["post_smd"], full["pre_smd"], color=LIGHT_GREY, lw=1.2, zorder=1)
    ax.scatter(full["pre_smd"], y, marker="o", facecolors="white", edgecolors=RED,
               linewidths=1.1, s=38, label="Before matching", zorder=3)
    ax.scatter(full["post_smd"], y, marker="s", color=BLUE, s=28,
               label="After matching", zorder=4)
    ax.axvline(0.10, color="#333333", linestyle=(0, (4, 3)), lw=0.9)
    ax.text(0.103, len(full) - 0.55, "0.10 rule", fontsize=7, va="top", color="#333333")
    ax.set_yticks(y)
    ax.set_yticklabels(full["covariate"].str.replace("rs_", "", regex=False))
    ax.set_xlabel("Absolute standardized mean difference")
    ax.set_xlim(0, max(0.18, float(full["max_smd"].max()) + 0.025))
    ax.grid(axis="x", alpha=0.22, lw=0.5)
    ax.legend(loc="lower right", fontsize=7.5)
    ax.set_title("Chongqing UHI pre-treatment set: covariate balance", pad=7)
    fig.tight_layout()
    save_pub(fig, "fig_chongqing_loveplot")


def draw_threshold_placebo() -> None:
    """Figure 4: dose-response style threshold sensitivity."""
    df = pd.read_csv(RES / "chongqing_placebo_thresholds.csv")
    fig, ax = plt.subplots(figsize=(6.2, 3.9))
    specs = [
        ("pre_treatment", BLUE, "o", -0.07, "Pre-treatment set"),
        ("full_rs_context", RED, "s", 0.07, "Full remote-sensing set"),
    ]
    for variant, color, marker, offset, label in specs:
        d = df[df["variant"] == variant].sort_values("threshold")
        if d.empty:
            continue
        x = d["threshold"].to_numpy(float) + offset
        y = d["att"].to_numpy(float)
        yerr = np.vstack([y - d["ci_lower"].to_numpy(float), d["ci_upper"].to_numpy(float) - y])
        ax.errorbar(x, y, yerr=yerr, color=color, marker=marker, ms=4.5,
                    capsize=3, lw=1.2, elinewidth=0.9, label=label)
    ax.axhline(0, color="#333333", lw=0.7)
    ax.set_xticks([8, 10, 12])
    ax.set_xlabel("High-rise threshold (floors)")
    ax.set_ylabel(r"ATT on summer LST ($^\circ$C)")
    ax.set_title("Threshold-placebo sensitivity in the Chongqing UHI case", pad=7)
    ax.grid(alpha=0.22, lw=0.5)
    ax.legend(loc="upper left", fontsize=7.5)
    fig.tight_layout()
    save_pub(fig, "fig_chongqing_threshold_curve")


def draw_residual_moran() -> None:
    """Figure 5: empirical matched-residual Moran scatter.

    The spatial lag is scaled with the same distance-band binary weights and
    n/S0 factor used by run_residual_spatial_diagnostics, so the fitted slope
    matches the reported Moran's I instead of a different KNN diagnostic.
    """
    sys.path.insert(0, str(ROOT))

    sample_path = RES / "chongqing_uhi_analysis_sample.csv"
    resid_path = RES / "chongqing_residual_spatial_diagnostics.csv"
    recorded_i = None
    recorded_p = None
    if resid_path.exists():
        rd = pd.read_csv(resid_path)
        row = rd[rd["variant"] == "pre_treatment"]
        if not row.empty:
            recorded_i = float(row.iloc[0]["moran_i"])
            recorded_p = float(row.iloc[0]["permutation_p_value"])

    if not sample_path.exists():
        raise RuntimeError("Chongqing analysis sample is required for the residual-Moran scatter")

    from data_agent.experiments.chongqing_uhi_analysis import (
        _match_variant,
        _moran_i,
        _ols_residuals,
        resolve_feature_columns,
    )

    frame = pd.read_csv(sample_path)
    row, _, _, details = _match_variant(
        frame,
        variant="pre_treatment",
        threshold=10,
        caliper=0.2,
        n_bootstrap=0,
        random_state=0,
        outcome_col="LST",
    )
    prepared = details["prepared"]
    idx = pd.Index(details.get("matched_indices", [])).unique()
    matched = prepared.loc[idx].copy()
    covariates = list(details.get("covariates", []))
    if matched.empty or not covariates:
        raise RuntimeError("No matched rows or covariates available for residual-Moran figure")

    residuals = _ols_residuals(matched, "_outcome", ["_treatment", *covariates])
    xcol, ycol = resolve_feature_columns(frame, ("centroid_x", "centroid_y"))
    coords = matched[[xcol, ycol]].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    mean_lat = float(np.nanmean(coords[:, 1])) if len(coords) else 0.0
    coords_m = np.column_stack([
        (coords[:, 0] - np.nanmin(coords[:, 0])) * 111_000.0 * max(np.cos(np.deg2rad(mean_lat)), 0.1),
        (coords[:, 1] - np.nanmin(coords[:, 1])) * 111_000.0,
    ])

    moran, p_value, distance_band = _moran_i(
        residuals,
        coords_m,
        n_permutations=99,
        rng=np.random.default_rng(0),
    )
    diffs = coords_m[:, None, :] - coords_m[None, :, :]
    distances = np.sqrt(np.sum(diffs**2, axis=2))
    weights = ((distances > 0) & (distances <= distance_band)).astype(float)
    weight_sum = float(weights.sum())
    centered = residuals - residuals.mean()
    scale = centered.std()
    x = centered / scale
    lag = (len(centered) / weight_sum) * (weights @ centered) / scale
    slope = float((x * lag).sum() / (x * x).sum())

    rng = np.random.default_rng(20260705)
    keep = np.arange(len(x))
    if len(x) > 2500:
        keep = np.sort(rng.choice(keep, size=2500, replace=False))

    fig, ax = plt.subplots(figsize=(5.4, 4.1))
    ax.scatter(x[keep], lag[keep], alpha=0.18, s=7, color=BLUE, linewidths=0)
    xs = np.linspace(float(np.percentile(x, 1)), float(np.percentile(x, 99)), 100)
    ax.plot(xs, slope * xs, color=RED, lw=1.4, label=fr"Slope = Moran's $I$ = {slope:.3f}")
    ax.axhline(0, color="#333333", lw=0.6)
    ax.axvline(0, color="#333333", lw=0.6)
    ax.set_xlabel("Standardized matched residual")
    ax.set_ylabel("Scaled spatial lag of residual")
    shown_p = recorded_p if recorded_p is not None else p_value
    ax.text(0.03, 0.97, f"Distance band = {distance_band/1000:.1f} km\nPermutation p = {shown_p:.2f}",
            transform=ax.transAxes, va="top", ha="left", fontsize=7.2,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#bbbbbb", lw=0.6))
    ax.legend(loc="lower right", fontsize=7.5)
    ax.grid(alpha=0.2, lw=0.5)
    ax.set_title("Residual spatial autocorrelation after pre-treatment matching", pad=7)
    fig.tight_layout()
    if recorded_i is not None and abs(slope - recorded_i) > 0.005:
        print(f"warning: plotted Moran slope {slope:.3f} differs from recorded {recorded_i:.3f}")
    if abs(slope - moran) > 0.005:
        print(f"warning: plotted Moran slope {slope:.3f} differs from recomputed {moran:.3f}")
    save_pub(fig, "fig_chongqing_residual_moran")

def draw_calibration_roc() -> None:
    """Figure 6: pooled and process-family ROC, with sparse labels."""
    roc_path = RES / "threshold_calibration_roc.csv"
    fam_path = RES / "threshold_calibration_roc_by_family.csv"
    if not roc_path.exists() or not fam_path.exists():
        raise RuntimeError("threshold calibration ROC inputs are missing")

    df = pd.read_csv(roc_path).sort_values("threshold")
    fam = pd.read_csv(fam_path).sort_values(["family", "threshold"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.4, 3.7), sharex=True, sharey=True)

    ax1.plot(df["fpr"], df["tpr"], color=BLUE, lw=1.4)
    ax1.scatter(df["fpr"], df["tpr"], color=BLUE, s=24, zorder=3)
    default = df[np.isclose(df["threshold"], 0.10)].iloc[0]
    ax1.scatter([default["fpr"]], [default["tpr"]], color=RED, s=42, zorder=4)
    ax1.annotate("default t=0.10", xy=(default["fpr"], default["tpr"]), xytext=(24, -10),
                 textcoords="offset points", arrowprops=dict(arrowstyle="->", lw=0.7, color=RED),
                 fontsize=7.2, color=RED)
    ax1.plot([0, 1], [0, 1], color=LIGHT_GREY, linestyle=":", lw=0.9)
    ax1.set_title("(a) Pooled ROC")
    ax1.set_xlabel("False-positive rate")
    ax1.set_ylabel("True-positive rate")

    colors = {"sar": BLUE, "car": RED, "kernel": GREEN, "nonstationary": PURPLE}
    labels = {"sar": "SAR", "car": "CAR", "kernel": "kernel", "nonstationary": "non-stationary"}
    for family, sub in fam.groupby("family", sort=False):
        ax2.plot(sub["fpr"], sub["tpr"], color=colors.get(family, GREY), lw=1.2, marker="o", ms=3)
        end = sub.iloc[-1]
        ax2.text(float(end["fpr"]) + 0.018, float(end["tpr"]), labels.get(family, family),
                 color=colors.get(family, GREY), fontsize=7.2, va="center")
    ax2.plot([0, 1], [0, 1], color=LIGHT_GREY, linestyle=":", lw=0.9)
    ax2.set_title("(b) Process-family ROC")
    ax2.set_xlabel("False-positive rate")

    for ax in (ax1, ax2):
        ax.set_xlim(-0.02, 0.16)
        ax.set_ylim(-0.02, 1.04)
        ax.grid(alpha=0.22, lw=0.5)

    fig.suptitle("Residual-Moran downgrade threshold calibration", y=1.02, fontsize=9.5)
    fig.tight_layout()
    save_pub(fig, "fig_threshold_calibration_roc")


def main() -> None:
    draw_dag()
    draw_loveplot()
    draw_threshold_placebo()
    draw_residual_moran()
    draw_calibration_roc()
    print("figures written to", FIG)


if __name__ == "__main__":
    main()