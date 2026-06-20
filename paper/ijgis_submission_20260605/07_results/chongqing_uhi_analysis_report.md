# Chongqing UHI Ablation and Robustness Report

- Balance interpretation: `credible_balance`
- Sample size: `5000`
- Treatment threshold: `10` floors

## Ablation Rows

- `raw`: ATT `0.23773722857142587`, max post-match SMD `nan`
- `coordinates_only`: ATT `0.26662119924848376`, max post-match SMD `0.08004424699577341`
- `geometry`: ATT `0.25168778112337814`, max post-match SMD `0.12530482413910446`
- `terrain`: ATT `0.3031107503607498`, max post-match SMD `0.10448622385232399`
- `sentinel_indices`: ATT `0.156651339165025`, max post-match SMD `0.08338257508162271`
- `sentinel_bands`: ATT `0.12145516919797432`, max post-match SMD `0.051095932272656346`
- `full_rs_context`: ATT `0.24412501101612677`, max post-match SMD `0.06130709231666454`
- `pca_context`: ATT `0.2314073873773931`, max post-match SMD `0.06463305428840517`
