# GeoCausal SCCA ArcGIS Pro 使用手册（县域社会资本示例）

## 1. 用途

本文档说明如何在 ArcGIS Pro 中调用：

- `arcgis_toolbox\GeoCausalSCCA.pyt`

并使用已经测试过的县域社会资本数据跑通一个完整示例。

这个 toolbox 是通用工具，不针对当前示例写死字段。本文只是提供一套可以直接照填的示例参数。

## 2. 已验证环境

- ArcGIS Pro Python 环境：
  `D:\Users\zn198\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone3`
- Toolbox 文件：
  `arcgis_toolbox\GeoCausalSCCA.pyt`
- 原始 Excel：
  `<restricted local source>
- 已复制并核验过的示例副本：
  `<local ArcGIS export>

建议优先使用：

- `<local ArcGIS export>

因为这是之前 ArcGIS 与 GeoCausal 对比实验实际使用过的副本。

## 3. 示例数据概况

### 3.1 工作表

- `CountyData`

### 3.2 关键字段

- Unit ID：`FIPS`
- Exposure：`SocialAssoc`
- Outcome：`AveAgeDeath`
- Bootstrap group：`STATE_NAME`

### 3.3 混杂变量

- `UnemployRate`
- `pHHinPoverty`
- `pNoHealthInsur`
- `MentalHealth`
- `pAdultSmoking`
- `pAdultObesity`
- `FastFood`
- `pInsufficientSleep`
- `pAlcohol`
- `pSuicideDeaths`
- `AirPollution`

### 3.4 Context 字段

- `Shape_Length`
- `Shape_Area`

### 3.5 行数

- 总行数：`3108`

## 4. 推荐流程

推荐流程不是直接把 Excel 工作表交给 toolbox，而是：

1. 先把 Excel 导入 file geodatabase。
2. 再把 `.gdb` 里的表作为 toolbox 输入。

原因：

1. ArcGIS Pro 对 Excel 字段类型推断不总是稳定。
2. 输出结果通常也希望直接写回 `.gdb`。
3. 后续做 join、制图、导出更方便。

## 5. 第一步：准备 geodatabase 和输入表

### 5.1 新建 geodatabase

在 ArcGIS Pro 中新建 file geodatabase，例如：

- `<local ArcGIS export>

### 5.2 导入 Excel

在 ArcGIS Pro 的 Geoprocessing 窗口运行：

- `Excel To Table`

参数填写：

- Input Excel File:
  `<local ArcGIS export>
- Sheet:
  `CountyData$`
- Output Table:
  `<local ArcGIS export>

导入完成后，toolbox 输入统一使用：

- `<local ArcGIS export>

## 6. 第二步：加载 toolbox

### 6.1 添加 folder connection

在 ArcGIS Pro 的 Catalog 中添加：

- `arcgis_toolbox`

### 6.2 打开 toolbox

找到：

- `GeoCausalSCCA.pyt`

双击工具：

- `GeoCausal SCCA Analysis`

## 7. 参数速查表

下面这张表可以直接对照 ArcGIS Pro 参数窗口填写。

| ArcGIS Pro 参数名 | 示例值 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| Input Features or Table | `<local ArcGIS export>
| Case Name | `county_social_capital_arcgis_demo` | 是 | 本次运行名称 |
| Unit ID Field | `FIPS` | 否 | 县级唯一标识，建议填写 |
| Exposure Field | `SocialAssoc` | 是 | 社会资本指标 |
| Outcome Field | `AveAgeDeath` | 是 | 平均死亡年龄 |
| Baseline Outcome Field | 留空 | 否 | 本示例不填 |
| Population Field | 留空 | 否 | 本示例不填 |
| Confounding Variables | `UnemployRate; pHHinPoverty; pNoHealthInsur; MentalHealth; pAdultSmoking; pAdultObesity; FastFood; pInsufficientSleep; pAlcohol; pSuicideDeaths; AirPollution` | 否 | 多值字段 |
| Context Fields | `Shape_Length; Shape_Area` | 否 | 上下文/形状代理变量 |
| X Coordinate Field | 留空 | 否 | 本示例没有坐标字段 |
| Y Coordinate Field | 留空 | 否 | 本示例没有坐标字段 |
| Bootstrap Group Field | `STATE_NAME` | 否 | 按州分组 bootstrap |
| Placebo Exposure Fields | `Shape_Length; Shape_Area` | 否 | 作为弱关系对照 |
| Lower Exposure Quantile | `0.01` | 否 | 对齐 ArcGIS 对比实验 |
| Upper Exposure Quantile | `0.99` | 否 | 对齐 ArcGIS 对比实验 |
| Target Outcome Values | `70` | 否 | 生成目标暴露结果 |
| Bootstrap Replicates | `200` | 否 | 与对比实验一致 |
| Output Report Folder | `paper\ijgis_submission_20260605\07_results` | 是 | 主输出根目录，必须是已存在的普通文件夹 |
| Output Analysis Joined Table | `<local ArcGIS export>
| Output ERF Table | `<local ArcGIS export>
| Output Target Exposure Table | `<local ArcGIS export>
| Output Effect Estimates Table | `<local ArcGIS export>

## 8. 参数填写说明

### 8.1 Input Features or Table

填：

- `<local ArcGIS export>

不建议第一次直接选 Excel。

### 8.2 Case Name

示例填：

- `county_social_capital_arcgis_demo`

这个参数非常重要，因为工具实际运行时会把结果写到：

- `Output Report Folder\Case Name\`

也就是本示例最终结果目录会是：

- `paper\ijgis_submission_20260605\07_results\arcgis_toolbox_demo\county_social_capital_arcgis_demo`

不是直接写在 `arcgis_toolbox_demo` 根目录。

### 8.3 坐标字段

本示例没有 `X` / `Y` 字段，所以：

- `X Coordinate Field` 留空
- `Y Coordinate Field` 留空

不要只填一个。

### 8.4 Exposure trim

填：

- Lower Exposure Quantile = `0.01`
- Upper Exposure Quantile = `0.99`

这对应之前 ArcGIS 对比实验的截尾规则。

按这组参数，预期会从 `3108` 行中去掉大约 `64` 行，最终分析样本接近 `3044`。

### 8.5 Target Outcome Values

示例填：

- `70`

如果这里留空：

- `target_exposures.csv` 不会生成
- `analysis_joined.csv` 不会生成
- `Output Analysis Joined Table` 通常也不会有内容

### 8.6 Output Report Folder

这里必须填普通文件夹，例如：

- `paper\ijgis_submission_20260605\07_results`

不要填：

- `.gdb`
- Excel 文件路径
- 单个 `.csv` 文件路径

## 9. 结果文件实际会写到哪里

如果参数为：

- Case Name = `county_social_capital_arcgis_demo`
- Output Report Folder = `paper\ijgis_submission_20260605\07_results`

那么真正的运行目录是：

- `paper\ijgis_submission_20260605\07_results\county_social_capital_arcgis_demo`

该目录下应能看到：

- `input.csv`
- `analysis.yaml`
- `manifest.json`
- `effect_estimates.csv`
- `erf_curve.csv`
- `context_ablation.csv`
- `placebo_tests.csv`
- `bootstrap_robustness.csv`
- `bootstrap_summary.json`
- `erf_stability.json`
- `robustness_report.md`
- `target_exposures.csv`
- `analysis_joined.csv`

## 10. ArcGIS 表输出会写到哪里

如果你按本文填写输出表路径，那么 `.gdb` 中应出现：

- `county_social_capital_joined`
- `county_social_capital_erf`
- `county_social_capital_target`
- `county_social_capital_effects`

这些是 ArcGIS Pro 里后续继续分析和制图时最方便使用的结果表。

## 11. 关键输出怎么理解

### 11.1 `county_social_capital_joined`

这是最适合继续 join 或制图的输出。

特点：

1. 一行对应一个县。
2. 保留原始字段。
3. 追加 `gc_` 开头的结果字段。

如果目标值填的是 `70`，通常能看到类似字段：

- `gc_target_70_required_exposure`
- `gc_target_70_exposure_change`
- `gc_target_70_status`
- `gc_target_70_warning`

其中：

- `gc_target_70_required_exposure`：达到 `70` 所需的暴露值
- `gc_target_70_exposure_change`：相对当前 `SocialAssoc` 还需增加多少
- `gc_target_70_status`：求解是否正常，如 `ok`
- `gc_target_70_warning`：求解警告信息

### 11.2 `county_social_capital_target`

这是长表格式的目标暴露结果。

通常会有两种方法记录：

- `adjusted_ols_prediction`
- `erf_delta_anchor`

如果你要直接做 ArcGIS join，优先看 `county_social_capital_joined`。

如果你要比较两种求解方法，优先看 `county_social_capital_target`。

### 11.3 `county_social_capital_erf`

这是暴露 - 响应曲线表，可用于后续绘图。

### 11.4 `county_social_capital_effects`

这是主效应估计表。通常优先看：

- 主系数符号是否为正
- 区间是否稳定
- 不同估计器方向是否一致

## 12. 本示例的预期结果方向

如果参数按本文填写，预期与之前 ArcGIS/GeoCausal 对比实验方向一致：

1. `SocialAssoc` 对 `AveAgeDeath` 应为正相关方向。
2. ERF 应整体递增。
3. `0.01` / `0.99` 截尾后，样本应接近 `3044`。
4. 能生成以 `70` 为目标值的目标暴露结果。

详细对比记录见：

- `paper\ijgis_submission_20260605\07_results\geocausal_county_arcgis_comparison\arcgis_geocausal_comparison.md`

## 13. 常见问题

### 13.1 toolbox 能加载，但运行时报依赖错误

先确认 ArcGIS Pro 当前使用环境是：

- `D:\Users\zn198\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone3`

### 13.2 直接选 Excel 时报错

按本文推荐流程：

1. 先运行 `Excel To Table`
2. 再使用 `.gdb` 表作为输入

### 13.3 输出表写不进去

常见原因：

1. `Output Report Folder` 填成了 `.gdb` 或一个不存在的文件夹
2. 输出 `.gdb` 还不存在
3. 输出表名已存在且被锁定

### 13.4 没有 target 输出

检查：

- `Target Outcome Values` 是否填写了 `70`

### 13.5 为什么找不到 CSV

最常见原因是去错目录。

请到：

- `Output Report Folder\Case Name\`

下面找，不是在 `Output Report Folder` 根目录直接找。

## 14. 迁移到别的数据时需要改什么

不需要改 toolbox 代码，只需要重新指定参数：

- `Unit ID Field`
- `Exposure Field`
- `Outcome Field`
- `Confounding Variables`
- `Context Fields`
- `Bootstrap Group Field`
- `Target Outcome Values`

也就是说，本文档里的：

- `SocialAssoc`
- `AveAgeDeath`
- `STATE_NAME`

只是当前示例参数，不是工具内部固定要求。
