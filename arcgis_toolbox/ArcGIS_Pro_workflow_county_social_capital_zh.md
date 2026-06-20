# ArcGIS Pro 实操流程：县域社会资本示例

本文档按 ArcGIS Pro 里的实际操作顺序组织，适合第一次上手时边点边看。

完整说明见：

- `ArcGIS_Pro_使用手册_县域社会资本示例.md`

快速参数表见：

- `ArcGIS_Pro_quickstart_county_social_capital_zh.md`

## 1. 目标

用 ArcGIS Pro 调用 `GeoCausalSCCA.pyt`，基于县域社会资本数据生成：

1. 主效应结果表
2. ERF 曲线表
3. 目标暴露结果表
4. 一行一个县的 joined 结果表

如果你手里只有 Excel 表，本流程可以跑通分析，但不能直接出县级专题地图。

如果你还拥有县界面要素，并且其中也有 `FIPS` 字段，那么可以把 joined 结果再关联到县面图层上做地图表达。

## 2. 你需要准备什么

### 2.1 必需文件

- Toolbox：
  `D:\adk\paper6-spatial-causal-inference\arcgis_toolbox\GeoCausalSCCA.pyt`
- 示例 Excel：
  `D:\tmp\paper6_county_social_capital.xlsx`

### 2.2 建议准备的 geodatabase

- `D:\tmp\paper6_arcgis_demo.gdb`

### 2.3 推荐结果目录

- `D:\adk\paper6-spatial-causal-inference\paper\ijgis_submission_20260605\07_results`

## 3. 在 ArcGIS Pro 中准备输入表

### 步骤 1：打开 ArcGIS Pro

打开一个空项目即可。

### 步骤 2：新建 file geodatabase

在 Catalog 或目录窗格中，新建：

- `paper6_arcgis_demo.gdb`

建议路径：

- `D:\tmp\paper6_arcgis_demo.gdb`

### 步骤 3：把 Excel 导入 geodatabase

打开 Geoprocessing，搜索并运行：

- `Excel To Table`

填写：

- Input Excel File:
  `D:\tmp\paper6_county_social_capital.xlsx`
- Sheet:
  `CountyData$`
- Output Table:
  `D:\tmp\paper6_arcgis_demo.gdb\county_social_capital`

运行完成后，你应该在 geodatabase 里看到：

- `county_social_capital`

## 4. 加载 GeoCausal toolbox

### 步骤 4：添加 folder connection

在 Catalog 中添加：

- `D:\adk\paper6-spatial-causal-inference\arcgis_toolbox`

### 步骤 5：打开工具

找到：

- `GeoCausalSCCA.pyt`

展开后双击：

- `GeoCausal SCCA Analysis`

## 5. 填写工具参数

### 步骤 6：填写输入与变量

| 参数 | 示例值 |
| --- | --- |
| Input Features or Table | `D:\tmp\paper6_arcgis_demo.gdb\county_social_capital` |
| Case Name | `county_social_capital_arcgis_demo` |
| Unit ID Field | `FIPS` |
| Exposure Field | `SocialAssoc` |
| Outcome Field | `AveAgeDeath` |
| Baseline Outcome Field | 留空 |
| Population Field | 留空 |

### 步骤 7：填写混杂、context 与稳健性参数

| 参数 | 示例值 |
| --- | --- |
| Confounding Variables | `UnemployRate; pHHinPoverty; pNoHealthInsur; MentalHealth; pAdultSmoking; pAdultObesity; FastFood; pInsufficientSleep; pAlcohol; pSuicideDeaths; AirPollution` |
| Context Fields | `Shape_Length; Shape_Area` |
| X Coordinate Field | 留空 |
| Y Coordinate Field | 留空 |
| Bootstrap Group Field | `STATE_NAME` |
| Placebo Exposure Fields | `Shape_Length; Shape_Area` |

注意：

1. `X Coordinate Field` 和 `Y Coordinate Field` 本例都留空。
2. 不要只填一个坐标字段。

### 步骤 8：填写预处理与目标参数

| 参数 | 示例值 |
| --- | --- |
| Lower Exposure Quantile | `0.01` |
| Upper Exposure Quantile | `0.99` |
| Target Outcome Values | `70` |
| Bootstrap Replicates | `200` |

### 步骤 9：填写输出参数

| 参数 | 示例值 |
| --- | --- |
| Output Report Folder | `D:\adk\paper6-spatial-causal-inference\paper\ijgis_submission_20260605\07_results` |
| Output Analysis Joined Table | `D:\tmp\paper6_arcgis_demo.gdb\county_social_capital_joined` |
| Output ERF Table | `D:\tmp\paper6_arcgis_demo.gdb\county_social_capital_erf` |
| Output Target Exposure Table | `D:\tmp\paper6_arcgis_demo.gdb\county_social_capital_target` |
| Output Effect Estimates Table | `D:\tmp\paper6_arcgis_demo.gdb\county_social_capital_effects` |

## 6. 运行后先看哪里

### 步骤 10：先看 ArcGIS 消息窗口

运行结束后，优先看 Geoprocessing 窗口底部的 messages。

重点看：

1. `Rows analyzed`
2. `Exposure trimming removed ... records`
3. `Output folder`

`Output folder` 显示的才是真正的运行目录。

本示例应接近：

- `D:\adk\paper6-spatial-causal-inference\paper\ijgis_submission_20260605\07_results\county_social_capital_arcgis_demo`

### 步骤 11：检查 gdb 结果表

在 `D:\tmp\paper6_arcgis_demo.gdb` 中查看：

- `county_social_capital_joined`
- `county_social_capital_erf`
- `county_social_capital_target`
- `county_social_capital_effects`

第一次看结果时，优先打开：

- `county_social_capital_joined`

## 7. 如果你只有 Excel 表，能做什么

如果你只有 `county_social_capital` 这张表，没有县界面图层，那么你现在可以做的是：

1. 看 `county_social_capital_joined` 中的 `gc_` 字段
2. 按 `gc_target_70_required_exposure` 排序
3. 按 `gc_target_70_exposure_change` 筛选出最需要提升社会资本的县
4. 查看 `county_social_capital_erf` 和 `county_social_capital_effects`

但这时你不能直接做县面专题图，因为输入只是表，不是面图层。

## 8. 如果你有县界面图层，怎么做专题图

### 前提

你需要有一个县级 polygon 图层，并且该图层中也有：

- `FIPS`

字段。

### 步骤 12：把县界图层加到地图中

把县界面图层加载到当前 Map。

### 步骤 13：做表连接

对县界图层执行 join：

- Join field on polygon layer: `FIPS`
- Join table: `county_social_capital_joined`
- Join table field: `FIPS`

### 步骤 14：做专题表达

优先尝试以下字段：

- `gc_target_70_required_exposure`
- `gc_target_70_exposure_change`

推荐表达方式：

1. Graduated Colors
2. 5 或 7 个等级
3. 先看自然断点，再看分位数

### 步骤 15：检查异常值和空值

如果某些县为空值，优先检查：

1. `FIPS` 字段类型是否一致
2. `FIPS` 是否存在前导零丢失问题
3. join 前后字段是否都是同一编码形式

## 9. 这次运行应看到的方向性结果

按本文示例参数，预期方向应为：

1. `SocialAssoc` 对 `AveAgeDeath` 为正向关系
2. ERF 整体递增
3. 截尾后分析样本接近 `3044`
4. 可以生成以 `70` 为目标值的 target 输出

## 10. 最常见的误区

### 误区 1：把 Output Report Folder 当成最终结果目录

不是。

真正结果目录是：

- `Output Report Folder\Case Name\`

### 误区 2：只有表也想直接画县面地图

不行。

只有表时只能看属性结果；要画县面专题图，必须另有县界 polygon 图层。

### 误区 3：Target Outcome Values 留空还希望有 joined target 结果

如果留空，就不会生成：

- `target_exposures.csv`
- `analysis_joined.csv`

### 误区 4：把普通文件夹和 `.gdb` 混用

- `Output Report Folder` 必须是普通文件夹
- `Output ... Table` 应当写到 `.gdb` 中
