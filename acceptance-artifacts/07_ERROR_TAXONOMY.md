# 07 错因分类与边界规则 v2.1.0

## 芽芽助教项目背景

芽芽助教是一个面向 K12 全学段、多学科场景的自我进化 AI 教学适配引擎。它以真实教材知识图谱为骨架、以学习行为为真值、以错因诊断为核心、以策略调度为动作系统、以成长记忆为长期资产。

一句话：孩子用得越久，芽芽越懂他；芽芽教得越久，越知道怎么教他。

**当前建设范围**：MVP 阶段为人教版小学数学 5–6 年级，第二阶段扩展至 1–4 年级。

**数据底座**：
- 394 个知识点（G1-G4: 205 个，G5-G6: 189 个），全量录入
- 86 个错因（L1 通用 10 个 + L2 数学特有 76 个），全量定义
- 1390 条知识点-错因绑定，394 个 KP 全覆盖
- 两层知识图谱（学习路径层 + 诊断依赖层），G1-G6 全部建成
- 题型规格矩阵（260KB）
- 数据质量门禁 data_quality_gate.py（9 铁规全覆盖）

**引擎架构**：诊断引擎（四步：初筛→匹配→验证→溯源）→ 策略引擎（六态调度）→ 家长摘要（中性安全反馈）→ 质量仪表盘（24 指标）。

**文档集**：14 份规划文档（01-14），覆盖产品愿景、开发路线、教材来源、分级规则、覆盖门禁、知识图谱、错因分类、策略包、事件协议、数据模型、诊断引擎、策略引擎、家长摘要、质量仪表盘。

## 本文档背景

这是芽芽助教产品文档集的第 07 号文件，定义两层错因体系（L1 通用 10 类 + L2 数学专属 76 类）和错因边界规则（如"迁移失败"必须在标准题能做但换场景不会做时才判定）。它回答「学生为什么错」——是诊断引擎 Step 2 匹配错因的参考依据。错因全量定义存储在 `error_taxonomy.json`（86 个错因），知识点-错因绑定在 `error_kp_bindings.json`（1390 条）。

## 两层错因体系

### L1 通用错因 10 类

以下 10 个 L1 错因覆盖跨学科通用错误模式，适用于 K12 全学段。标注了对应的英文 errorCode（引擎和数据库中使用的字段值）。

| # | 中文名 | errorCode |
|---|--------|-----------|
| 1 | 前置知识缺失 | `prerequisite_gap` |
| 2 | 概念混淆 | `concept_confusion` |
| 3 | 题意理解偏差 | `comprehension_bias` |
| 4 | 关键信息遗漏 | `info_omission` |
| 5 | 计算/操作失误 | `calculation_error` |
| 6 | 解题策略缺失 | `strategy_missing` |
| 7 | 迁移失败 | `transfer_failure` |
| 8 | 题型不熟 | `question_type_unfamiliar` |
| 9 | 表达/书写/格式问题 | `expression_format_error` |
| 10 | 记忆提取失败 | `memory_retrieval_failure` |

> **parentExplanation 参考**：每个 L1 错因的家长端中性解释（用于家长摘要引擎，见 13 号文档 §7）已在 `error_taxonomy.json` 中完整定义。以下为摘要参考：
> - prerequisite_gap：孩子在一些需要用到之前学过的知识的题目上遇到了困难，系统正在安排针对性的复习练习来巩固基础。
> - concept_confusion：孩子在做混合练习时偶尔会把相似的概念搞混，我们正在用对比练习帮助孩子建立清晰的区分。
> - comprehension_bias：孩子在做应用题时有时会误解题目的意思，我们在引导孩子用自己的话复述题目来加深理解。
> - info_omission：孩子在做题时偶尔会漏看题目中的一些信息，我们正在训练孩子养成逐条检查题目条件的习惯。
> - calculation_error：孩子的解题思路是对的，只是在计算过程中出现了一些小失误，通过验算练习可以帮助提高准确率。
> - strategy_missing：孩子在面对某些题型时还需要更多方法引导，我们在通过示范例题帮助孩子建立解题框架。
> - transfer_failure：孩子在课本例题上掌握得很好，但在不同场景下运用同样的知识还需要更多练习，这是学习中很正常的阶段。
> - question_type_unfamiliar：孩子对这类题型的答题方式还不太熟悉，我们正在通过示范和练习帮助孩子适应不同的题目形式。
> - expression_format_error：孩子能把题做对，只是在书写格式上还需要养成更规范的习惯，我们在帮助孩子建立检查清单。
> - memory_retrieval_failure：孩子对公式和方法的记忆还需要更多巩固，我们在通过间隔复习帮助孩子把知识从短期记忆转化为长期记忆。

### L2 数学专属错因 76 类

L2 错因已全量定义在 `error_taxonomy.json` 的 `l2_math_specific` 中，覆盖小学数学 1-6 年级全部数学领域。以下列出各领域方向及典型 errorCode 示例。

#### 数与运算（示例）

- 分数单位理解错误（`fraction_unit_misunderstanding`）
- 分数大小比较错误（`fraction_comparison_error`）
- 分子/分母意义混淆（`numerator_denominator_confusion`）
- 分数与除法关系混淆（`fraction_division_confusion`）
- 通分规则错误（`common_denominator_error`）
- 约分遗漏（`simplification_omission`）
- 小数位值理解错误（`decimal_place_value_error`）
- 小数点定位错误（`decimal_point_position_error`）
- 小数/分数/百分数互化错误（`number_format_conversion_error`）
- 运算顺序错误（`operation_order_error`）
- 比和比例意义混淆（`ratio_proportion_confusion`）
- 百分数标准量找错（`percentage_base_error`）

#### 应用题（示例）

- 数量关系识别失败（`quantity_relation_error`）
- 单位"1"找错（`unit_one_error`）
- 比较量/标准量混淆（`comparison_base_confusion`）
- 已知未知关系反了（`known_unknown_reversal`）
- 多步关系断裂（`multi_step_break`）
- 冗余条件干扰（`redundant_info_interference`）
- 逆向推理失败（`reverse_reasoning_failure`）

> 应用题领域的「迁移失败」和「题型不熟」归 L1 层（见 §L1 通用错因），不作为 L2 独立 code。若需应用题场景的细化变体，应在 error_taxonomy.json 中定义新 L2 code（如 word_problem_transfer_failure）。

#### 几何（示例）

- 周长和面积混淆（`perimeter_area_confusion`）
- 表面积和体积混淆（`surface_volume_confusion`）
- 公式适用对象错误（`formula_target_error`）
- 半径/直径混淆（`radius_diameter_confusion`）
- 高/底对应错误（`height_base_mismatch`）
- 圆周率相关公式误用（`pi_formula_misuse`）
- 展开图空间想象错误（`net_spatial_error`）
- 体积单位混淆（`volume_unit_confusion`）

#### 统计与概率（示例）

- 平均数意义理解错误（`mean_understanding_error`）
- 扇形统计图比例读取错误（`pie_chart_ratio_error`）
- 折线图趋势判断错误（`line_chart_trend_error`）
- 可能性大小理解错误（`probability_understanding_error`）

#### 单位与量（示例）

- 长度/面积/体积单位混淆（`measurement_unit_confusion`）
- 时间单位换算错误（`time_conversion_error`）
- 速度/时间/路程关系混淆（`speed_distance_confusion`）
- 单价/数量/总价关系混淆（`price_quantity_confusion`）

> 完整的 76 类 L2 错因定义（含触发条件、排除条件、验证动作、推荐策略、家长端解释）见 `error_taxonomy.json`。

---

## 错因边界样例

> **注**：完整的 86 个错因（10 L1 + 76 L2）的边界规则定义在 `error_taxonomy.json` 中各错因的 `exclusionCondition` 和 `adjacentDifference` 字段。以下仅摘录最有代表性的 3 个 L1 错因边界作为示例。L1 层中最易混淆的错因对（如 `prerequisite_gap` vs `concept_confusion`）的区分边界详见数据文件。

### 计算/操作失误（`calculation_error`）
只有在列式正确、思路正确、计算过程或最终结果错误时才提高概率。如果列式错误，不能优先判为计算失误。

### 迁移失败（`transfer_failure`）
只有在标准题能做、同结构换场景后不能做时才提高概率。如果标准题也不会，不判为迁移失败。

### 题型不熟（`question_type_unfamiliar`）
只有在知识点基础题能做、但看到某类题型不知道步骤时才提高概率。如果看模板后仍不会，应重新判断为概念混淆或解题策略缺失。

---

## 每类错因必须配置

1. 定义（definition）
2. 典型表现（typicalManifestation）
3. 触发条件（triggerCondition）
4. 排除条件（exclusionCondition）
5. 验证动作（validationAction）
6. 相邻错因区别（adjacentDifference）
7. 推荐策略包（recommendedStrategies）
8. 家长端中性解释（parentExplanation）
9. **parentL1 映射**（仅 L2 错因）：每个 L2 错因必须通过 `parentL1` 字段指向其归属的 L1 错因 code（如 `parentL1: "calculation_error"`）。用于家长摘要引擎的 L2 回退规则——当 L2 错因的 `parentExplanation` 意外为空时，回退使用其 `parentL1` 指向的 L1 错因的 `parentExplanation`（见 13 号文档 §7）。

> **注**：字段名均为单数形式（triggerCondition、exclusionCondition 等），与 `error_taxonomy.json` 数据文件一致。`knowledge.json` 中使用复数形式（如 validationActions），两者属不同数据文件，引擎消费时需分别处理。

---

**变更记录**

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v2.1.0 | 2026-05-15 03:07 | 交叉审查修复（4 项）：(1)L2 应用题部分移除 transfer_failure 和 question_type_unfamiliar（归 L1 层），补层级归属说明——若需应用题细化变体应定义新 L2 code；(2)错因边界样例增总注——完整 86 错因边界见 error_taxonomy.json，本文档仅 3 个示例；(3)L1 表后增 parentExplanation 参考区（10 条，来自 error_taxonomy.json），引 13 号 §7；(4)「每类错因必须配置」增第 9 项 parentL1 映射（L2→L1 回退规则基础），底部补字段名单/复数差异说明（error_taxonomy.json 用单数，knowledge.json 用复数） |
| v2.0.0 | 2026-05-15 00:37 | 新增项目背景段和文档背景段。L1 改为中英对照表格（标注 errorCode）。L2 描述改为"已全量定义 76 类"（原"由学科插件注册"已过时）。各错因方向标注对应 errorCode 示例。建设范围更新为 1-6 年级。移除"状态：需扩充"标记。每类错因配置项标注对应字段名。 |
