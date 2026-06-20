from __future__ import annotations

from typing import Any

from .geocausal_scca_algorithm import GeoCausalSCCAAlgorithm


class GeoCausalProviderSkeleton:
    """Runtime-light provider facade that remains importable without QGIS."""

    PROVIDER_ID = "geocausal"
    PROVIDER_NAME = "GeoCausal"

    def id(self) -> str:
        return self.PROVIDER_ID

    def name(self) -> str:
        return self.PROVIDER_NAME

    def longName(self) -> str:
        return "GeoCausal Processing"

    def loadAlgorithms(self) -> list[GeoCausalSCCAAlgorithm]:
        return [GeoCausalSCCAAlgorithm()]


def create_qgis_provider() -> Any:
    """Create a real QGIS provider when the runtime is available."""
    try:
        from qgis.core import QgsProcessingProvider  # type: ignore
    except ImportError:
        return GeoCausalProviderSkeleton()

    class GeoCausalProvider(QgsProcessingProvider):  # type: ignore[misc]
        def loadAlgorithms(self) -> None:
            self.addAlgorithm(GeoCausalSCCAAlgorithm.create_qgis_algorithm())

        def id(self) -> str:
            return GeoCausalProviderSkeleton.PROVIDER_ID

        def name(self) -> str:
            return GeoCausalProviderSkeleton.PROVIDER_NAME

        def longName(self) -> str:
            return "GeoCausal Processing"

    return GeoCausalProvider()

