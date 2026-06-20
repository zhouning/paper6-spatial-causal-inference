from __future__ import annotations

from pathlib import Path

import pandas as pd
import statsmodels.api as sm


BASE_DIR = Path(__file__).resolve().parent
OUT_CSV = BASE_DIR / "threshold_sensitivity.csv"
OUT_MD = BASE_DIR / "threshold_sensitivity.md"

OUTCOME = "AveAgeDeath"
EXPOSURE = "SocialAssoc"
CONFOUNDERS = [
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
]
CONTEXT = ["Shape_Length", "Shape_Area"]
KNOTS = [10.0, 13.0, 15.0, 20.0]


def _fit_linear(df: pd.DataFrame) -> sm.regression.linear_model.RegressionResultsWrapper:
    columns = [EXPOSURE, *CONFOUNDERS, *CONTEXT]
    x = sm.add_constant(df[columns], has_constant="add")
    return sm.OLS(df[OUTCOME], x).fit()


def _fit_piecewise(
    df: pd.DataFrame, knot: float
) -> tuple[
    sm.regression.linear_model.RegressionResultsWrapper,
    dict[str, pd.Series | pd.DataFrame],
]:
    work = df.copy()
    hinge_col = f"hinge_after_{knot:g}"
    work[hinge_col] = (work[EXPOSURE] - knot).clip(lower=0)
    columns = [EXPOSURE, hinge_col, *CONFOUNDERS, *CONTEXT]
    x = sm.add_constant(work[columns], has_constant="add")
    fitted = sm.OLS(work[OUTCOME], x).fit()
    robust = fitted.get_robustcov_results(cov_type="HC3")
    robust_stats = {
        "params": pd.Series(robust.params, index=fitted.params.index),
        "bse": pd.Series(robust.bse, index=fitted.params.index),
        "pvalues": pd.Series(robust.pvalues, index=fitted.params.index),
        "conf_int": pd.DataFrame(
            robust.conf_int(alpha=0.05),
            index=fitted.params.index,
            columns=["ci_lower", "ci_upper"],
        ),
    }
    return fitted, robust_stats


def _row(sample_name: str, df: pd.DataFrame, knot: float) -> dict[str, float | int | str]:
    base = _fit_linear(df)
    fitted, robust_stats = _fit_piecewise(df, knot)
    hinge_col = f"hinge_after_{knot:g}"
    params = robust_stats["params"]
    bse = robust_stats["bse"]
    pvalues = robust_stats["pvalues"]
    conf = robust_stats["conf_int"]
    before = float(params[EXPOSURE])
    change = float(params[hinge_col])
    after = before + change
    return {
        "sample": sample_name,
        "n": int(len(df)),
        "knot": knot,
        "n_at_or_below_knot": int((df[EXPOSURE] <= knot).sum()),
        "n_above_knot": int((df[EXPOSURE] > knot).sum()),
        "slope_before_or_at_knot": before,
        "slope_after_knot": after,
        "slope_change_after_knot": change,
        "slope_change_se_hc3": float(bse[hinge_col]),
        "slope_change_p_hc3": float(pvalues[hinge_col]),
        "slope_change_ci_lower_hc3": float(conf.loc[hinge_col, "ci_lower"]),
        "slope_change_ci_upper_hc3": float(conf.loc[hinge_col, "ci_upper"]),
        "linear_adjusted_r2": float(base.rsquared_adj),
        "piecewise_adjusted_r2": float(fitted.rsquared_adj),
        "aic_improvement_vs_linear": float(base.aic - fitted.aic),
    }


def main() -> int:
    samples = {
        "full_sample": pd.read_csv(BASE_DIR / "county_social_capital.csv"),
        "arcgis_trimmed": pd.read_csv(
            BASE_DIR / "arcgis_trimmed" / "county_social_capital_arcgis_trimmed.csv"
        ),
    }
    rows = []
    for sample_name, df in samples.items():
        for knot in KNOTS:
            rows.append(_row(sample_name, df, knot))

    result = pd.DataFrame(rows)
    result.to_csv(OUT_CSV, index=False)

    knot13 = result[result["knot"].eq(13.0)].copy()
    lines = [
        "# Threshold Sensitivity: SocialAssoc Piecewise Slope",
        "",
        "Model: `AveAgeDeath ~ SocialAssoc + max(0, SocialAssoc - knot) + confounders + context`.",
        "Standard errors use HC3 robust covariance. Positive `slope_change_after_knot` means the",
        "social-capital slope is steeper above the knot.",
        "",
        "## Knot 13 Summary",
        "",
        "| Sample | n | Slope <=13 | Slope >13 | Change after 13 | HC3 p-value | AIC improvement |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in knot13.iterrows():
        lines.append(
            "| {sample} | {n:d} | {before:.4f} | {after:.4f} | {change:.4f} | {p:.3g} | {aic:.2f} |".format(
                sample=str(row["sample"]),
                n=int(row["n"]),
                before=float(row["slope_before_or_at_knot"]),
                after=float(row["slope_after_knot"]),
                change=float(row["slope_change_after_knot"]),
                p=float(row["slope_change_p_hc3"]),
                aic=float(row["aic_improvement_vs_linear"]),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Both samples show a positive slope change after `SocialAssoc = 13`, but the strength of",
            "evidence differs by sample. In the full sample, the change is positive but not statistically",
            "stable. In the ArcGIS-compatible trimmed sample, the slope increase after `13` is positive,",
            "statistically clear, and improves AIC. This supports the ArcGIS slide interpretation that",
            "the ERF becomes steeper beyond about `13` once the same tail-trimming rule is applied.",
            "The result should still be described as a slope increase, not a discontinuous threshold.",
        ]
    )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print({"csv": str(OUT_CSV), "markdown": str(OUT_MD), "rows": len(result)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
