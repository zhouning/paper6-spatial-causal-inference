# Threshold Sensitivity: SocialAssoc Piecewise Slope

Model: `AveAgeDeath ~ SocialAssoc + max(0, SocialAssoc - knot) + confounders + context`.
Standard errors use HC3 robust covariance. Positive `slope_change_after_knot` means the
social-capital slope is steeper above the knot.

## Knot 13 Summary

| Sample | n | Slope <=13 | Slope >13 | Change after 13 | HC3 p-value | AIC improvement |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| full_sample | 3108 | 0.1155 | 0.1576 | 0.0420 | 0.213 | 2.07 |
| arcgis_trimmed | 3044 | 0.1084 | 0.2123 | 0.1039 | 0.00075 | 17.46 |

## Interpretation

Both samples show a positive slope change after `SocialAssoc = 13`, but the strength of
evidence differs by sample. In the full sample, the change is positive but not statistically
stable. In the ArcGIS-compatible trimmed sample, the slope increase after `13` is positive,
statistically clear, and improves AIC. This supports the ArcGIS slide interpretation that
the ERF becomes steeper beyond about `13` once the same tail-trimming rule is applied.
The result should still be described as a slope increase, not a discontinuous threshold.
