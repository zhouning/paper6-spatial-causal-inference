from __future__ import annotations

import numpy as np
import pandas as pd


NUMERIC_COLUMNS = (
    "deaths",
    "death_dum",
    "dis_bspump",
    "dis_pestf",
    "dis_sewers",
    "pestfield",
    "COORD_X",
    "COORD_Y",
)


def prepare_soho_table(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    for column in NUMERIC_COLUMNS:
        if column in prepared.columns:
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    prepared["bspump_proximity"] = -np.log1p(prepared["dis_bspump"])
    return prepared
