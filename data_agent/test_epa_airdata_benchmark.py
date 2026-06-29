from __future__ import annotations

import pandas as pd
import pytest


def test_aggregate_airdata_monitor_rows_to_county_year():
    from data_agent.experiments.epa_airdata_benchmark import aggregate_airdata_county_year

    raw = pd.DataFrame(
        {
            "state_code": ["01", "01", "01"],
            "county_code": ["001", "001", "003"],
            "parameter_code": [88101, 88101, 88101],
            "year": [2020, 2020, 2020],
            "arithmetic_mean": [8.0, 10.0, 7.0],
            "observation_count": [100, 300, 50],
        }
    )

    result = aggregate_airdata_county_year(raw, pollutant_code=88101)

    row = result.loc[result["county_fips"] == "01001"].iloc[0]
    assert row["annual_mean"] == pytest.approx(9.5)
    assert row["monitor_count"] == 2
    assert row["observation_count"] == 400
    assert set(result["county_fips"]) == {"01001", "01003"}
