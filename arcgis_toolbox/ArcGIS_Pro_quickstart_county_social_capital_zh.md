# ArcGIS Pro 快速填写清单：县域社会资本示例

完整手册见同目录：

- `ArcGIS_Pro_使用手册_县域社会资本示例.md`

本文是第一次在 ArcGIS Pro 里跑 `GeoCausalSCCA.pyt` 时可直接照填的精简版。

## 1. 先准备输入表

建议先在 ArcGIS Pro 里运行 `Excel To Table`。

参数：

- Input Excel File:
  `<local ArcGIS export>
- Sheet:
  `CountyData$`
- Output Table:
  `<local ArcGIS export>

如果 `<local ArcGIS export>

## 2. 加载 toolbox

在 Catalog 中添加 folder connection：

- `arcgis_toolbox`

打开：

- `GeoCausalSCCA.pyt`
- `GeoCausal SCCA Analysis`

## 3. GeoCausal SCCA Analysis 参数

| 参数 | 填写值 |
| --- | --- |
| Input Features or Table | `<local ArcGIS export>
| Case Name | `county_social_capital_arcgis_demo` |
| Unit ID Field | `FIPS` |
| Exposure Field | `SocialAssoc` |
| Outcome Field | `AveAgeDeath` |
| Baseline Outcome Field | 留空 |
| Population Field | 留空 |
| Confounding Variables | `UnemployRate; pHHinPoverty; pNoHealthInsur; MentalHealth; pAdultSmoking; pAdultObesity; FastFood; pInsufficientSleep; pAlcohol; pSuicideDeaths; AirPollution` |
| Context Fields | `Shape_Length; Shape_Area` |
| X Coordinate Field | 留空 |
| Y Coordinate Field | 留空 |
| Bootstrap Group Field | `STATE_NAME` |
| Placebo Exposure Fields | `Shape_Length; Shape_Area` |
| Lower Exposure Quantile | `0.01` |
| Upper Exposure Quantile | `0.99` |
| Target Outcome Values | `70` |
| Bootstrap Replicates | `200` |
| Output Report Folder | `paper\ijgis_submission_20260605\07_results` |
| Output Analysis Joined Table | `<local ArcGIS export>
| Output ERF Table | `<local ArcGIS export>
| Output Target Exposure Table | `<local ArcGIS export>
| Output Effect Estimates Table | `<local ArcGIS export>

## 4. 运行后检查

CSV/Markdown/JSON 主输出目录不是 `Output Report Folder` 根目录，而是：

- `paper\ijgis_submission_20260605\07_results\county_social_capital_arcgis_demo`

应看到：

- `analysis.yaml`
- `manifest.json`
- `effect_estimates.csv`
- `erf_curve.csv`
- `target_exposures.csv`
- `analysis_joined.csv`
- `robustness_report.md`

ArcGIS gdb 中应看到：

- `county_social_capital_joined`
- `county_social_capital_erf`
- `county_social_capital_target`
- `county_social_capital_effects`

## 5. 优先看哪张表

优先打开：

- `<local ArcGIS export>

这张表是一行一个县，保留原始字段，并追加 `gc_` 开头的目标暴露结果字段，最适合在 ArcGIS Pro 里 join、制图和筛选。
