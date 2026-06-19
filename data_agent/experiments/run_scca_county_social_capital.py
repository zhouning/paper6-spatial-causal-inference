from __future__ import annotations

from pathlib import Path

import pandas as pd


NUMERIC_COLUMNS = (
    "OBJECTID",
    "CountyCode",
    "FIPS",
    "AveAgeDeath",
    "SocialAssoc",
    "UnemployRate",
    "pHHinPoverty",
    "pNoHealthInsur",
    "MentalHealth",
    "pAdultSmoking",
    "pAdultObesity",
    "FastFood",
    "pInsufficientSleep",
    "pAlcohol",
    "pSuicideDeaths",
    "AirPollution",
    "Shape_Length",
    "Shape_Area",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results" / "scca_county_social_capital"


def prepare_county_social_capital_table(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    for column in NUMERIC_COLUMNS:
        if column in prepared.columns:
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    for column in ("STATE_NAME", "County"):
        if column in prepared.columns:
            prepared[column] = prepared[column].astype(str)
    return prepared
