# ArcGIS Pro 布局与导出手册（县域社会资本示例）

本手册说明如何把 `GeoCausal SCCA Analysis` 的输出结果，进一步制作成 ArcGIS Pro 中可直接导出的专题图布局。这里继续使用前面的县域社会资本示例。

## 一、准备条件

在开始布局前，建议你已经完成以下步骤：

1. 已运行 `GeoCausal SCCA Analysis` 工具。
2. 已将 `analysis_joined.csv` 与美国县级边界面图层完成连接。
3. 已将连接结果导出为新的面图层，避免 ArcGIS 临时连接失效。

示例输出目录：

- 结果目录：`D:\adk\paper6-spatial-causal-inference\paper\ijgis_submission_20260605\07_results\arcgis_toolbox_demo\county_social_capital_arcgis_demo`
- 连接后的 CSV：`D:\adk\paper6-spatial-causal-inference\paper\ijgis_submission_20260605\07_results\arcgis_toolbox_demo\county_social_capital_arcgis_demo\analysis_joined.csv`

如果你已经按上一篇连接手册操作过，示例导出的县级面图层可以是：

- `D:\tmp\paper6_arcgis_demo.gdb\county_social_capital_joined`

说明：县级边界面数据不是本仓库自带数据，你需要自行准备带有 `FIPS`、`FIPS5` 或 `GEOID` 等县级编码字段的边界图层。

## 二、建议优先制图的字段

对于当前示例，最适合做地图表达的字段通常是下面三个：

1. `gc_target_70_exposure_change`
   - 含义：如果目标平均死亡年龄设为 70，该县还需要增加多少暴露值。
   - 适合表达“还差多少”的政策缺口。
2. `gc_target_70_required_exposure`
   - 含义：模型推算达到目标结果时所需的暴露水平。
   - 适合表达“目标暴露水平”的空间格局。
3. `gc_target_70_status`
   - 含义：是否已经达到目标。
   - 适合做二元或分类地图。

如果你在工具参数中设置了别的目标结果值，例如 `72`，则会生成对应的：

- `gc_target_72_exposure_change`
- `gc_target_72_required_exposure`
- `gc_target_72_status`

## 三、制作分级设色图

以下以 `gc_target_70_exposure_change` 为例。

1. 在 `Contents` 面板中选中导出的县级面图层，例如 `county_social_capital_joined`。
2. 打开右侧 `Symbology` 面板。
3. `Primary symbology` 选择 `Graduated Colors`。
4. `Field` 选择 `gc_target_70_exposure_change`。
5. `Normalization` 保持为空。
6. `Method` 可先使用：
   - `Natural Breaks (Jenks)`，适合自然分布展示；
   - 或 `Quantile`，适合做分位数比较。
7. `Classes` 建议先设为 `5`。
8. 颜色带建议选择单向渐变色带，避免过于花哨。

对于论文图件，建议优先使用：

- 单色系浅到深渐变，表达“缺口从低到高”；
- 或冷暖对比但层次克制的连续色带。

如果字段同时包含正负值，可改用发散色带，使 `0` 附近成为中间色。

## 四、处理空值与异常值

有些县可能因为连接失败、缺失值或模型警告而出现空值。建议这样处理：

1. 在 `Symbology` 中检查是否有 `NoData` 或 `<Null>`。
2. 将空值设置为浅灰色。
3. 在图例中明确空值类别，避免被误读为数值很低。

如果个别县数值极端，导致整体颜色被拉伸：

1. 先检查是否是数据连接错误。
2. 若为真实极端值，可考虑：
   - 改用 `Quantile`；
   - 手工调整分级断点；
   - 或同时输出一张去极值后的展示图，但正文中应说明处理方式。

## 五、制作目标达成状态图

如果你想直接表达“是否已达到目标平均死亡年龄”，可对 `gc_target_70_status` 制图。

建议步骤：

1. 在 `Symbology` 中选择 `Unique Values`。
2. `Field 1` 选择 `gc_target_70_status`。
3. 常见取值包括：
   - `meets_target`
   - `below_target`
   - 以及可能的空值或警告状态
4. 建议颜色：
   - `meets_target`：较深绿色
   - `below_target`：橙色或红色
   - 空值：灰色

这种图适合放在正文主图中，因为解释直接。

## 六、设置标注与底图

论文制图一般不建议保留复杂底图。建议：

1. 关闭或弱化在线底图。
2. 县界保留细边线，颜色不要太重。
3. 州界如果可用，可适当加粗一点，帮助读者识别区域结构。

如果需要州名或区域名：

1. 只标注少量关键州或区域。
2. 不要让文字覆盖主要色块。

## 七、新建布局页面

1. 顶部菜单选择 `Insert`。
2. 点击 `New Layout`。
3. 常用选择：
   - `A4 Landscape`
   - 或 `Letter Landscape`

如果地图是论文主图，推荐横向页面，便于放下完整美国县级分布。

## 八、插入地图框与图面要素

在新布局中按以下顺序操作：

1. `Insert` -> `Map Frame`
2. 选择包含县级结果图层的地图
3. 在页面上拖出主地图框

然后按需添加：

1. `Legend`
2. `North Arrow`
3. `Scale Bar`
4. `Text`

论文图件建议尽量克制：

1. 图例保留，但不要太大。
2. 指北针和比例尺只有在确实需要时再放。
3. 标题可以不放在图内，而在论文排版中作为图题说明。

## 九、建议的版式结构

对于单幅县级结果图，推荐版式：

1. 主地图居中，占据页面大部分宽度。
2. 图例放右下角或右侧中部。
3. 若有 Alaska、Hawaii 等缩略图，可单独做 inset。
4. 四周留白保持均衡，不要把元素堆得太满。

如果你要做论文多面板图，可以在同一布局中并排放置：

1. `gc_target_70_exposure_change`
2. `gc_target_70_required_exposure`
3. `gc_target_70_status`

这样能同时展示“缺口”“目标水平”“是否达标”三类信息。

## 十、导出高质量图片

布局完成后：

1. 点击 `Share`。
2. 选择 `Export Layout`。
3. 常用导出格式：
   - `PDF`：适合论文和汇报
   - `PNG`：适合 PPT
   - `TIFF`：适合高质量投稿图件

建议参数：

- 分辨率：`300 dpi` 起步
- 若投稿要求较高，可用 `600 dpi`
- 颜色模式按期刊要求设置

如果导出 PNG 用于 PPT，建议：

- 保持白色背景；
- 宽度足够大，避免放大后失真。

## 十一、与当前示例对应的最小可复现实操路径

如果你想直接复现一个最简流程，可按下面路径操作：

1. 运行工具，得到：
   - `D:\adk\paper6-spatial-causal-inference\paper\ijgis_submission_20260605\07_results\arcgis_toolbox_demo\county_social_capital_arcgis_demo\analysis_joined.csv`
2. 将该表与县级边界面图层按 `FIPS` 或 `GEOID` 连接。
3. 导出连接后的面图层，例如：
   - `D:\tmp\paper6_arcgis_demo.gdb\county_social_capital_joined`
4. 对 `gc_target_70_exposure_change` 做 `Graduated Colors` 分级设色图。
5. 插入 `Layout`，添加图例并导出 `PDF` 或 `PNG`。

## 十二、论文表达建议

从论文图件角度看，当前工具输出最值得优先展示的不是原始暴露值，而是模型推导出的决策型结果字段，例如：

1. `gc_target_70_exposure_change`
2. `gc_target_70_required_exposure`
3. `gc_target_70_status`

这三类字段比单纯展示 `SocialAssoc` 原值更能体现你的方法价值，因为它们对应的是：

1. 可解释的因果目标；
2. 可操作的政策缺口；
3. 可直接落到空间决策的分区结果。

这也是你的开源工具与一般相关性制图相比更有方法意义的地方。
