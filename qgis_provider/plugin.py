from __future__ import annotations

import sys
from pathlib import Path


def _ensure_repo_root_on_path() -> None:
    plugin_dir = Path(__file__).resolve().parent
    for candidate in (plugin_dir.parent, *plugin_dir.parents):
        if (candidate / "geocausal" / "adapters.py").exists():
            candidate_text = str(candidate)
            if candidate_text not in sys.path:
                sys.path.insert(0, candidate_text)
            return


_ensure_repo_root_on_path()

from .provider import create_qgis_provider


class GeoCausalPlugin:
    """Minimal QGIS plugin entrypoint that registers the processing provider."""

    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.registry = None

    @staticmethod
    def _processing_registry(iface):
        try:
            from qgis.core import QgsApplication  # type: ignore

            return QgsApplication.processingRegistry()
        except Exception:
            return getattr(iface, "processingRegistry", lambda: None)()

    def initGui(self) -> None:
        self.initProcessing()

    def initProcessing(self) -> None:
        self.provider = create_qgis_provider()
        self.registry = self._processing_registry(self.iface)
        if self.registry is not None:
            self.registry.addProvider(self.provider)

    def unload(self) -> None:
        if self.registry is not None and self.provider is not None:
            self.registry.removeProvider(self.provider)
        self.provider = None
        self.registry = None


def classFactory(iface):
    return GeoCausalPlugin(iface)
