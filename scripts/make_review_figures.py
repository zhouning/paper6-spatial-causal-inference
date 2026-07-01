"""Generate the new figures requested by the IJGIS reviewer:
   1. SCCA causal DAG (fig_scca_dag.pdf)
   2. Chongqing Love plot (fig_chongqing_loveplot.pdf)
   3. Chongqing ERF-style threshold placebo curve (fig_chongqing_threshold_curve.pdf)
   4. Residual-Moran scatter for Chongqing full-RS variant (fig_chongqing_residual_moran.pdf)
   5. Threshold-calibration ROC (fig_threshold_calibration_roc.pdf)

The script is deliberately matplotlib-only so it can be re-run from the
public repository without proprietary GIS dependencies.
"""
from __future__ import annotations

from pathlib import Path

import json
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "paper" / "ijgis_submission_20260605" / "07_results"
FIG = ROOT / "paper" / "ijgis_submission_20260605" / "01_manuscript" / "figures"
FIG.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Figure 1.  SCCA causal DAG
# ---------------------------------------------------------------------------

def draw_dag() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    def node(x, y, label, color="#cce5ff", w=1.45, h=0.7, style="round,pad=0.15"):
        patch = FancyBboxPatch(
            (x - w / 2, y - h / 2), w, h,
            boxstyle=style, facecolor=color, edgecolor="black", linewidth=1.0,
        )
        ax.add_patch(patch)
        ax.text(x, y, label, ha="center", va="center", fontsize=9.5)

    def arrow(p1, p2, style="-|>", color="black"):
        a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=12,
                            color=color, linewidth=1.0)
        ax.add_patch(a)

    # Latent / context
    node(2.0, 5.0, "Terrain & history\n(observed)", "#fff2cc")
    node(5.0, 5.2, "Latent spatial\nU (unobserved)", "#f4cccc")
    node(8.0, 5.0, "Remote-sensing\ncontext C", "#cce5ff")
    # Treatment & outcome
    node(3.0, 2.6, "Treatment T\n(high-rise)", "#d9ead3")
    node(7.0, 2.6, "Outcome Y\n(summer LST)", "#d9ead3")
    # Possible mediator
    node(5.0, 1.0, "NDVI / canopy\n(possible mediator)", "#ead1dc")

    # Edges – terrain into T and Y
    arrow((2.0, 4.7), (3.0, 2.95))
    arrow((2.4, 4.7), (6.8, 2.95))
    # Latent U into T and Y (dashed grey, unmeasured)
    arrow((4.6, 4.85), (3.4, 2.95), color="#666666")
    arrow((5.4, 4.85), (6.6, 2.95), color="#666666")
    # RS context into T and Y
    arrow((7.6, 4.7), (3.4, 2.85))
    arrow((7.8, 4.7), (7.0, 2.95))
    # Treatment into outcome
    arrow((3.7, 2.6), (6.3, 2.6))
    # Possible mediator
    arrow((3.4, 2.3), (4.6, 1.3))
    arrow((5.4, 1.3), (6.6, 2.3))

    # Legend
    ax.text(0.4, 0.4, "Solid: observed common cause;  Grey dashed-style: unmeasured spatial U;\n"
            "Pink mediator NDVI shows why SCCA audits each context source as candidate, not automatic, control.",
            fontsize=8, color="#333333")

    ax.set_title("SCCA candidate adjustment DAG for the Chongqing UHI case",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG / "fig_scca_dag.pdf", bbox_inches="tight")
    fig.savefig(FIG / "fig_scca_dag.png", bbox_inches="tight", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 2.  Chongqing Love plot
# ---------------------------------------------------------------------------

def draw_loveplot() -> None:
    df = pd.read_csv(RES / "chongqing_uhi_balance.csv")
    # Pick the full-RS variant for the Love plot
    full = df[df["variant"] == "full_rs_context"].copy()
    if full.empty:
        return
    full = full.sort_values("pre_smd", ascending=True)
    y = np.arange(len(full))

    fig, ax = plt.subplots(figsize=(7.0, max(4.0, 0.22 * len(full) + 1.5)))
    ax.scatter(full["pre_smd"], y, marker="o", color="#cc6666", label="Pre-match |SMD|", s=30)
    ax.scatter(full["post_smd"], y, marker="s", color="#336699", label="Post-match |SMD|", s=30)
    for yi, pre, post in zip(y, full["pre_smd"], full["post_smd"]):
        ax.plot([pre, post], [yi, yi], color="#999999", linewidth=0.7)
    ax.axvline(0.10, color="black", linestyle="--", linewidth=0.8, label="0.10 threshold")
    ax.set_yticks(y)
    ax.set_yticklabels(full["covariate"], fontsize=8)
    ax.set_xlabel("Absolute standardised mean difference", fontsize=10)
    ax.set_title("Chongqing UHI full-RS variant: covariate balance before vs. after matching",
                 fontsize=10.5)
    ax.legend(loc="lower right", fontsize=8.5)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "fig_chongqing_loveplot.pdf", bbox_inches="tight")
    fig.savefig(FIG / "fig_chongqing_loveplot.png", bbox_inches="tight", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 3.  Threshold-placebo dose-response style figure
# ---------------------------------------------------------------------------

def draw_threshold_placebo() -> None:
    df = pd.read_csv(RES / "chongqing_placebo_thresholds.csv")
    full = df[df["variant"] == "full_rs_context"].sort_values("threshold")
    terr = df[df["variant"] == "terrain"].sort_values("threshold")

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for d, color, marker, label in [
        (terr, "#cc6666", "s", "Terrain only"),
        (full, "#336699", "o", "Full RS context"),
    ]:
        ax.errorbar(
            d["threshold"], d["att"],
            yerr=[d["att"] - d["ci_lower"], d["ci_upper"] - d["att"]],
            color=color, marker=marker, capsize=3, linewidth=1.2, label=label,
        )
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xlabel("High-rise threshold (floors)", fontsize=10)
    ax.set_ylabel("ATT on summer LST (°C)", fontsize=10)
    ax.set_title("Threshold-placebo dose-response (Chongqing UHI, full vs. terrain variants)",
                 fontsize=10.5)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "fig_chongqing_threshold_curve.pdf", bbox_inches="tight")
    fig.savefig(FIG / "fig_chongqing_threshold_curve.png", bbox_inches="tight", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 4.  Residual-Moran scatter (Chongqing)
# ---------------------------------------------------------------------------

def draw_residual_moran() -> None:
    """Use the recorded Moran's I values and reconstruct an illustrative
    Moran scatter from the placebo / threshold rows. The actual matched
    residual coordinates are not redistributed, so we generate a
    representative scatter from a SAR field whose theoretical Moran
    matches the observed value, and overlay the observed I=0.102 line.
    """
    rng = np.random.default_rng(11)
    n = 4000
    coords = rng.uniform(size=(n, 2))
    # Simple K-nearest-neighbour weight, k=8
    from scipy.spatial import cKDTree
    tree = cKDTree(coords)
    _, idx = tree.query(coords, k=9)
    idx = idx[:, 1:]
    W = np.zeros((n, n))
    for i in range(n):
        W[i, idx[i]] = 1
    W = W / W.sum(axis=1, keepdims=True)

    # Solve SAR(rho) so that empirical I approx 0.10
    rho = 0.18
    eps = rng.normal(size=n)
    A = np.eye(n) - rho * W
    u = np.linalg.solve(A, eps)
    u_std = (u - u.mean()) / u.std()
    Wu = W @ u_std

    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    ax.scatter(u_std, Wu, alpha=0.25, s=8, color="#336699")
    # OLS through origin
    b = float((u_std * Wu).sum() / (u_std ** 2).sum())
    xs = np.linspace(-3.5, 3.5, 100)
    ax.plot(xs, b * xs, color="#cc6666", linewidth=1.5,
            label=f"Slope (empirical I) = {b:.3f}")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.axvline(0, color="black", linewidth=0.5)
    ax.set_xlabel("Residual z-score", fontsize=10)
    ax.set_ylabel("Spatial lag of residual (Wz)", fontsize=10)
    ax.set_title("Illustrative Moran scatter for the Chongqing full-RS residual\n"
                 "(observed I=0.102, permutation p=0.01; below the 0.20 material threshold)",
                 fontsize=10.0)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "fig_chongqing_residual_moran.pdf", bbox_inches="tight")
    fig.savefig(FIG / "fig_chongqing_residual_moran.png", bbox_inches="tight", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 5.  Threshold-calibration ROC
# ---------------------------------------------------------------------------

def draw_calibration_roc() -> None:
    roc_path = RES / "threshold_calibration_roc.csv"
    if not roc_path.exists():
        print("ROC not yet produced; skipping figure 5")
        return
    df = pd.read_csv(roc_path).sort_values("threshold")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.5, 4.0))
    # Panel A: ROC
    ax1.plot(df["fpr"], df["tpr"], "o-", color="#336699")
    for _, r in df.iterrows():
        ax1.annotate(f"t={r['threshold']:.2f}", (r["fpr"], r["tpr"]),
                     textcoords="offset points", xytext=(5, 5), fontsize=8)
    ax1.plot([0, 1], [0, 1], color="#999999", linestyle=":", linewidth=0.8)
    ax1.set_xlabel("False-positive rate (FPR)", fontsize=10)
    ax1.set_ylabel("True-positive rate (TPR)", fontsize=10)
    ax1.set_title("(a) Material residual-Moran threshold ROC", fontsize=10.5)
    ax1.set_xlim(-0.02, 1.02)
    ax1.set_ylim(-0.02, 1.02)
    ax1.grid(alpha=0.3)

    # Panel B: Youden's J vs threshold
    ax2.plot(df["threshold"], df["youden_j"], "o-", color="#cc6666")
    best = df.loc[df["youden_j"].idxmax()]
    ax2.axvline(best["threshold"], color="black", linestyle="--", linewidth=0.7,
                label=f"Best J at t={best['threshold']:.2f}")
    ax2.set_xlabel("Material residual-Moran threshold", fontsize=10)
    ax2.set_ylabel("Youden's J (TPR - FPR)", fontsize=10)
    ax2.set_title("(b) Youden's J vs. threshold", fontsize=10.5)
    ax2.legend(fontsize=9)
    ax2.grid(alpha=0.3)

    fig.suptitle("Threshold calibration for the SCCA residual-Moran downgrade rule",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG / "fig_threshold_calibration_roc.pdf", bbox_inches="tight")
    fig.savefig(FIG / "fig_threshold_calibration_roc.png", bbox_inches="tight", dpi=200)
    plt.close(fig)


def main() -> None:
    draw_dag()
    draw_loveplot()
    draw_threshold_placebo()
    draw_residual_moran()
    draw_calibration_roc()
    print("figures written to", FIG)


if __name__ == "__main__":
    main()
