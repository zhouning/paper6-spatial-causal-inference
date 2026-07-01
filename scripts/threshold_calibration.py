"""Calibration experiment for SCCA downgrade thresholds.

Sweeps a controlled spatially structured DGP across:
  - spatial autocorrelation strength rho  in {0.2, 0.5, 0.8}
  - sample size N                          in {500, 2000, 5000}
  - unmeasured spatial confounding sigma_u in {0.0, 0.5, 1.0, 2.0}

For each cell we generate 50 replicates with a known ATT, fit the
SCCA adjusted estimator, compute residual Moran's I and the relative
shift induced by an SLX-style spatial adjustment, and record whether
the SCCA residual-Moran downgrade rule fires under candidate material
thresholds in {0.05, 0.10, 0.15, 0.20, 0.25, 0.30}.

A run is labelled "biased" when |ATT_hat - ATT_true| / |ATT_true|
exceeds 25%, i.e. the very magnitude that the spatial_adjustment
relative-change rule is meant to flag.  We treat sigma_u > 0 cases
with strong rho as the positive class and (sigma_u == 0) cases as
the negative class for ROC purposes.

The script writes:
  paper/ijgis_submission_20260605/07_results/
    threshold_calibration_summary.csv
    threshold_calibration_roc.csv
    threshold_calibration_manifest.json

All computation is pure numpy/scipy/pandas so it can be re-run from
the public repository without the restricted Chongqing inputs.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "ijgis_submission_20260605" / "07_results"
OUT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# DGP
# ---------------------------------------------------------------------------

@dataclass
class DGPConfig:
    n: int
    rho: float          # spatial autocorrelation of latent confounder
    sigma_u: float      # strength of unmeasured spatial confounding
    att_true: float = 0.5
    seed: int = 0


def _grid_coords(n: int, rng: np.random.Generator) -> np.ndarray:
    side = int(math.ceil(math.sqrt(n)))
    xs = np.linspace(0, 1, side)
    ys = np.linspace(0, 1, side)
    grid = np.array([(x, y) for x in xs for y in ys])
    grid = grid[:n]
    grid += rng.normal(scale=1.0 / (4 * side), size=grid.shape)
    return grid


def _row_standardised_W(coords: np.ndarray, k: int = 8) -> np.ndarray:
    n = coords.shape[0]
    diffs = coords[:, None, :] - coords[None, :, :]
    d2 = np.sum(diffs ** 2, axis=2)
    np.fill_diagonal(d2, np.inf)
    idx = np.argsort(d2, axis=1)[:, :k]
    W = np.zeros((n, n))
    for i in range(n):
        W[i, idx[i]] = 1.0
    row_sums = W.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    return W / row_sums


def _sar_field(W: np.ndarray, rho: float, rng: np.random.Generator) -> np.ndarray:
    """Draw a SAR(rho) field u = (I - rho W)^-1 epsilon."""
    n = W.shape[0]
    eps = rng.normal(size=n)
    A = np.eye(n) - rho * W
    return np.linalg.solve(A, eps)


def simulate(cfg: DGPConfig) -> dict:
    rng = np.random.default_rng(cfg.seed)
    coords = _grid_coords(cfg.n, rng)
    W = _row_standardised_W(coords, k=8)

    u = _sar_field(W, cfg.rho, rng)         # unmeasured spatial confounder
    x = rng.normal(size=cfg.n)              # measured covariate
    elev = rng.normal(size=cfg.n)            # observed terrain proxy

    logit = 0.5 * x + 0.5 * elev + cfg.sigma_u * u
    p = 1.0 / (1.0 + np.exp(-logit))
    t = (rng.uniform(size=cfg.n) < p).astype(float)
    y = cfg.att_true * t + 1.0 * x + 0.7 * elev + cfg.sigma_u * u + rng.normal(scale=0.5, size=cfg.n)

    # adjusted OLS using only observed covariates
    Z = np.column_stack([np.ones(cfg.n), t, x, elev])
    beta, *_ = np.linalg.lstsq(Z, y, rcond=None)
    att_hat = beta[1]
    resid = y - Z @ beta

    # residual Moran's I
    Wr = W @ resid
    s = (resid - resid.mean())
    num = float(s @ (Wr - Wr.mean()))
    den = float((s ** 2).sum())
    moran_i = (cfg.n / W.sum()) * num / max(den, 1e-12)

    # permutation p-value
    perms = 200
    perm_stats = np.empty(perms)
    for j in range(perms):
        idx = rng.permutation(cfg.n)
        sp = (resid[idx] - resid[idx].mean())
        Wsp = W @ resid[idx]
        num_p = float(sp @ (Wsp - Wsp.mean()))
        den_p = float((sp ** 2).sum())
        perm_stats[j] = (cfg.n / W.sum()) * num_p / max(den_p, 1e-12)
    p_val = (np.sum(np.abs(perm_stats) >= abs(moran_i)) + 1) / (perms + 1)

    # SLX sensitivity: add neighbour-of-T and neighbour-of-X
    WT = W @ t
    WX = W @ x
    Z2 = np.column_stack([np.ones(cfg.n), t, WT, x, WX, elev])
    beta2, *_ = np.linalg.lstsq(Z2, y, rcond=None)
    att_slx = beta2[1]
    rel_shift = abs(att_slx - att_hat) / max(abs(att_hat), 1e-6)

    bias = att_hat - cfg.att_true
    rel_bias = abs(bias) / max(abs(cfg.att_true), 1e-6)

    return {
        "n": cfg.n,
        "rho": cfg.rho,
        "sigma_u": cfg.sigma_u,
        "att_true": cfg.att_true,
        "att_hat": att_hat,
        "att_slx": att_slx,
        "bias": bias,
        "rel_bias": rel_bias,
        "rel_shift": rel_shift,
        "moran_i": moran_i,
        "moran_p": p_val,
        "seed": cfg.seed,
    }


# ---------------------------------------------------------------------------
# Sweep
# ---------------------------------------------------------------------------

def sweep(reps: int = 50) -> pd.DataFrame:
    cells = []
    for n in (500, 2000, 5000):
        for rho in (0.2, 0.5, 0.8):
            for sigma_u in (0.0, 0.5, 1.0, 2.0):
                for r in range(reps):
                    cfg = DGPConfig(n=n, rho=rho, sigma_u=sigma_u, seed=1000 * r + 7)
                    cells.append(simulate(cfg))
    return pd.DataFrame(cells)


def roc_curves(df: pd.DataFrame, thresholds: Iterable[float]) -> pd.DataFrame:
    """For each candidate material-residual-Moran threshold compute TPR/FPR.

    Positive class: rel_bias > 0.25 (i.e. estimator is materially biased).
    Negative class: rel_bias <= 0.25 (i.e. estimator is acceptable).
    Predictor: |moran_i| >= threshold AND moran_p <= 0.05.
    """
    rows = []
    positive = df["rel_bias"] > 0.25
    for t in thresholds:
        pred = (df["moran_i"].abs() >= t) & (df["moran_p"] <= 0.05)
        tp = int(((pred) & (positive)).sum())
        fp = int(((pred) & (~positive)).sum())
        fn = int(((~pred) & (positive)).sum())
        tn = int(((~pred) & (~positive)).sum())
        tpr = tp / max(tp + fn, 1)
        fpr = fp / max(fp + tn, 1)
        precision = tp / max(tp + fp, 1)
        rows.append({
            "threshold": t,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "tpr": tpr, "fpr": fpr, "precision": precision,
            "youden_j": tpr - fpr,
        })
    return pd.DataFrame(rows)


def main() -> None:
    df = sweep(reps=50)
    summary_path = OUT / "threshold_calibration_summary.csv"
    df.to_csv(summary_path, index=False)

    by_cell = (
        df.groupby(["n", "rho", "sigma_u"])
        .agg(
            mean_bias=("bias", "mean"),
            mean_rel_bias=("rel_bias", "mean"),
            frac_biased_gt_25=("rel_bias", lambda s: float((s > 0.25).mean())),
            mean_moran_i=("moran_i", "mean"),
            frac_moran_sig=("moran_p", lambda s: float((s <= 0.05).mean())),
            mean_rel_shift=("rel_shift", "mean"),
        )
        .reset_index()
    )
    by_cell.to_csv(OUT / "threshold_calibration_cells.csv", index=False)

    thresholds = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    roc = roc_curves(df, thresholds)
    roc.to_csv(OUT / "threshold_calibration_roc.csv", index=False)

    best = roc.loc[roc["youden_j"].idxmax()]
    manifest = {
        "rule_set": "scca-evidence-grade-rules-2026-06-20",
        "thresholds_tested": thresholds,
        "best_threshold_by_youden_j": float(best["threshold"]),
        "best_tpr": float(best["tpr"]),
        "best_fpr": float(best["fpr"]),
        "best_precision": float(best["precision"]),
        "n_rows": int(len(df)),
        "rho_grid": [0.2, 0.5, 0.8],
        "n_grid": [500, 2000, 5000],
        "sigma_u_grid": [0.0, 0.5, 1.0, 2.0],
        "reps_per_cell": 50,
        "positive_class": "rel_bias_gt_0_25",
        "rule_predictor": "abs(moran_i) >= t AND moran_p <= 0.05",
    }
    (OUT / "threshold_calibration_manifest.json").write_text(json.dumps(manifest, indent=2))

    print("wrote", summary_path)
    print(roc.to_string(index=False))
    print("best by Youden's J:")
    print(best.to_string())


if __name__ == "__main__":
    main()
