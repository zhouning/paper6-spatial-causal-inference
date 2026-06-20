# ArcGIS Pro 县界图层 Join 与专题图手册（县域社会资本示例）

本文档说明如何把 `GeoCausal SCCA Analysis` 的输出结果，关联到县界 polygon 图层上并制作专题图。

前提是你已经完成了 GeoCausal toolbox 运行，并且其 `Output Report Folder` 使用的是一个已存在的普通文件夹，例如：

- `D:\adk\paper6-spatial-causal-inference\paper\ijgis_submission_20260605\07_results`

并得到了：

- `county_social_capital_joined`

这张 ArcGIS 表。

## 1. 这份手册解决什么问题

GeoCausal toolbox 本身输出的是：

1. 结果 CSV
2. ArcGIS 结果表

如果输入只是 Excel 表或普通 ArcGIS 表，那么它不会自动变成县面地图。

要画县级专题图，你还需要：

1. 一个美国县界 polygon 图层
2. 该图层中有能够与结果表对上的县级 ID 字段，优先是 `FIPS`

## 2. 你至少需要哪些数据

### 2.1 已经跑完的 GeoCausal 结果表

推荐使用：

- `D:\tmp\paper6_arcgis_demo.gdb\county_social_capital_joined`

### 2.2 另一个县界 polygon 图层

这个仓库里目前没有现成的美国县界面要素，所以这一步需要你自己提供。

理想条件是该图层至少有以下之一：

1. `FIPS`
2. `GEOID`
3. 州县代码可拼成 5 位县级标识

如果字段不是 `FIPS`，也可以做，但需要先整理成可以与结果表对应的 join 字段。

## 3. 先理解 join 的关键点

`county_social_capital_joined` 里推荐作为关联键的字段是：

- `FIPS`

但 ArcGIS Pro 里最容易失败的地方不是字段名，而是字段类型和编码形式。

最常见问题有两个：

1. 一边是数值型 `1001`，另一边是文本型 `01001`
2. 前导零丢失，导致本该 5 位的县代码变成了 4 位或更短

所以在 join 前，先检查：

1. 县界图层的 join 字段类型
2. 结果表的 `FIPS` 字段类型
3. 两边是否都是 5 位县代码

## 4. 推荐的两种 join 方式

### 方式 A：临时 Join

适合：

1. 先看图
2. 还不确定字段处理是否正确
3. 不想立刻生成新要素类

ArcGIS Pro 里可用：

- `Add Join`

### 方式 B：永久 Join

适合：

1. 已确认字段没问题
2. 准备做正式制图
3. 想输出一个新的专题图要素类

ArcGIS Pro 里可用：

- `Join Field`
- 或先 `Add Join` 再 `Export Features`

第一次操作时，建议先做方式 A。

## 5. 第一步：检查两个表的 join 字段

### 5.1 打开结果表

打开：

- `county_social_capital_joined`

确认有：

- `FIPS`

以及需要制图的结果字段，例如：

- `gc_target_70_required_exposure`
- `gc_target_70_exposure_change`
- `gc_target_70_status`

### 5.2 打开县界图层属性表

确认是否有以下字段之一：

- `FIPS`
- `GEOID`

### 5.3 判断是否需要新建文本 join 字段

如果县界图层中的县代码是数值型，而 `county_social_capital_joined` 里的 `FIPS` 以文本方式保存，建议先统一为文本 5 位代码。

## 6. 第二步：必要时创建标准 5 位 FIPS 文本字段

如果两边类型不一致，推荐在县界图层里新建一个文本字段，例如：

- `FIPS5`

字段类型：

- Text

字段长度：

- 5

然后用字段计算器把县级代码统一成 5 位文本。

### 6.1 如果现有字段是数值型 FIPS

字段计算器表达式的目标是把它转成 5 位字符串，例如：

- `1001` 变成 `01001`

在 ArcGIS Pro Python 表达式里可按这个思路：

```python
str(!FIPS!).zfill(5)
```

### 6.2 如果现有字段是 GEOID

如果 `GEOID` 已经是 5 位文本，那么通常可直接使用，不必再建新字段。

## 7. 第三步：临时 Add Join

在 Geoprocessing 中运行：

- `Add Join`

示例填写：

- Input Table:
  你的县界 polygon 图层
- Input Join Field:
  `FIPS` 或 `FIPS5` 或 `GEOID`
- Join Table:
  `D:\tmp\paper6_arcgis_demo.gdb\county_social_capital_joined`
- Join Table Field:
  `FIPS`

运行后，先不要急着做符号化，先打开属性表确认是否 join 成功。

## 8. 第四步：判断 join 是否成功

成功时应看到：

1. 县界图层属性表里多出 `county_social_capital_joined` 的字段
2. 例如能看到：
   - `gc_target_70_required_exposure`
   - `gc_target_70_exposure_change`
   - `gc_target_70_status`
3. 空值不是大面积铺满全表

如果大量为空，优先检查：

1. 两边字段是否真的一一对应
2. 是否存在前导零丢失
3. 是否一边是州县拼接代码，另一边只有县代码

## 9. 第五步：制作专题图

推荐首先尝试两个字段：

1. `gc_target_70_required_exposure`
2. `gc_target_70_exposure_change`

这两个字段的解释分别是：

1. 为了达到目标平均死亡年龄 `70`，该县所需的社会资本水平
2. 相对当前社会资本，还需要增加多少

### 9.1 打开符号系统

选中 join 后的县界图层，打开：

- `Symbology`

### 9.2 选择表达方式

选择：

- `Graduated Colors`

### 9.3 选择字段

Field 选择：

- `gc_target_70_exposure_change`

这是最容易解释的一张图：哪几个县还需要更大的社会资本提升幅度。

### 9.4 分类方式建议

建议尝试两种：

1. Natural Breaks
2. Quantile

建议等级数：

1. `5`
2. 或 `7`

### 9.5 空值处理

如果有少量空值，可单独设置为灰色。

如果空值很多，不要继续调色，先回去检查 join。

## 10. 第六步：导出永久结果

如果临时 Add Join 的结果已经正确，建议导出一个新的专题图图层。

方法：

1. 右键 join 后的图层
2. `Data`
3. `Export Features`

输出到新的 `.gdb` 要素类，例如：

- `D:\tmp\paper6_arcgis_demo.gdb\county_social_capital_map_ready`

这样之后开图、调符号、做布局都更稳。

## 11. 推荐做的三张图

### 图 1：目标增量图

字段：

- `gc_target_70_exposure_change`

含义：

哪些县距离达到目标值 `70` 还差得最远。

### 图 2：目标暴露水平图

字段：

- `gc_target_70_required_exposure`

含义：

如果要达到目标值 `70`，不同县所需社会资本水平分别是多少。

### 图 3：状态图

字段：

- `gc_target_70_status`

含义：

哪些县的目标反推是正常求得的，哪些县处于 ERF 支持范围外。

这个图更偏诊断用途，不一定放进论文主文。

## 12. 最常见错误

### 错误 1：join 字段都是 FIPS，但还是 join 不上

通常是因为：

1. 一边是数字
2. 一边是文本
3. 前导零丢失

### 错误 2：临时 join 成功，但导出后字段不见了

通常是导出时选错了图层，或者导出前 join 没真正挂在当前图层上。

### 错误 3：直接拿 Excel 结果去和 polygon 图层 join

可以，但不推荐。

更稳的做法是先使用 toolbox 输出到：

- `county_social_capital_joined`

然后再和 polygon 图层关联。

### 错误 4：把 `gc_target_70_required_exposure` 和 `gc_target_70_exposure_change` 混为一谈

二者不是一回事：

1. `required_exposure` 是目标水平
2. `exposure_change` 是相对当前值还差多少

做政策解释时，通常优先看：

- `gc_target_70_exposure_change`
