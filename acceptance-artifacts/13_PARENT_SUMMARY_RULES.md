# 13 家长端摘要安全规则 v2.0

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | - | 初始版本：69行，摘要公式+禁止词+推荐表达+家长反馈 |
| 2.0 | 2026-05-14 | 对齐数据底座：摘要生成从 diagnosis_updated 事件取数据；补全 parentSafeExplanation 模板体系；新增风险评分算法；新增家长反馈闭环；Phase 1 实现范围 |

---

## 芽芽助教项目背景

芽芽助教是一个面向 K12 全学段、多学科场景的自我进化 AI 教学适配引擎。它以真实教材知识图谱为骨架、以学习行为为真值、以错因诊断为核心、以策略调度为动作系统、以成长记忆为长期资产。

一句话：孩子用得越久，芽芽越懂他；芽芽教得越久，越知道怎么教他。

**当前建设范围**：人教版小学数学 1-6 年级全量覆盖。

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

这是芽芽助教产品文档集的第 13 号文件，定义家长摘要的生成模板（shortSummary/fullSummary/progress）、风险评分算法、禁止词清单和家长反馈闭环。它回答「怎么让家长看到 AI 做了什么支持，而不是孩子被贴了什么标签」——消费 diagnosis_updated 和 strategy_applied 事件，结合 error_taxonomy.json 的 parentSafeExplanation 字段生成摘要。

## 一、目标

家长端摘要的核心原则：**让家长看到 AI 做了什么支持，而不是看到孩子被贴了什么标签。**

每一份摘要回答三个问题：
1. 孩子今天学了什么？
2. 芽芽做了什么？
3. 接下来可以怎么做？

## 二、输入数据源

| 数据源 | 字段 | 用途 |
|--------|------|------|
| diagnosis_updated 事件 | mainHypothesis.errorCode | 定位到具体错因 |
| diagnosis_updated 事件 | diagnosisStatus | 判断是确诊/排除/不确定，影响措辞 |
| error_taxonomy.json | parentSafeExplanation | 每个错因的"安全版解释"，作为摘要母版 |
| answer_submitted 事件 | 具体题目、学生回答 | 填充摘要中的具体细节 |
| lesson_completed 事件 | questionCount, correctCount | 课堂整体数据 |
| GrowthMemory | masteryScore | 长期进步对比 |

## 三、摘要模板

### 3.1 模板结构

```
【一句话亮点】{shortSummary}

【课堂回顾】{fullSummary}

【成长看得见】{progress}
```

### 3.2 shortSummary 生成规则

```
function generateShort(status, errorCode, questionContext):
  safeExplanation = errorTaxonomy[errorCode].parentSafeExplanation

  if status == "confirmed":
    return safeExplanation.replace("孩子", "孩子今天")
  if status == "confirmed_with_reservation":
    return "今天孩子在" + questionContext.topic + "上有些犹豫，芽芽在继续观察"
  if status == "inconclusive":
    return "今天孩子在" + questionContext.topic + "上遇到了一点挑战，芽芽降低了难度来帮助"
  if status == "excluded":
    return "芽芽排除了一个可能的困难点，正在更准确地找到孩子需要帮助的地方"
  if status == "traced":
    return "芽芽发现孩子可能需要先巩固" + prerequisiteName + "的基础，正在帮助中"
```

### 3.3 fullSummary 生成规则

```
【当前学习现象】
从 answer_submitted 提取：哪道题、答了什么、花了多久
用 parentSafeExplanation 的中性表达改写

【芽芽做了什么支持】
从 strategy_applied 提取：用了什么策略
从 error_taxonomy 提取：该策略的作用

【孩子的积极变化 / 下一步建议】
如果 diagnosisStatus = confirmed 且策略有效 → 描述变化
如果 diagnosisStatus = in_progress → 描述"芽芽正在观察"
如果 effectScore >= 1 → 强调进步
如果 effectScore <= 0 → 强调"继续用另一种方式帮助"
```

### 3.4 完整示例

推荐版本：

> 今天孩子在"百分数应用题"里，一开始对"谁是单位1"有些犹豫。芽芽用图示把两个数量关系摆出来后，孩子能自己选出正确关系。后面可以继续用"先找单位1"的小步骤练几次。

避免版本：

> 孩子百分数应用题薄弱，单位1经常找错，需要加强训练。

## 四、禁止内容

### 4.1 禁止词列表

粗心 / 注意力差 / 反应慢 / 不擅长 / 落后 / 抗挫差 / 情绪差 / 能力弱 / 不认真 / 没天赋 / 理解力差 / 逻辑弱 / 经常 / 总是 / 明显差 / 跟不上 / 不行 / 太差

### 4.2 禁止表达模式

```
孩子存在 XXX 问题
孩子 XXX 能力弱
孩子经常 XXX
孩子不适合 XXX
孩子明显落后于同龄人
XXX 是孩子的弱项
需要加强 XXX（暗示不足）
```

### 4.3 禁止数据

- 不出现具体分数/排名
- 不出现与其他孩子的对比
- 不出现"正确率 30%"这类绝对数字
- 可以用"正确率有进步""比上次更好"这类趋势表达

## 五、风险评分

每份摘要计算 riskScore ∈ [0, 1]：

| 风险因素 | 惩罚 | 说明 |
|----------|------|------|
| 含有禁止词 | +0.3/词 | 每个禁止词 |
| 含有禁止表达模式 | +0.5/模式 | 模式匹配 |
| diagnosisStatus = inconclusive | +0.1 | 不确定时措辞更难把握 |
| 连续 3 次 inconclusive | +0.2 | 累积不确定 |
| 家长上次反馈为"不准确" | +0.3 | 信任已受损 |
| effectScore = -2 | +0.2 | 策略有害，摘要可能引起焦虑 |

**风险阈值**：
- riskScore < 0.3：自动发送
- 0.3 ≤ riskScore < 0.5：发送但标记"建议人工复查"
- riskScore ≥ 0.5：不发送，进入人工复审队列

## 六、家长反馈闭环

家长可以反馈（见 ParentSummary 表）：

| 反馈选项 | 系统动作 |
|----------|----------|
| 准确 | 信任度 + 0.1，摘要模板偏好锁定 |
| 不准确 | 信任度 - 0.2，该摘要进入 badcase 池，下次生成时 riskScore + 0.3 |
| 有帮助 | 记录该模板有效，后续同类情况复用 |
| 不适合 | 降低该错因在摘要中的提及优先级，优先用通用描述 |
| 请芽芽重新观察 | 触发该知识点重新诊断（相当于下次答题后重跑诊断链路） |

**重要规则**：家长反馈不能直接修改诊断结果或学生画像。只能影响摘要生成策略、置信度调整、badcase 复盘优先级。

## 七、parentSafeExplanation 模板体系

error_taxonomy.json 中每个错因的 `parentSafeExplanation` 字段是摘要母版。引擎从中提取关键元素：

| 错因 errorCode | parentSafeExplanation（示例） | 摘要中使用方式 |
|---------------|------------------------------|---------------|
| decimal_point_position_error | 孩子在判断小数点位置时需要更多图示支持 | "一开始在判断小数点位置时有些犹豫" |
| calculation_error | 孩子在计算过程中出现了操作失误 | "做题过程中有一个小疏忽" |
| concept_confusion | 孩子对两个相似概念还需要更清晰的区分 | "在做题时，两个概念有点像，孩子需要更清晰的区分" |
| info_omission | 孩子在读题时可能遗漏了关键信息 | "这道题里有个小细节需要再仔细看看" |
| transfer_failure | 孩子在遇到变化后的题目时需要更多引导 | "题目变了一点点形式后，孩子需要一些引导来适应" |
| strategy_missing | 孩子在面对某些题型时还需要更多方法引导 | "知识点理解了，解题方法可以再练练" |
| question_type_unfamiliar | 孩子对这类题型的答题方式还不太熟悉 | "遇到了新的题型，芽芽给了个模板先试试" |
| expression_format_error | 孩子能把题做对，只是书写格式上需要更规范的习惯 | "做题的时候格式上稍微注意一下就更好了" |
| prerequisite_gap | 孩子需要巩固一下之前学过的基础知识 | "需要先复习一下之前学过的内容" |
| memory_retrieval_failure | 孩子一时想不起来之前学过的方法 | "之前学过的方法暂时没想起来，芽芽给了一点提示" |
| comprehension_bias | 孩子对题目的理解可能和出题意图不完全一致 | "这道题的理解方向可以调整一下" |

模板的核心技巧：**永远不说是孩子的问题，而是描述"现象 + 芽芽在帮"。**

## 八、Phase 1 实现范围

Phase 1 实现：
- [ ] diagnosisStatus = confirmed → 基于 parentSafeExplanation 生成完整摘要
- [ ] diagnosisStatus = confirmed_with_reservation → 保守措辞摘要
- [ ] diagnosisStatus = inconclusive → 通用安全摘要（不提具体错因）
- [ ] 禁止词过滤器（4.1 全量生效）
- [ ] 风险评分 + 阈值拦截（riskScore ≥ 0.5 不发送）
- [ ] 家长反馈记录（ParentSummary 表更新）
- [ ] shortSummary 一句话生成

Phase 2 补齐：
- [ ] 周/月/学期摘要
- [ ] 长期进步趋势可视化描述
- [ ] 个性化模板偏好学习

## 九、与相关文档的接口约定

| 文档 | 关系 |
|------|------|
| 09_EVENT_PROTOCOL.md | 消费 diagnosis_updated（事件 8）、strategy_applied（事件 10） |
| 07_ERROR_TAXONOMY.md | 读取 parentSafeExplanation |
| 10_DATA_MODEL.md | 写入 ParentSummary 表 |
| 11_DIAGNOSIS_ENGINE.md | 诊断引擎预填 parentSummary.short/full/teacherNote |
| 14_QUALITY_DASHBOARD.md | 摘要安全率、家长投诉率指标 |
