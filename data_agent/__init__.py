"""data_agent package."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _configure_conda_proj_data() -> None:
    if os.environ.get("PROJ_DATA") or os.environ.get("PROJ_LIB"):
        return
    for prefix in (sys.prefix, sys.base_prefix):
        candidate = Path(prefix) / "share" / "proj"
        if (candidate / "proj.db").exists():
            os.environ["PROJ_DATA"] = str(candidate)
            return


_configure_conda_proj_data()
