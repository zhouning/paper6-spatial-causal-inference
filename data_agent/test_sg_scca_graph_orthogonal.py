import numpy as np

from data_agent.scca.graph_orthogonal import (
    adjacency_matrix_from_neighbors,
    graph_laplacian,
    low_frequency_basis,
    graph_orthogonalize,
)
from data_agent.scca.spatial_diagnostics import SpatialGraph


def test_adjacency_matrix_from_neighbors_is_symmetric():
    graph = SpatialGraph(method="fixture", neighbors=((1,), (0, 2), (1,)))

    adjacency = adjacency_matrix_from_neighbors(graph)

    assert adjacency.shape == (3, 3)
    assert np.allclose(adjacency, adjacency.T)
    assert adjacency[0, 1] == 1.0
    assert adjacency[0, 2] == 0.0


def test_low_frequency_basis_has_requested_components_without_constant():
    graph = SpatialGraph(method="line", neighbors=((1,), (0, 2), (1, 3), (2,)))
    laplacian = graph_laplacian(adjacency_matrix_from_neighbors(graph))

    basis = low_frequency_basis(laplacian, n_components=2)

    assert basis.shape == (4, 2)
    assert np.allclose(basis.mean(axis=0), 0.0, atol=1e-10)
    assert np.allclose(basis.T @ basis, np.eye(2), atol=1e-10)


def test_graph_orthogonalize_removes_basis_projection():
    graph = SpatialGraph(method="line", neighbors=((1,), (0, 2), (1, 3), (2,)))
    basis = low_frequency_basis(graph_laplacian(adjacency_matrix_from_neighbors(graph)), n_components=1)
    residual = basis[:, 0] * 3.0 + np.array([0.2, -0.1, 0.1, -0.2])

    result = graph_orthogonalize(residual, basis)

    assert result.projection_norm_before > result.projection_norm_after
    assert result.projection_norm_after < 1e-10
    assert np.allclose(basis.T @ result.orthogonal_residual, 0.0, atol=1e-10)
