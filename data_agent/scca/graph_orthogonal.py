from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .spatial_diagnostics import SpatialGraph


@dataclass(frozen=True)
class GraphOrthogonalizationResult:
    original_residual: np.ndarray
    orthogonal_residual: np.ndarray
    projection: np.ndarray
    projection_norm_before: float
    projection_norm_after: float
    n_components: int


def adjacency_matrix_from_neighbors(graph: SpatialGraph) -> np.ndarray:
    n = len(graph.neighbors)
    adjacency = np.zeros((n, n), dtype=float)
    for i, neighbors in enumerate(graph.neighbors):
        for j in neighbors:
            if 0 <= int(j) < n and int(j) != i:
                adjacency[i, int(j)] = 1.0
                adjacency[int(j), i] = 1.0
    return adjacency


def graph_laplacian(adjacency: np.ndarray) -> np.ndarray:
    matrix = np.asarray(adjacency, dtype=float)
    degrees = np.diag(matrix.sum(axis=1))
    return degrees - matrix


def low_frequency_basis(laplacian: np.ndarray, n_components: int) -> np.ndarray:
    matrix = np.asarray(laplacian, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("Graph Laplacian must be a square matrix.")
    if matrix.shape[0] == 0 or n_components <= 0:
        return np.zeros((matrix.shape[0], 0), dtype=float)

    eigenvalues, eigenvectors = np.linalg.eigh(matrix)
    order = np.argsort(eigenvalues)
    vectors = eigenvectors[:, order]
    start = 1 if vectors.shape[1] > 1 else 0
    stop = min(vectors.shape[1], start + int(n_components))
    basis = vectors[:, start:stop].astype(float)
    if basis.size == 0:
        return np.zeros((matrix.shape[0], 0), dtype=float)

    basis = basis - basis.mean(axis=0, keepdims=True)
    q, _ = np.linalg.qr(basis)
    return q[:, : basis.shape[1]]


def graph_orthogonalize(residual: np.ndarray, basis: np.ndarray) -> GraphOrthogonalizationResult:
    vector = np.asarray(residual, dtype=float).reshape(-1)
    design = np.asarray(basis, dtype=float)
    if design.ndim != 2:
        raise ValueError("Basis must be a two-dimensional matrix.")
    if design.shape[0] != vector.shape[0]:
        raise ValueError("Residual and basis row counts must match.")
    if design.shape[1] == 0:
        projection = np.zeros_like(vector)
        return GraphOrthogonalizationResult(
            original_residual=vector,
            orthogonal_residual=vector.copy(),
            projection=projection,
            projection_norm_before=0.0,
            projection_norm_after=0.0,
            n_components=0,
        )

    coefficients = np.linalg.pinv(design) @ vector
    projection = design @ coefficients
    orthogonal = vector - projection
    after = float(np.linalg.norm(design.T @ orthogonal))
    before = float(np.linalg.norm(design.T @ vector))
    return GraphOrthogonalizationResult(
        original_residual=vector,
        orthogonal_residual=orthogonal,
        projection=projection,
        projection_norm_before=before,
        projection_norm_after=after,
        n_components=int(design.shape[1]),
    )
