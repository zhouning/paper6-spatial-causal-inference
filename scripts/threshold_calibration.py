"""Calibration experiment for SCCA downgrade thresholds.

Sweeps a controlled spatially structured DGP across:
  - spatial autocorrelation strength rho  in {0.2, 0.5, 0.8}
  - sample size N                          in {500, 2000, 5000}
  - unmeasured spatial confounding sigma_u in {0.0, 0.5, 1.0, 2.0}
  - spatial-process FAMILY                 in {SAR, CAR, exponential/Matern
                                              kernel, non-stationary}

The multi-family sweep answers a reviewer concern: a threshold calibrated on a
single SAR generator may not transfer to other spatial processes. We therefore
regenerate the latent confounder under four qualitatively different spatial
processes and report both the pooled ROC and per-family ROC so threshold
stability across families is auditable.

For each cell we generate replicates with a known ATT, fit the SCCA adjusted
estimator, compute residual Moran's I and the relative shift induced by an
SLX-style spatial adjustment, and record whether the SCCA residual-Moran
downgrade rule fires under candidate material thresholds in
{0.05, 0.10, 0.15, 0.20, 0.25, 0.30}.

A run is labelled "biased" when |ATT_hat - ATT_true| / |ATT_true|
exceeds 25%, i.e. the very magnitude that the spatial_adjustment
relative-change rule is meant to flag.

The script writes:
  paper/ijgis_submission_20260605/07_results/
    threshold_calibration_summary.csv
    threshold_calibration_roc.csv          (pooled across families)
    threshold_calibration_roc_by_family.csv
    threshold_calibration_cells.csv
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
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "ijgis_submission_20260605" / "07_results"
OUT.mkdir(parents=True, exist_ok=True)

# Spatial-process families for the latent confounder U.
FAMILIES = ("sar", "car", "kernel", "nonstationary")


# ---------------------------------------------------------------------------
# DGP
# ---------------------------------------------------------------------------

@dataclass
class DGPConfig:
    n: int
    rho: float          # spatial autocorrelation of latent confounder
    sigma_u: float      # strength of unmeasured spatial confounding
    family: str = "sar"  # spatial-process family for U
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


def _sparse_knn_W(coords: np.ndarray, k: int = 8) -> sparse.csr_matrix:
    """Row-standardised kNN weight matrix as a sparse CSR matrix.

    Used for the Moran statistic and SLX neighbour terms so residual
    diagnostics scale to n in the thousands without dense n x n products.
    """
    from scipy.spatial import cKDTree

    n = coords.shape[0]
    tree = cKDTree(coords)
    _, idx = tree.query(coords, k=k + 1)  # first neighbour is self
    rows = np.repeat(np.arange(n), k)
    cols = idx[:, 1:].reshape(-1)
    data = np.full(rows.shape, 1.0 / k)
    return sparse.csr_matrix((data, (rows, cols)), shape=(n, n))


def _standardise(field: np.ndarray) -> np.ndarray:
    field = field - field.mean()
    sd = field.std()
    return field / sd if sd > 1e-12 else field


def _sar_field(W: np.ndarray, rho: float, rng: np.random.Generator) -> np.ndarray:
    """Draw a SAR(rho) field u = (I - rho W)^-1 epsilon."""
    n = W.shape[0]
    eps = rng.normal(size=n)
    A = np.eye(n) - rho * W
    return _standardise(np.linalg.solve(A, eps))


def _car_field(W: np.ndarray, rho: float, rng: np.random.Generator) -> np.ndarray:
    """Draw a CAR field with precision (I - rho W), symmetrised.

    A conditional autoregression has a different covariance structure than a
    simultaneous (SAR) one; using it checks that the threshold is not tuned to
    the SAR error geometry.
    """
    n = W.shape[0]
    Wsym = 0.5 * (W + W.T)
    prec = np.eye(n) - rho * Wsym
    # Ensure positive definiteness for the draw.
    prec = prec + (abs(min(np.linalg.eigvalsh(prec).min(), 0.0)) + 1e-3) * np.eye(n)
    cov = np.linalg.inv(prec)
    L = np.linalg.cholesky(cov + 1e-8 * np.eye(n))
    return _standardise(L @ rng.normal(size=n))


def _kernel_field(coords: np.ndarray, rho: float, rng: np.random.Generator) -> np.ndarray:
    """Draw a Gaussian process field with an exponential (Matern-1/2) kernel.

    The correlation range grows with rho so the sweep still moves from weak to
    strong autocorrelation, but the covariance is distance-based rather than
    graph-based.
    """
    n = coords.shape[0]
    diffs = coords[:, None, :] - coords[None, :, :]
    dist = np.sqrt(np.sum(diffs ** 2, axis=2))
    length_scale = 0.05 + 0.45 * rho
    cov = np.exp(-dist / length_scale)
    L = np.linalg.cholesky(cov + 1e-6 * np.eye(n))
    return _standardise(L @ rng.normal(size=n))


def _nonstationary_field(
    coords: np.ndarray, rho: float, rng: np.random.Generator
) -> np.ndarray:
    """Non-stationary field: a smooth spatial trend plus a local kernel bump.

    Autocorrelation strength varies over space, violating the stationarity that
    SAR/CAR assume.
    """
    n = coords.shape[0]
    x, y = coords[:, 0], coords[:, 1]
    trend = np.sin(2 * math.pi * rho * x) + np.cos(2 * math.pi * rho * y)
    # Localised high-correlation patch in one quadrant.
    diffs = coords[:, None, :] - coords[None, :, :]
    dist = np.sqrt(np.sum(diffs ** 2, axis=2))
    local = np.exp(-dist / (0.03 + 0.2 * rho))
    local_field = local @ rng.normal(size=n) / math.sqrt(n)
    weight = (x > 0.5).astype(float)
    return _standardise(trend + rho * weight * local_field * math.sqrt(n) * 0.3)


def _latent_field(
    family: str, coords: np.ndarray, W: np.ndarray, rho: float, rng: np.random.Generator
) -> np.ndarray:
    if family == "sar":
        return _sar_field(W, rho, rng)
    if family == "car":
        return _car_field(W, rho, rng)
    if family == "kernel":
        return _kernel_field(coords, rho, rng)
    if family == "nonstationary":
        return _nonstationary_field(coords, rho, rng)
    raise ValueError(f"Unknown spatial family: {family}")


def simulate(cfg: DGPConfig) -> dict:
    rng = np.random.default_rng(cfg.seed)
    coords = _grid_coords(cfg.n, rng)
    # Dense W is only needed by the SAR/CAR field draws; kernel and
    # non-stationary families use coordinates directly, so skip the dense
    # build for them.
    if cfg.family in ("sar", "car"):
        W = _row_standardised_W(coords, k=8)
    else:
        W = None

    u = _latent_field(cfg.family, coords, W, cfg.rho, rng)  # unmeasured confounder
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

    # residual Moran's I using a sparse kNN weight matrix (row-standardised,
    # so W.sum() == n and the leading n/W.sum() factor is 1).
    Wsp = _sparse_knn_W(coords, k=8)
    s = resid - resid.mean()
    den = float(s @ s)
    moran_i = float(s @ (Wsp @ s)) / max(den, 1e-12)

    # permutation p-value (99 permutations; sparse matvec keeps this cheap)
    perms = 99
    perm_stats = np.empty(perms)
    for j in range(perms):
        sp = rng.permutation(s)
        perm_stats[j] = float(sp @ (Wsp @ sp)) / max(float(sp @ sp), 1e-12)
    p_val = (np.sum(np.abs(perm_stats) >= abs(moran_i)) + 1) / (perms + 1)

    # SLX sensitivity: add neighbour-of-T and neighbour-of-X
    WT = Wsp @ t
    WX = Wsp @ x
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
        "family": cfg.family,
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

def sweep(reps: int = 20, families: Iterable[str] = FAMILIES) -> pd.DataFrame:
    cells = []
    # n grid kept moderate because CAR/kernel families require dense n x n
    # Cholesky/inverse draws; the range still spans small to large samples.
    for fam_idx, family in enumerate(families):
        for n in (400, 900, 1600):
            for rho in (0.2, 0.5, 0.8):
                for sigma_u in (0.0, 0.5, 1.0, 2.0):
                    for r in range(reps):
                        cfg = DGPConfig(
                            n=n, rho=rho, sigma_u=sigma_u, family=family,
                            seed=1000 * r + 7 + 100_003 * fam_idx,
                        )
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


def roc_by_family(df: pd.DataFrame, thresholds: Iterable[float]) -> pd.DataFrame:
    parts = []
    for family, sub in df.groupby("family"):
        roc = roc_curves(sub, thresholds)
        roc.insert(0, "family", family)
        parts.append(roc)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def main() -> None:
    reps = 20
    df = sweep(reps=reps)
    summary_path = OUT / "threshold_calibration_summary.csv"
    df.to_csv(summary_path, index=False)

    by_cell = (
        df.groupby(["family", "n", "rho", "sigma_u"])
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

    roc_fam = roc_by_family(df, thresholds)
    roc_fam.to_csv(OUT / "threshold_calibration_roc_by_family.csv", index=False)

    best = roc.loc[roc["youden_j"].idxmax()]
    # per-family Youden optimum, to report threshold stability
    fam_best = (
        roc_fam.loc[roc_fam.groupby("family")["youden_j"].idxmax()]
        [["family", "threshold", "tpr", "fpr", "youden_j"]]
        .to_dict(orient="records")
        if not roc_fam.empty
        else []
    )
    manifest = {
        "rule_set": "scca-evidence-grade-rules-2026-06-30",
        "thresholds_tested": thresholds,
        "families": list(FAMILIES),
        "best_threshold_by_youden_j_pooled": float(best["threshold"]),
        "best_tpr": float(best["tpr"]),
        "best_fpr": float(best["fpr"]),
        "best_precision": float(best["precision"]),
        "per_family_youden_optimum": fam_best,
        "n_rows": int(len(df)),
        "rho_grid": [0.2, 0.5, 0.8],
        "n_grid": [400, 900, 1600],
        "sigma_u_grid": [0.0, 0.5, 1.0, 2.0],
        "reps_per_cell": reps,
        "positive_class": "rel_bias_gt_0_25",
        "rule_predictor": "abs(moran_i) >= t AND moran_p <= 0.05",
    }
    (OUT / "threshold_calibration_manifest.json").write_text(json.dumps(manifest, indent=2))

    print("wrote", summary_path)
    print("\nPOOLED ROC:")
    print(roc.to_string(index=False))
    print("\nPER-FAMILY ROC:")
    print(roc_fam.to_string(index=False))
    print("\nbest by Youden's J (pooled):")
    print(best.to_string())


if __name__ == "__main__":
    main()
