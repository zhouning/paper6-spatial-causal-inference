# GeoFM AlphaEarth Ablation Report

- Claim guidance: `geofm_no_clear_gain`
- Input GeoFM columns: `64`
- Runtime sampling: `ok`

## Variants

- `geometry_only`: status `ok`, ATT `0.25168778112337814`, max post-match SMD `0.12530482413910446`
- `geometry_rs_context`: status `ok`, ATT `0.24412501101612677`, max post-match SMD `0.06130709231666454`
- `geometry_alphaearth_64d`: status `ok`, ATT `-0.12993616287094953`, max post-match SMD `0.37592578595911713`
- `geometry_rs_alphaearth_64d`: status `ok`, ATT `0.32604382332642706`, max post-match SMD `0.35698184329287114`
- `geometry_alphaearth_pca`: status `ok`, ATT `0.24098039215685862`, max post-match SMD `0.2676577320301034`
- `geometry_rs_alphaearth_pca`: status `ok`, ATT `0.12357583774249765`, max post-match SMD `0.6759163712129674`
