# SCCA 商业化推进简报：对标 ArcGIS Causal Inference Analysis

日期：2026-06-26

## 一句话定位

SCCA 可以定位为面向 GIS 用户的开放式空间因果诊断工具：它对齐 ArcGIS Pro Causal Inference Analysis 的连续暴露因果分析工作流，并在空间残差诊断、邻近暴露敏感性、图结构稳健性、空间 bootstrap 和证据分级方面形成差异化。

## 为什么对标 ArcGIS

ArcGIS Pro Causal Inference Analysis 已经给 GIS 用户建立了清晰的产品心智：

- 用户选择 exposure、outcome 和 confounders。
- 工具通过倾向得分、匹配或加权构造近似随机实验。
- 工具输出 exposure-response function，支持 target exposure 和 target outcome。
- 结果回到 GIS 表或图层中，方便制图、解释和业务汇报。

这正好是 SCCA 商业化应切入的市场：用户已经理解“GIS 中做因果分析”的需求，但仍缺少更强的空间诊断和证据边界。

## SCCA 的差异化价值

ArcGIS 的强项是把因果分析产品化到 GIS workflow 中。SCCA 的差异化不应是“重新做一个 ArcGIS”，而是增加 ArcGIS 工具链中最容易被忽略的空间证据审计层。

SCCA 可以提供：

1. **空间残差审计**：报告 residual Moran's I，防止空间自相关残留被忽略。
2. **邻近暴露敏感性**：检查相邻地区 exposure 是否仍显著关联 outcome。
3. **空间滞后/SLX 敏感性**：给出 direct、indirect、total effect proxy，帮助业务用户理解空间溢出风险。
4. **图结构敏感性**：比较不同邻接/近邻图下的估计稳定性。
5. **空间 bootstrap**：用空间块重采样降低普通独立样本置信区间的过度自信。
6. **证据分级**：把结果分为 core support 或 bounded support，让商业报告不会过度承诺因果强度。
7. **开放输出**：CSV、JSON、Markdown、GeoPackage、GeoJSON、Shapefile、静态图、HTML 地图和 QGIS 样式都可检查和复用。

## 目标用户

优先目标用户：

- 城市规划和自然资源部门的数据分析人员。
- 环境、公共卫生、交通、土地利用领域的 GIS 分析团队。
- 已经使用 ArcGIS/QGIS，但需要更透明因果分析审计的研究机构和咨询团队。
- 需要把空间分析结果写入报告、论文或政策材料的业务用户。

## MVP 产品形态

第一阶段 MVP 不需要完整重做桌面 GIS 产品。建议先做四个交付件：

1. **ArcGIS Toolbox adapter**：在 ArcGIS Pro 中选择字段并运行 SCCA core。
2. **Notebook/QGIS open workflow**：保证无 ArcGIS 授权时也能复现实验。
3. **Evidence package**：每次运行输出 effect estimates、ERF、balance、overlap、spatial diagnostics、evidence grade 和 Markdown 报告。
4. **Commercial parity report**：自动生成 ArcGIS 对标矩阵，说明哪些功能 matched、partial、gap、SCCA-only differentiator。

## Paper6 的商业化叙事

Paper6 应从“一个学术方法”推进为“一个可产品化的 GIS 因果分析证据审计框架”。

建议论文中明确三层证据：

- **重庆案例**：证明 SCCA 的空间上下文调整逻辑在真实遥感/建筑数据中有效。
- **County social capital case**：作为 ArcGIS-facing commercial parity benchmark，证明 SCCA 能接近 ArcGIS 因果分析工具的业务流程，并进一步输出空间诊断。
- **EPA policy-structure semi-synthetic benchmark**：作为公开政策地理上的空间诊断压力测试，不把它夸大为已完成的 observational AirData validation。

## 当前已具备的商业化基础

仓库已经具备以下基础：

- `geocausal` shared core。
- ArcGIS Pro Python toolbox adapter。
- QGIS provider。
- Notebook workflow。
- County social-capital demo 数据和输出。
- GeoPackage、GeoJSON、Shapefile、PNG、HTML map、QGIS style 输出。
- Evidence synthesis 和 machine-readable evidence-grade rules。

这说明 SCCA 已经不是单纯论文代码，而是有跨界面产品雏形。

## 主要缺口

商业化前需要补齐：

- ArcGIS-compatible 字段命名和输出文档。
- 明确的 propensity score / balancing weight 输出。
- 200 点 ERF curve parity option。
- target outcome 输出合同核查。
- gradient boosting propensity score 作为可选模式。
- ArcGIS-native local ERF popups。
- 更稳定的一键安装和示例工程。

## 风险边界

商业化表达必须避免三个过度承诺：

1. 不说 SCCA 完全替代 ArcGIS。
2. 不说 SCCA 自动解决未观测空间混杂。
3. 不把 bounded support 结果包装成确定因果结论。

正确表达是：

> SCCA makes GIS causal analysis more inspectable, spatially cautious, and reproducible.

中文表达：

> SCCA 让 GIS 因果分析更可检查、更重视空间风险、更容易复现，而不是自动把观测数据变成随机实验。

## 下一步路线

短期：

- 已生成 ArcGIS parity matrix、benchmark summary 和 manifest，后续重点转向字段契约与演示工程。
- 已更新 Paper6 的 county case 叙事，把它明确为 ArcGIS-facing parity benchmark。
- 保持中文商业化 brief、英文论文段落和生成结果同步。

中期：

- 增加 ArcGIS-compatible 输出字段。
- 增加 200 点 ERF parity option。
- 增加 propensity-score trimming 和 gradient boosting propensity score。

长期：

- 开发更完整的 ArcGIS/QGIS 用户界面。
- 增加项目模板、一键运行示例和可视化 dashboard。
- 面向规划、环境、公共卫生和政策评估形成垂直案例库。
