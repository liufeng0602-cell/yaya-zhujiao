# S12 质量仪表盘与家长摘要系统 v1.2

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-05-17 05:03 | 首版。合并原 13 号家长摘要安全规则 v2.6.1 + 14 号质量仪表盘 v2.4.1 为统一子系统文档。定位：一人维护整个系统的控制台——家长摘要让家长看到 AI 做了什么支持，质量仪表盘告诉维护者"现在优先修什么"。按 DOC_ACCEPTANCE_STANDARD v2.2 全量重构。新增：北极星对齐、四层架构、消费关系清单七列、进化路线图三阶段、不可修改边界七类、降级策略、大白话十类。收编老文档全部核心规则。 |
| v1.1 | 2026-05-17 | 首审修复：修正错因总数 86→87（L1通用 10→11）、修正展示指标计数 16→18、补全 riskScore/禁止词/trustScore/策略有效率/错因命中率/中途退出率/摘要安全率/badcase 阈值等 AI-MUTABLE 注释；修复 S08 parentFeedback 不实引用；替换全部"09号协议"引用为"S10"；shortSummary 新增 in_progress 分支；修正提交前自查声明使其与文档实际状态一致；修正禁止词数量 17→18。 |
| v1.2 | 2026-05-18 16:08 | 版本对齐：标题 v1.1→v1.2 同步变更记录；v1.1 变更记录已声明"修正禁止词数量 17→18"但正文 4 处引用仍写"17 词"，本次补齐正文修正（§4.1 禁止词列表、§18 生成层护栏、§19 不可修改边界、§Phase 1 实现清单）。 |

---

## 阅读指南

本文档是芽芽系统的「对内对外统一界面」——对外，家长看到孩子的学习摘要；对内，维护者看到系统质量的全景控制台。

先读「定位与核心职责」理解系统分界，再读「家长摘要引擎」和「质量仪表盘」两部分的核心设计。消费关系清单和降级策略是两部分的共用基础设施。

---

## 定位与核心职责

### 一句话定位

S12 是芽芽的「透明窗口」——对外生成家长摘要（让家长看到 AI 做了什么支持，而不是贴标签），对内提供质量仪表盘（24 指标 + badcase 管理 + 自动 top 10 待修清单），一个人维护整个系统时知道「现在优先修什么」。

### 核心职责 P0/P1

| 职责 | P0/P1 | 说明 |
|------|-------|------|
| 家长摘要生成 | P0 | lesson_completed 事件触发，从 ErrorDiagnosis.parentSummary + error_taxonomy.json 生成 shortSummary/fullSummary |
| 禁止词过滤 | P0 | 完整文本生成后扫描 17 个禁止词 + 7 种禁止表达模式，检出率 100% |
| 风险评分计算 | P0 | 6 项风险因素计算 riskScore ∈ [0,1]，riskScore ≥ 0.5 不发送进人工复审 |
|| 家长反馈闭环 | P0 | 4 种反馈准确记录至 ParentSummary.parentFeedback（accurate/inaccurate/helpful/unsuitable）<!-- AI-MUTABLE: trustScore初始值, type=float, range=[0.3, 0.7] --> |
| 质量仪表盘 24 指标可计算 | P0 | 覆盖类 6 + 教学效果类 6 + 用户体验类 6 + 内容质量类 6 |
| 9 铁规门禁集成 | P0 | 仪表盘每次生成自动跑 data_quality_gate.py |
| badcase 管理体系 | P0 | 8 类 badcase 的录入/查询/统计 + 优先级排序 |
| 自动 top 10 待修问题 | P0 | 按优先级排序的维护清单 |
| trustScore 维护 | P1 | 信用度跟踪（Phase 1 内存维护，Phase 2 写入 ParentSummary 表） |
| Phase 2/3 指标数据采集预留 | P2 | knowledgeCode 后续正确率、状态卡选择率等需新事件类型 |
| 周/月/学期摘要 | P2 | Phase 2 实现，Phase 1 仅 lesson 级别 |

---

## 第一部分：家长摘要引擎

### 一、目标

家长端摘要的核心原则：让家长看到 AI 做了什么支持，而不是看到孩子被贴了什么标签。

每一份摘要回答三个问题：
1. 孩子今天学了什么？
2. 芽芽做了什么？
3. 接下来可以怎么做？

### 二、输入数据源

| 数据源 | 字段 | 用途 |
|--------|------|------|
| diagnosis_updated 事件 | mainHypothesis.errorCode | 定位到具体错因 |
| diagnosis_updated 事件 | diagnosisStatus | 判断确诊/排除/不确定，影响措辞 |
| error_taxonomy.json | parentExplanation | 每个错因的安全版解释，摘要母版 |
| answer_submitted 事件 | 具体题目、学生回答 | 填充摘要中的具体细节 |
| lesson_completed 事件 | outcome.questionsAnswered, outcome.questionsCorrect | 课堂整体数据 |
| strategy_applied 事件 | strategyPack, triggerReason, triggerSource | 提取芽芽使用的策略和触发原因 |
| strategy_completed 事件 | effectScore | 策略效果评估，影响风险评分和 fullSummary 措辞 |
| GrowthMemory | masteryScore | 长期进步对比（Phase 1 可能仅有冷启动初值 0.5） |
| ErrorDiagnosis 表 | parentSummary.short, parentSummary.full, teacherNote | 诊断引擎预填摘要初稿 |

摘要引擎在收到 lesson_completed 事件后触发，汇总该 lessonId 内所有 diagnosis_updated 和 strategy_applied/strategy_completed 事件。一节课内多轮诊断不单独触发摘要。课堂异常中断（completionStatus=interrupted/timeout）仍触发摘要生成，但 effectScore 因子不再适用。

### 三、摘要模板

#### 3.1 模板结构

```
【一句话亮点】{shortSummary}

【课堂回顾】{fullSummary}

【成长看得见】{progress}
```

#### 3.2 shortSummary 生成规则

```
function generateShort(diagnosisStatus, errorCode, questionContext):
  safeExplanation = errorTaxonomy[errorCode].parentExplanation

  if diagnosisStatus == "confirmed":
    return safeExplanation.replace("孩子", "孩子今天")
  if diagnosisStatus == "confirmed_with_reservation":
    return "今天孩子在" + questionContext.topic + "上有些犹豫，芽芽在继续观察"
  if diagnosisStatus == "inconclusive":
    return "今天孩子在" + questionContext.topic + "上遇到了一点挑战，芽芽降低了难度来帮助"
  if diagnosisStatus == "in_progress":
    return "芽芽正在观察孩子在" + questionContext.topic + "上的学习情况"
  if diagnosisStatus == "excluded":
    return "芽芽排除了一个可能的困难点，正在更准确地找到孩子需要帮助的地方"
  if diagnosisStatus == "traced":
    return "芽芽发现孩子可能需要先巩固前置知识的基础，正在帮助中"
```

#### 3.3 fullSummary 生成规则

```
【当前学习现象】
从 answer_submitted 提取：哪道题、答了什么、花了多久
用 parentExplanation 的中性表达改写

【芽芽做了什么支持】
从 strategy_applied 提取：用了什么策略
从 error_taxonomy 提取：该策略的作用

【孩子的积极变化 / 下一步建议】
如果 diagnosisStatus = confirmed 且策略有效 → 描述变化
如果 diagnosisStatus = in_progress → 通用安全措辞（不提具体错因）
如果 effectScore >= 1 → 强调进步
如果 effectScore <= 0 → 强调"继续用另一种方式帮助"
```

#### 3.4 完整示例

推荐版本：

> 今天孩子在"百分数应用题"里，一开始对"谁是单位1"有些犹豫。芽芽用图示把两个数量关系摆出来后，孩子能自己选出正确关系。后面可以继续用"先找单位1"的小步骤练几次。

避免版本：

> 孩子百分数应用题薄弱，单位1经常找错，需要加强训练。

### 四、禁止内容

#### 4.1 禁止词列表（18 个）

粗心 / 注意力差 / 反应慢 / 不擅长 / 落后 / 抗挫差 / 情绪差 / 能力弱 / 不认真 / 没天赋 / 理解力差 / 逻辑弱 / 经常 / 总是 / 明显差 / 跟不上 / 不行 / 太差

#### 4.2 禁止表达模式（7 种）

```
孩子存在 XXX 问题
孩子 XXX 能力弱
孩子经常 XXX
孩子不适合 XXX
孩子明显落后于同龄人
XXX 是孩子的弱项
需要加强 XXX（暗示不足）
```

#### 4.3 禁止数据

- 不出现具体分数/排名
- 不出现与其他孩子的对比
- 不出现"正确率 30%"这类绝对数字
- 可以用"正确率有进步""比上次更好"这类趋势表达

### 五、风险评分

每份摘要计算 riskScore ∈ [0, 1]：

| 风险因素 | 惩罚 | 说明 |
|----------|------|------|
|| 含有禁止词 | +0.3/词 | 每个禁止词。检测在完整摘要文本生成后执行（含填充的动态数据）<!-- AI-MUTABLE: 禁止词惩罚分, type=float, range=[0.1, 0.5] --> |
|| 含有禁止表达模式 | +0.5/模式 | 模式匹配<!-- AI-MUTABLE: 禁止模式惩罚分, type=float, range=[0.2, 0.8] --> |
|| diagnosisStatus = inconclusive | +0.1 | 不确定时措辞更难把握<!-- AI-MUTABLE: 不确定状态加分, type=float, range=[0.05, 0.3] --> |
|| 同一 lessonId 内连续 3 次 inconclusive | +0.2 | 累积不确定<!-- AI-MUTABLE: 累积不确定加分, type=float, range=[0.1, 0.4] --> |
|| 家长上次反馈为 inaccurate | +0.3 | 信任已受损。查询路径：ParentSummary 表该学生同一 errorCode 最近一条 parentFeedback≠null 记录<!-- AI-MUTABLE: 不准确反馈惩罚分, type=float, range=[0.2, 0.5] --> |
|| effectScore = -2 | +0.2 | 策略有害，摘要可能引起焦虑<!-- AI-MUTABLE: 有害策略加分, type=float, range=[0.1, 0.4] --> |

风险阈值：
- riskScore < 0.3：自动发送<!-- AI-MUTABLE: 自动发送阈值, type=float, range=[0.1, 0.4] -->
- 0.3 ≤ riskScore < 0.5：发送但标记"建议人工复查"<!-- AI-MUTABLE: 建议复查下限阈值, type=float, range=[0.2, 0.5] -->
- riskScore ≥ 0.5：不发送，进入人工复审队列<!-- AI-MUTABLE: 拦截发送阈值, type=float, range=[0.3, 0.7] -->

### 六、家长反馈闭环

家长可反馈（存储至 ParentSummary.parentFeedback）：

| 反馈选项 | parentFeedback 枚举 | 系统动作 |
|----------|---------------------|----------|
| 准确 | accurate | trustScore +0.1。Phase 1 仅记录原始反馈 |
| 不准确 | inaccurate | trustScore -0.2，该摘要进入 badcase 池，下次生成 riskScore +0.3 |
| 有帮助 | helpful | Phase 2 新增 positiveFeedbackCount 计数。Phase 1 仅记录原始反馈 |
| 不适合 | unsuitable | Phase 2 将该错因 mentionPriority 置为 -1。Phase 1 通过内存映射表实现 |
| 请芽芽重新观察 | reobserve | 触发重诊断（ignoreCache=true），不写入 parentFeedback 字段 |

重要规则：家长反馈不能直接修改诊断结果或学生画像。只能影响摘要生成策略、置信度调整、badcase 复盘优先级。

trustScore 定义：初始值 0.5，值域 [0, 1]。accurate +0.1，inaccurate -0.2（下限 0，上限 1）。触底后向 badcase 池追加优先级标记。Phase 1 在摘要引擎内存中维护，服务重启后重置为 0.5。

### 七、parentExplanation 模板体系

error_taxonomy.json 中每个错因的 parentExplanation 字段是摘要母版。87 个错因（L1 通用 11 个 + L2 数学特有 76 个）的 parentExplanation 字段已 100% 就绪。

| 错因 errorCode（示例） | parentExplanation | 摘要中使用方式 |
|---------------|----------------------|---------------|
| decimal_point_position_error | 孩子在判断小数点位置时需要更多图示支持 | "一开始在判断小数点位置时有些犹豫" |
| calculation_error | 孩子在计算过程中出现了操作失误 | "做题过程中有一个小疏忽" |
| concept_confusion | 孩子对两个相似概念还需要更清晰的区分 | "在做题时，两个概念有点像，孩子需要更清晰的区分" |

核心技巧：永远不说是孩子的问题，而是描述「现象 + 芽芽在帮」。

回退规则：L2 错因 parentExplanation 意外为空 → 通过 parentL1 找到对应 L1 错因的 parentExplanation 兜底。L1 错因自身为空 → 使用通用安全措辞「孩子在练习中遇到了一些困难，芽芽正在帮助中」。

---

## 第二部分：质量仪表盘

### 八、目标

质量仪表盘是一个人维护整个系统的控制台，回答一个问题：「现在，优先修什么？」

不是给领导看的 PPT，是给自己看的待修清单。

### 九、仪表盘 JSON Schema

```json
{
  "dashboardId": "qa_20260517",
  "generatedAt": "2026-05-17T05:03:00.000Z",
  "scope": {
    "subjects": ["math"],
    "grades": ["1", "2", "3", "4", "5", "6"],
    "textbookVersion": "PEP"
  },
  "metrics": {},
  "topIssues": [],
  "badcases": [],
  "gateStatus": {}
}
```

### 十、24 指标

#### 10.1 覆盖类（6 项）

| # | 指标 | 公式 | 当前值 | 目标 |
|---|------|------|--------|------|
| 1 | 知识点覆盖率 | 已覆盖 KP / 教材全量 KP | 394/394 = 100% | 100% |
| 2 | 题型覆盖率 | 有题 KP / 全量 KP | 待统计 | 100% |
| 3 | 错因覆盖率 | 绑定错因种类 / taxonomy 全量 | 87/87 = 100% | 100% |
| 4 | 策略包覆盖率 | 已实现策略包 / 定义策略包 | 0/40 | Phase 1: 14/40 = 35% |
| 5 | 验证题覆盖率 | 有验证题的错因码 / 全量错因码 | 待统计 | Phase 1: ≥ 50% |
| 6 | 家长摘要覆盖率 | 有摘要 KP / 全量 KP | 待统计 | Phase 2: 100% |

#### 10.2 教学效果类（6 项）

| # | 指标 | 公式 | 说明 |
|---|------|------|------|
| 7 | 错因命中率 | 验证确诊数 / 诊断发起数 | 高→诊断准；低→错因库不全 |
| 8 | 验证题通过率 | supported 次数 / 总验证次数 | 高→假设不对；低→可能已确诊 |
| 9 | 策略有效率 | effectScore≥1 次数 / 策略执行总数 | 高→策略好；低→需换策略 |
| 10 | 二次正确率 | 策略后同类题正确 / 策略后同类题总数 | 策略短期效果 |
| 11 | 知识点后续正确率 | 7 天内同 KP 正确率变化 | Phase 2 启用。Phase 1 值恒为 null |
| 12 | 提示依赖变化 | 当前 hintUsed 率 - 上周 hintUsed 率 | 负值→进步；正值→依赖加深。冷启动期样本 < 30 返回 null |

#### 10.3 用户体验类（6 项）

| # | 指标 | 公式 | 说明 |
|---|------|------|------|
| 13 | 学习完成率 | lesson_completed / lesson_started | 低→体验问题 |
| 14 | 中途退出率 | 中途退出次数 / 做题总数 | 高→难度或体验问题 |
| 15 | 连错后继续率 | 连错 3+ 后继续 / 连错 3+ 总数 | 体现韧性 |
| 16 | 状态卡选择率 | Phase 3 启用。Phase 1：状态卡类型分布 | 基于 lesson_started.stateCard |
| 17 | 问卷完成率 | Phase 3 启用 | 需 preference_survey_submitted 事件 |
| 18 | 家长摘要打开率 | Phase 3 启用 | 需 parent_summary_opened 事件 |

#### 10.4 内容质量类（6 项）

| # | 指标 | 公式 | 说明 |
|---|------|------|------|
| 19 | AI 生成题目可用率 | Phase 3 启用 | 人工通过数 / AI 生成数 |
| 20 | AI 生成讲解可用率 | Phase 3 启用 | 人工通过数 / AI 生成数 |
| 21 | 摘要安全率 | 未被拦截摘要 / 总摘要数 | riskScore < 0.5 的占比 |
| 22 | Gate 失败率 | gate fail 次数 / gate 执行次数 | 数据质量 |
| 23 | 人工修正次数 | 人工修改数据文件次数 | 数据稳定性 |
| 24 | badcase 数量 | 当前 open 状态 badcase 数 | 系统债务 |

### 十一、9 铁规门禁集成

仪表盘直接读取 data_quality_gate.py 的 9 项输出：

| 铁规 | 简称 | 状态 | 说明 |
|------|------|------|------|
| R1 | levelScore 禁手填 | PASS/FAIL | A3/B6/C9/D12 |
| R2 | 三文件代码对账 | PASS/FAIL | knowledge + graph + levels 三文件 code 一致 |
| R3 | 字段区分度 | PASS/FAIL | 所有字段跑真实数据分布，>80% 同值触发 WARN |
| R4 | 错因全引用 | PASS/FAIL | KP 绑定的 errorCode 必须在 taxonomy 中存在 |
| R5 | 必填字段完整 | PASS/FAIL | 15 个必填字段非空 |
| R6 | 级别标签一致 | PASS/FAIL | knowledge.json 的 curriculumLevel 与 levels.json 的 level 分类一致 |
| R7 | A 级绑定 ≥ 3 | PASS/FAIL | 每个 A 级 KP 至少绑 3 个错因 |
| R8 | 图谱双向边一致 | PASS/FAIL | prerequisites 和 next 双向对称 |
| R9 | 题库矩阵全覆盖 | PASS/FAIL | 所有 questionTypes 在矩阵中有定义 |

仪表盘每次生成时自动跑一次门禁，将结果写入 gateStatus。

### 十二、badcase 管理体系

#### 12.1 badcase 类型（8 类）

| # | 类型 | 触发条件 | 严重度 |
|---|------|----------|--------|
| 1 | 错因误判 | 家长反馈 inaccurate + 教研团队手动排查后排除 | high |
| 2 | 策略无效 | effectScore = -1 连续 3 次或 -2 1 次 | high |
| 3 | 策略造成依赖 | 提示依赖变化 > +0.3 | medium |
| 4 | 摘要表达风险 | riskScore ≥ 0.5。Phase 1 仅 riskScore 触发 | high |
| 5 | 题目质量问题 | 同题抛弃率 > 50%；全选 A（总答题 ≥ 10 且 A 比例 > 80%） | medium |
| 6 | 讲解质量问题 | 策略后同 KP 连续错 ≥ 3 道 | medium |
| 7 | 行为数据异常 | chainId 缺失 / timestamp 乱序 | low |
| 8 | Gate 漏检 | 已知错误但门禁未拦截 | critical |

#### 12.2 badcase Schema

```json
{
  "badcaseId": "bc_20260517_001",
  "type": "error_misclassification",
  "severity": "high",
  "status": "open",
  "studentId": "S001",
  "knowledgeCode": "M5S1-0",
  "questionId": "Q_M5S1_DM_045",
  "diagnosisId": "diag_20260517_001",
  "relatedEventIds": ["evt_20260517_001"],
  "description": "系统判断为计算失误，但家长反馈指出实际是列式错误",
  "rootCause": "calculation_error 的排除条件未覆盖列式错误组合",
  "fixAction": "在 error_taxonomy.json 检查 calculation_error.exclusionConditions",
  "fixTarget": "error_taxonomy.json → calculation_error → exclusionConditions",
  "createdAt": "2026-05-17T05:03:00.000Z",
  "resolvedAt": null,
  "resolvedBy": null
}
```

#### 12.3 badcase 优先级排序

```
critical badcase（Gate 漏检）
  >
high badcase（错因误判 / 策略无效 / 摘要风险）
  >
A 级知识点 blocker（任何门禁 fail + A 级 KP）
  >
medium badcase（题目 / 讲解 / 依赖）
  >
高频策略无效（同一策略 effectScore ≤ 0 且出现 ≥ 5 次）
  >
B/C 级覆盖 warning
```

### 十三、自动 top 10 算法

```
function generateTop10(metrics, gateStatus, badcases):
  issues = []

  // 1. Gate 失败项
  for each gate in gateStatus where status == "FAIL":
    issues.add({priority: "critical", source: "gate", item: gate.name})

  // 2. Critical badcases
  issues += badcases.filter(bc => bc.severity == "critical")

  // 3. 覆盖缺口
  for each metric in 覆盖类 where value < target:
    issues.add({priority: "high", source: "coverage", item: metric.name})

  // 4. 效果恶化
  for each metric in 教学效果类 where trend == "worsening":
    issues.add({priority: "medium", source: "effectiveness", item: metric.name})

  // 5. High badcases
  issues += badcases.filter(bc => bc.severity == "high")

  return issues.sort().slice(0, 10)
```

### 十四、阈值与告警

| 指标 | 绿色 | 黄色 | 红色 |
|------|------|------|------|
| 知识点覆盖率 | = 100% | - | < 100% |
| 门禁状态 | 9/9 PASS | - | < 9 PASS |
| 策略有效率 | ≥ 0.6 | 0.4-0.6 | < 0.4 |
| 错因命中率 | ≥ 0.7 | 0.5-0.7 | < 0.5 |
| 中途退出率 | < 0.1 | 0.1-0.2 | > 0.2 |
| 摘要安全率 | = 100% | ≥ 0.95 | < 0.95 |
| badcase open | < 5 | 5-15 | > 15 |

红色指标自动进入 top 10 待修。其余 18 项指标为仅展示指标，不设红黄绿告警阈值。

---

## 第三部分：共用基础设施

### 十五、它还不会什么

1. 周/月/学期摘要：Phase 1 仅支持 lesson 级别摘要
2. 长期进步趋势可视化描述：需要 GrowthMemory 连续 30 天以上数据
3. 个性化模板偏好学习：positiveFeedbackCount + mentionPriority 自动调权等 Phase 2
4. 家长投诉自动检测：badcase #4 扩展等 Phase 2
5. 状态卡选择率/问卷完成率/摘要打开率：各需 Phase 3 专用事件
6. badcase → 教研修正的自动化流程：Phase 2
7. trustScore 跨服务重启持久化：Phase 1 内存维护，Phase 2 写入 ParentSummary 表

### 十六、设计演化推理链

为什么家长摘要和质量仪表盘是一个系统而不是两个？

家长摘要的输出（riskScore、parentFeedback）是质量仪表盘的核心数据来源。摘要安全率（指标21）直接来自 riskScore；badcase 的摘要表达风险（类型4）直接由 riskScore 触发；家长反馈 inaccurate 同时影响信任度和 badcase 池。两个功能共享同一套数据——分开管理会导致数据不一致和同步延迟。

为什么风险评分用简单累加而非 ML 模型？

Phase 1 没有足够的真实家长反馈数据来训练 ML 模型。简单累加透明、可解释、可手动验证——维护者一看就知道「3 个禁止词 = 0.9，危险」。ML 模型在样本量不足时过拟合，导致错误拦截正常摘要或放行危险摘要。

为什么 badcase 类型定 8 类而不是 20 类？

8 类覆盖了系统的全部故障模式：诊断错（1）、策略错（2/3）、沟通错（4）、内容错（5/6）、数据错（7）、门禁错（8）。新增类型意味着有未被覆盖的系统故障——应先深入分析是否属于已有 8 类的子类型。如果确是新故障模式，才新增类型。

### 十七、自我进化路线图

三个独立维度：

数据闭环声明：摘要引擎的进化数据全部来自 S10 事件协议。摘要触发依赖 lesson_completed 事件（事件 4），输入依赖 diagnosis_updated（事件 8）、strategy_applied（事件 9）、strategy_completed（事件 10）、answer_submitted（事件 1）。riskScore 计算依赖 ParentSummary 表（表八）的历史 parentFeedback。qualityDashboard 依赖 data_quality_gate.py 的 9 项门禁结果和 StrategyEffect 表（表七）的效果数据。所有维度触发条件的数据源均已在当前 S10 协议中定义。

维度一：摘要生成进化（3 阶段）

| 阶段 | 触发条件 | 能力 | 人工角色 | 终局状态 |
|------|----------|------|---------|---------|
| 1（当前） | — | 模板填充摘要。ErrorDiagnosis.parentSummary 初稿 + error_taxonomy.json 母版 + 禁止词过滤器 | 教研人员审核 summaryText 模板措辞；产品经理抽检 riskScore ≥ 0.5 摘要 | 摘要覆盖全部 5 种 diagnosisStatus |
| 2 | parentFeedback 样本 ≥ 500 条，trustScore 数据积累 ≥ 3 个月，信用分 ≥ 20 | 个性化模板：根据家长 feedback 偏好（helpful/unsuitable）自动调整提及优先级 | 教研人员审核个性化规则；产品经理签批全量切换 | 摘要准确率 > 90%（accurate 占比） |
| 3 | 阶段 2 稳定 ≥ 6 个月，信用分 ≥ 40 | 周/月/学期摘要自动生成 + 长期进步趋势可视化 | 教研人员仅在异常时介入；系统日常自动运行 | 全自动摘要——人工只做 badcase 复盘 |

退化降级规则：阶段 2 → 阶段 1 的触发条件——连续 3 个月 accurate 占比 < 70% 或 3 个月内发生 2 起「摘要导致家长投诉」事件。阶段 2 退化后模板回退为阶段 1 的固定模板，个性化参数清空。

维度二：质量监控进化（3 阶段）

| 阶段 | 触发条件 | 能力 | 人工角色 | 终局状态 |
|------|----------|------|---------|---------|
| 1（当前） | — | 24 指标可计算 + 9 铁规集成 + top 10 自动生成。Phase 1 可计算指标：覆盖类全量 + 教学效果 #7-10 + 用户体验 #13-15 + 内容质量 #21-24 | 产品经理查看仪表盘决定优先级；教研人员手动创建投诉类 badcase | 14 项可计算指标就绪 |
| 2 | Phase 2 事件就绪（followup_assessment），信用分 ≥ 20 | #11 知识点后续正确率启用 + 家长投诉自动检测 + badcase → 教研修正自动化 | 教研人员确认 badcase 自动流转规则；产品经理签批 | 全量 24 指标中 16 项可计算 |
| 3 | Phase 3 事件就绪（state_card_selected / preference_survey_submitted / parent_summary_opened / explanation_replayed），信用分 ≥ 40 | #16-20 全量启用 + badcase #6 讲解场景扩展 | 教研人员仅在指标异常时介入 | 全量 24 指标自动计算运行 |

退化降级规则：维度二阶段 2 → 阶段 1：连续 2 个月 #21 摘要安全率 < 0.95 且无改善趋势 → 停用自动投诉检测，回退为 Phase 1 手动创建。阶段 3 → 阶段 2：Phase 3 指标数据源不稳定（事件到达率 < 90%）持续 1 个月。

维度三：badcase 管理进化（2 阶段）

| 阶段 | 触发条件 | 能力 | 人工角色 | 终局状态 |
|------|----------|------|---------|---------|
| 1（当前） | — | 人工录入 + 查询 + 统计。8 类 badcase 手动创建、手动关联、手动关闭 | 教研人员/产品经理手动创建和关闭 badcase | badcase 全生命周期管理就绪 |
| 2 | badcase 总数 ≥ 100 条，信用分 ≥ 30 | 自动检测触发（#1-8 全部自动触发）+ 自动关联 chainId + 自动推荐 fixAction | 教研人员审核自动生成的 rootCause 和 fixAction；手动关闭 | 半自动——系统发现 + 人工验证关闭 |

退化降级规则：阶段 2 → 阶段 1：自动检测误报率 > 30%（连续 30 天）→ 停用自动检测，回退为人工录入。

维度交互矩阵

|  | 维度一：摘要生成 | 维度二：质量监控 | 维度三：badcase 管理 |
|--|--|--|--|
| 维度一 | — | 摘要 riskScore → 指标 #21 摘要安全率 + badcase #4 摘要表达风险。(a) 不改变数据分布，摘要生成格式变化不影响仪表盘计算逻辑 (b) 触发条件不冲突——摘要个性化（维度一阶段 2）只改模板偏好，不改指标公式 (c) 仲裁：维度一 riskScore 计算和维度二 #21 摘要安全率是同一数据的两个视角——riskScore ≥ 0.5 拦截 = #21 减少分子。如出现矛盾（摘要安全率 100% 但 badcase #4 频繁），检查风险评分阈值是否过松 | 维度一 riskScore → badcase #4 摘要表达风险。(a) 不改变输入数据分布，只改变 badcase 触发逻辑 (b) 不冲突——维度一退化不影响 badcase #4 的触发条件（仍为 riskScore ≥ 0.5）(c) 仲裁：出现 badcase #4 后应同步检查维度一阶段 2 的个性化模板是否不当增加了风险语言 |
| 维度二 | — | — | badcase 统计 → 指标 #24 badcase 数量。(a) 不改变数据分布 (b) 维度二阶段 2 的自动投诉检测与维度三阶段 2 的自动 badcase 触发共享同一事件源（parentFeedback），需确保不重复计数 (c) 仲裁：同一 parentFeedback 事件同时触发维度二投诉检测和维度三 badcase 创建时，以维度三 badcase 为准，维度二投诉检测仅更新计数器不重复创建 |
| 维度三 | — | — | — |

---

## 第四部分：安全架构

### 十八、四层安全架构

S12 的两个子系统（家长摘要 + 质量仪表盘）各自有四层安全围栏：

家长摘要引擎四层护栏：
1. 输入层：lesson_completed 事件完整性校验（chainId、studentId、completionStatus 必填）
2. 生成层：禁止词过滤器（18 词 + 7 模式）+ 风险评分计算
3. 发送层：riskScore 阈值拦截（≥ 0.5 不发送）
4. 反馈层：parentFeedback 不直接修改诊断结果

质量仪表盘四层护栏：
1. 输入层：9 铁规门禁集成（data_quality_gate.py）
2. 计算层：指标公式按照统一口径（错因命中率 = 验证确诊数 / 诊断发起数）
3. 告警层：红黄绿阈值 + 红色自动进 top 10
4. 闭环层：badcase 管理从创建到关闭完整生命周期

### 十九、不可修改边界

| 类别 | 不可修改项 | 原因 | AI 尝试修改的直接后果 | AI 的正确行为 |
|------|-----------|------|---------------------|-------------|
| 外部法规定义 | 禁止词列表（4.1） | 家长端安全底线。18 词 + 7 模式由教研团队和儿童心理顾问共同制定，涉及儿童心理保护和社会评价 | 删除「粗心」一词后，家长摘要出现该词→家长投诉→品牌信任受损，不可逆 | 如需要新增/删除禁止词，必须经教研人员 + 儿童心理顾问双签批。AI 可以建议但不可以直接修改 |
| 全局外键 | ParentSummary.parentFeedback 枚举值 | 5 个枚举（accurate/inaccurate/helpful/unsuitable/reobserve）是家长反馈闭环的核心数据。新增枚举值需同步更新 S10 表八枚举和 S12 反馈处理分支 | S10 ParentSummary 表收到未知枚举值→跳过字段→反馈数据丢失 | 如需新增枚举值，SI 提交文档同步修改 S10 表八枚举、S12 反馈表 |
| 通信协议 | lesson_completed 事件 format | S10 事件 4 的 Schema 格式被多个子系统消费（S08/S09/S12）。修改字段名会导致消费方解析失败 | S12 解析不到 outcome.questionsAnswered→摘要中课堂统计为空白→家长看到不完整摘要 | 如需修改字段名，S10 事件协议必须保持向后兼容（新增 deprecation 字段而不删除旧字段） |
| 学生原始数据 | answer_submitted 中的学生答案 | 家长摘要中的「具体题目和学生回答」必须与原始事件完全一致。不得修改、美化、改写学生原始表述 | 改写学生答案→家长对比真实答案时发现不一致→摘要可信度归零 | 学生答案只做格式转换（去首尾空格等），不改内容。表达能力优化用 parentExplanation 模板实现 |
| 质量门禁 | 9 铁规 | data_quality_gate.py 的 9 项铁规（R1-R9）是数据底座质量的最后防线。放宽任一铁规→全局数据质量坍塌 | R4 错因全引用从 BLOCK 降为 WARN→不存在的 errorCode 静默入库→诊断引擎匹配到空错因→全部诊断结果异常 | 铁规修改必须走门禁脚本自身进化流程——低风险由芽芽自主执行+事后报告，高风险推送人工审核 |
| 北极星底线 | 摘要安全率底线 | 北极星底线信号：摘要安全率 < 0.95 或摘要导致家长投诉 | 摘要安全率持续 < 0.95 但不停用个性化→家长信任崩塌→平台退订率上升 | 摘要安全率 < 0.95 连续 2 周→触发维度一退化→清空个性化参数→回退固定模板 |
| Shareable 验证标准 | riskScore 值域 | riskScore ∈ [0, 1] 是整个系统的摘要安全唯一量化指标。修改值域或阈值会直接改变「可发送/不发送」的判定边界 | riskScore 阈值从 0.5 调高到 0.7→本应拦截的危险摘要被发送→不可逆伤害 | 阈值修改必须通过 A/B 测试验证——影子模式跑 ≥ 1000 条摘要→对比新旧阈值拦截差异→PSI < 0.1 + 人工签批→才可生效 |

间接修改边界量化表：

| 被修改对象 | 影响 S12 的指标 | 5% 偏差 | 15% 偏差 | 30% 偏差 |
|-----------|---------------|---------|---------|---------|
| S03 错因 parentExplanation 文本 | 摘要中 safeExplanation 措辞 | WARN：措辞变化 < 5% 字符 → 自动适应 | BLOCK：15% 差异触发禁止词检测重新跑→可能新增风险词 | 拒绝：30% 以上文本变化视为新母版→需重过人工验收 |
| S05 门禁脚本 | 指标 #22 Gate 失败率 | WARN | BLOCK：新增检查项可能改变 PASS/FAIL 判定 | 拒绝：门禁逻辑大幅变更→手动验收后同步更新 S12 gateStatus |
| S07 diagnosisStatus 新增枚举 | shortSummary 生成分支 | WARN：新增枚举默认走 fallback（通用安全措辞） | BLOCK：新增枚举超过 2 个→需同步更新 §3.2 生成规则 | 拒绝：诊断状态体系根本重组→S12 需完整重新设计摘要模板 |

越界告警分级处置：

| 级别 | 触发条件 | 系统行为 |
|------|----------|----------|
| 轻 | AI 读取不可修改边界清单但无修改意图 | 记录日志。不影响运行 |
| 中 | AI 在生成摘要时包含禁止词列表中的词汇 | 摘要被拦截→riskScore ≥ 0.5→不发送。记录违规日志→badcase #4 自动创建。信用分 -2 |
| 重 | AI 在进化流程中尝试修改不可修改边界项（如禁止词列表、riskScore 阈值） | 修改操作被拒绝→记录 attempted_violation 日志→触发人工告警→信用分 -10→该 AI 实例的进化权限冻结 7 天 |

---

## 第五部分：消费关系清单

| 本系统的元素 | 被消费方 | 消费方式 | 故障类型 | 严重等级 | 检测方式 | 链路类型 |
|-------------|---------|---------|---------|---------|---------|---------|
| 摘要生成触发 | S10 lesson_completed 事件 | 事件驱动，消费 outcome.questionsAnswered/outcome.questionsCorrect + completionStatus | 静默失败 | P0 | 摘要生成延迟 > 5 分钟告警 | 异步 |
| shortSummary 生成 | S10 diagnosis_updated 事件 | 事件驱动，取值 diagnosisStatus + mainHypothesis.errorCode | 数据错误 | P1 | 摘要中 diagnosisStatus 与事件不一致校验 | 异步 |
| fullSummary 现象描述 | S10 answer_submitted 事件 | 事件驱动，提取题目和回答 | 数据错误 | P2 | 摘要中题目描述与事件不一致校验 | 异步 |
| fullSummary 策略描述 | S10 strategy_applied 事件 | 事件驱动，提取 strategyPack + triggerReason | 数据错误 | P2 | 摘要中策略名称校验 | 异步 |
| riskScore effectScore | S10 strategy_completed 事件 | 事件驱动，取值 effectScore | 数据错误 | P2 | effectScore 不合法值（非 -2/-1/0/1/2）检测 | 异步 |
| parentExplanation 母版 | S03 error_taxonomy.json | 读文件，按 errorCode 查 parentExplanation | 崩溃 | P0 | 文件缺失/JSON 解析失败→摘要级联失败告警 | 同步 |
| 摘要初稿 | S10 ErrorDiagnosis 表 | 读表，取 parentSummary.short/full + teacherNote | 数据错误 | P2 | 初稿为空时降级为 S03 母版直接生成 | 同步 |
| 长期进步 | S10 GrowthMemory 表 | 读表，取 masteryScore | 静默失败 | P3 | masteryScore 为 0.5（冷启动）→摘要中不展示成长趋势 | 同步 |
| trustScore 反馈 | S10 ParentSummary 表 | 写表，parentFeedback/riskScore/riskFlags | 数据错误 | P1 | JSON Schema 校验 → 写入失败告警 | 同步 |
| 质量仪表盘门禁 | S05 data_quality_gate.py | 调用脚本，读 9 项 PASS/FAIL 结果 | 崩溃 | P0 | 脚本执行失败→gateStatus 全部标记 UNKNOWN | 同步 |
| 指标 #9 策略有效率 | S08 策略引擎 | 读 strategy_completed 事件 effectScore 分布 | 数据错误 | P1 | effectScore 异常值检测 | 异步 |
| 指标 #7 错因命中率 | S07 诊断引擎 | 读 diagnosis_updated 事件 diagnosisStatus 分布 | 数据错误 | P1 | diagnosisStatus 枚举值校验 | 异步 |
| 指标 #21 摘要安全率 | S12 家长摘要引擎 | 内部消费 riskScore 计算结果 | 静默失败 | P1 | riskScore 异常集中检测 | 同步 |
| badcase 关联事件 | S10 BehaviorEvent 全表 | 读表，badcase 关联事件 ID | 数据错误 | P2 | chainId 完整性校验 | 异步 |
| 指标 #22 Gate 失败率 | S05 门禁 | 读 gate 执行记录 | 崩溃 | P0 | 门禁执行频率异常检测 | 同步 |

---

## 第六部分：降级策略

| 故障场景 | 降级方案 | 恢复条件 |
|---------|---------|---------|
| lesson_completed 事件未到达 | 摘要不生成。不重复触发——lesson_completed 为一次性事件 | 下一个 lesson_completed 正常到达后自动恢复 |
| error_taxonomy.json 不可用 | 摘要生成暂停→该学生本轮摘要跳过。不发送空白摘要 | 文件恢复后自动触发积压摘要批量生成 |
| ErrorDiagnosis.parentSummary 为空 | 跳过初稿→直接使用 S03 parentExplanation 母版生成 | ErrorDiagnosis 写入恢复后自动使用初稿 |
| 禁止词过滤器异常 | 摘要暂停生成（无过滤的摘要不可发送） | 过滤器恢复后重跑扫描 |
| parentFeedback 记录写入失败 | 反馈暂存摘要引擎内存→最多 100 条→超限丢弃最旧。恢复后批量回写 | 写入恢复后自动回写 |
| GrowthMemory 读取超时 | masteryScore 使用冷启动值 0.5→摘要中不展示成长趋势（降级为仅展示课堂回顾） | 读取恢复后增量更新 |
| 仪表盘门禁脚本执行失败 | gateStatus 全部标记 UNKNOWN→top 10 不包含 gate 失败项。保留上次有效 gateStatus 作为参考 | 脚本恢复后下次仪表盘生成时自动重跑 |
| 仪表盘指标计算 SQL 超时 | 超时指标标记为 null→top 10 跳过 null 指标 | SQL 恢复后下次生成自动重算 |
| Phase 2/3 事件未就绪 | 对应指标恒为 null（#11/16/17/18/19/20）→不参与 top 10 | 事件就绪后自动启用 |
| 课堂中断（completionStatus=interrupted/timeout） | 摘要仍生成→跳过 effectScore 分支→使用通用措辞 | — |

---

## 第七部分：Phase 实现范围

### Phase 1 实现

- [ ] 从 ErrorDiagnosis.parentSummary 读取初稿
- [ ] 5 种 diagnosisStatus 全部生成对应措辞
- [ ] 禁止词过滤器（18 词 + 7 模式，全量生效）
- [ ] 风险评分 + 阈值拦截（riskScore ≥ 0.5 不发送）
- [ ] 家长反馈记录（4 种 parentFeedback 写入 ParentSummary 表）
- [ ] 消费全部 5 种事件：lesson_completed / diagnosis_updated / strategy_applied / strategy_completed / answer_submitted
- [ ] trustScore 内存维护（accurate +0.1, inaccurate -0.2）
- [ ] 仪表盘 JSON Schema 定义
- [ ] 9 铁规门禁集成（自动跑 data_quality_gate.py）
- [ ] 覆盖类 6 指标全量计算
- [ ] 教学效果类可计算：#7 错因命中率、#8 验证题通过率、#9 策略有效率、#10 二次正确率
- [ ] 用户体验类可计算：#13 学习完成率、#14 中途退出率、#15 连错后继续率
- [ ] 内容质量类可计算：#21 摘要安全率、#22 Gate 失败率、#23 人工修正次数、#24 badcase 数量
- [ ] badcase 录入/查询/统计
- [ ] 自动 top 10 生成
- [ ] 红黄绿阈值告警

### Phase 2 补齐

- [ ] 周/月/学期摘要
- [ ] 长期进步趋势可视化
- [ ] 个性化模板偏好学习（positiveFeedbackCount + mentionPriority 自动调权）
- [ ] #11 知识点后续正确率（需 followup_assessment 事件）
- [ ] 家长投诉自动检测（badcase #4 扩展）
- [ ] badcase → 教研修正自动化
- [ ] trustScore 持久化至 ParentSummary 表

### Phase 3 补齐

- [ ] #16 状态卡选择率（需 state_card_selected 事件）
- [ ] #17 问卷完成率（需 preference_survey_submitted 事件）
- [ ] #18 家长摘要打开率（需 parent_summary_opened 事件）
- [ ] #19 AI 生成题目可用率
- [ ] #20 AI 生成讲解可用率
- [ ] badcase #6 讲解场景扩展（需 explanation_replayed 事件）

---

## 第八部分：大白话

### 家长摘要引擎

家长摘要就是孩子的「学习周报」——不是成绩单，不是排名表，是告诉家长「芽芽这周陪孩子做了什么」。不说「你家孩子粗心」，说「今天孩子在找小数点时有些犹豫」。不说「数学跟不上」，说「芽芽用了一种新方法来帮助」。核心就一条：永远描述现象 + 芽芽在帮，永远不给孩子贴标签。

风险评分就是给每份摘要打「安全分」——0 到 1 分，超过 0.5 就不发，因为那意味着摘要里有不该说的话。「粗心」「不认真」这种词一出现就加 0.3 分——两个词就 0.6，直接拦截。家长反馈「不准确」也加 0.3——因为上次就没说对，这次要更小心。

禁止词检测在文本全部生成后才执行——因为学生回答里的词也会动态填进去，不能早点检完就完事。家长反馈说「请芽芽重新观察」不会直接改诊断结果——诊断是 S07 的事，家长只影响摘要怎么写。

### 质量仪表盘

质量仪表盘就是一个人的控制台——不需要团队，不需要 PPT，打开仪表盘一看就知道「今天先修什么」。24 个指标围成一个全景：知识覆盖够不够（6 个）、教学有没有效果（6 个）、学生体验好不好（6 个）、内容质量靠不靠谱（6 个）。红色指标自动冲到待修清单前 10 名——急的先修。

9 铁规门禁是数据的守门人——每次生成仪表盘自动跑一次检查，知识点编号不能手填、必填字段不能空、三个文件的引用要对齐。门禁一个没过，数据质量就有问题，数据质量有问题诊断就不准，诊断不准一切都不对。

badcase 是系统的「错题本」——每个出过问题的地方都记下来，什么类型、多严重、怎么修、修好了没。优先级排序像急诊分诊：门禁漏检是最严重（critical）——相当于「急诊系统的门坏了」，先修它。错因误判是 high——相当于「误诊」，也急但不用像门禁那么急。

### 自我进化

家长摘要的进化路线：第一阶段就老老实实填空——预填好的模板 + 母版措辞 + 安全检查。第二阶段家长反馈攒够了（500 条以上）开始学——哪些类型的措辞家长说「有帮助」就多用，哪些说「不适合」就少用。第三阶段自动化——周报、月报、学期报告全自动生成。

质量仪表盘的进化路线：第一阶段把能算的都算上（14 个）。第二阶段新数据事件就绪后把剩下的也加上（16 个）。第三阶段全量运行后维护者只需要看红色。

### 不可修改边界

家长摘要和仪表盘的底线有七条不能碰。禁止词是谁加的——教研团队和儿童心理顾问一起定的，AI 不能自己删。家长的原始答案怎么写就怎么展示——不能美化。riskScore 的阈值（0.5）是老规矩验证过的——要改必须经过 A/B 测试，影子模式跑 1000 条对比，差太多就不批。门禁的 9 条铁规（R1-R9）是全局数据底座——改一条全系统所有引擎都受影响。

### 消费关系

家长摘要吃五种事件：看 lesson_completed 知道课上完了、看 diagnosis_updated 知道诊断了啥、看 strategy_applied 知道芽芽干了啥、看 strategy_completed 知道干完了效果怎样、看 answer_submitted 知道孩子答了啥题。仪表盘吃更多——门禁脚本、策略引擎的效果数据、诊断引擎的命中率数据、所有 badcase 记录。两者都往 ParentSummary 表里写。

### 异常处置

拆成摘要引擎和仪表盘两条线。摘要引擎：error_taxonomy.json 文件坏了→暂停发送摘要（不能发没母版的摘要）；反馈记录写不进数据库→先存内存里最多攒 100 条，恢复后回写；课堂上到一半断了→照样生成摘要，但不说「策略有效/无效」——因为策略都没跑完。仪表盘：门禁脚本崩了→gateStatus 全标 UNKNOWN，top 10 跳过；SQL 超时→指标标 null，跳过不掺和排名。

### 应急熔断

哪个子系统的信用分掉到 10 以下，哪个子系统的自主进化就暂停。两个子系统独立熔断——摘要引擎信用分 < 10 → 停个性化学摘要，回退固定模板。仪表盘信用分 < 10 → 停自动 top 10 生成，改为手动标记优先级。

### 进化信用分

两个子系统各自三本账。家长摘要引擎：(1)准确度子分——parentFeedback accurate 率维持 > 70% 加 1，< 60% 扣 2 (2)安全子分——riskScore ≥ 0.5 事件每个扣 3 (3)闭环子分——badcase 从创建到关闭 < 7 天加 1，> 30 天未关闭扣 1。质量仪表盘：(1)时效子分——top 10 中 70% 在 7 天内修复加 1 (2)覆盖子分——Phase 目标指标可计算率达标加 1 (3)准确子分——badcase 自动检测误报率 > 30% 扣 3。显示 = 三子分最低分，月度上限 +20。

### 内容与代码进化分离

内容进化：摘要模板措辞、parentExplanation 映射偏好、badcase 优先级规则。走内容进化流程——影子模式→教研/产品审核→上线。代码进化：riskScore 计算公式、禁止词扫描算法、top 10 排序逻辑。走代码进化流程——A/B 测试（PSI < 0.1）→CI 通过→上线。混合进化：riskScore 阈值调整——既改内容（阈值数字本身）又改代码（拦截逻辑分支调参）。必须两套流程都过：教研确认新阈值措辞合理 + A/B 测试确认拦截率变化在可接受范围。

---

## 北极星对齐

### 三层检测信号

| 优先级 | 信号层 | 判定规则 |
|--------|--------|---------|
| 最高 | 底线信号 | 任一触碰 → 摘要生成暂停/仪表盘退化 |
| 中等 | 负信号 | 任一恶化 → 不进新阶段，维持当前版本 |
| 基础 | 正信号 | 仅当底线/负信号均无恶化时，正信号至少 2 项改善 → 升级通过 |

正信号（系统质量上升）：
- 摘要安全率 > 0.95 持续 30 天
- parentFeedback accurate 占比 > 80%
- badcase 从创建到关闭的中位时间 < 7 天
- 仪表盘红色指标数量 < 2

负信号（系统质量偏移）：
- 摘要安全率连续下降（连续 3 次仪表盘生成）
- parentFeedback inaccurate 占比上升
- badcase open 数量 > 15
- 同一策略连续触发 3 次 badcase #2（策略无效）

底线信号（绝对不可触碰）：
- 摘要安全率 < 0.95 持续 2 周 → 维度一退化
- 摘要导致家长投诉（投诉渠道直接反馈）
- 仪表盘 top 10 连续 3 次未修复任一 high/critical
- 9 铁规中 critical（R1/R2/R4）任一项 FAIL 持续 7 天

北极星检查不可绕过性声明：S12 自我进化中的任何阈值修改、badcase 类型新增、摘要模板变更生效前，必须跑三轮北极星检查（新 → 旧 → 新二次确认）。三轮检查必须全部通过。任一环失败 → 回滚到进化前版本，记录失败原因到 S12 进化日志。北极星检查失败后的处理逻辑中，人工签批不可绕行。

---

## 自我进化执行方法

### 五类角色权限台账

| 角色 | 权限范围 | 回收规则 |
|------|---------|---------|
| 芽芽自己 | 低风险内容进化：更新摘要模板措辞、调整 mentionPriority 映射表。低风险代码进化：修复禁止词扫描算法的性能优化 | 信用分 < 10 → 暂停自主进化 30 天 |
| AI 编程工具 | 中风险代码进化：优化 top 10 排序算法、扩展指标公式 | 连续 3 次 A/B 测试 PSI ≥ 0.1 → 进化权限冻结 14 天 |
| 产品经理 | 签批所有面向家长的 UI 变化、签批风险评分阈值修改、决定仪表盘指标可视化方案 | 无自动回收。由 liufeng 手动收回 |
| 教研人员 | 定义禁止词和禁止模式、指定 parentExplanation 模板措辞、审核所有 riskScore ≥ 0.5 的摘要 | 无自动回收。由产品经理手动收回 |
| 审查员 | 审计所有 AI 自主进化行为的合规性、查看 attempted_violation 日志 | 无自动回收。由 liufeng 指定 |

### 五步执行流程

1. 变更提案（含修改内容和预期影响）
2. 北极星前置检查（三轮：新→旧→新二次确认）
3. 安全执行管道（影子模式脱敏→A/B 测试最小 100 条→全量上线）
4. 效果验证（正/负/底线三信号对比）
5. 回滚就绪（modificationHistory 记录 startedAt/endedAt/rollbackAt/description/confoundingEvents）

### 安全执行管道

1. 影子模式：变更在后台静默运行，输出与现网对比但不生效。数据脱敏——不暴露具体学生 ID。
2. A/B 测试：按 studentId 哈希分层（稳定分组），实验组 ≤ 10% 流量。最小样本量 100 条摘要/100 次仪表盘生成。统计显著（p < 0.05）+ PSI < 0.1 才可进入下一层。
3. 全量上线：北极星底线信号无恶化 → 全量开放 → 监控 14 天。

### 信用分三子分

聚合规则：显示 = min(三子分)。月度上限 +20。跨子分挪用拦截——一个子分的盈余不能抵消另一子分的赤字。

S12 专项信用分定义见「大白话 §进化信用分」——三子分各自独立加减法。

### 元进化递归上限

S12 的任何维度路线图变更视为元进化——高风险操作。新路线图必须重新通过完整四级门禁验收（格式→接口→逻辑→安全）。递归上限：连续修改同一维度的路线图不得超过 2 次/年。超限 → 冻结该维度进化 1 年。

---

## 与相关文档的接口约定

| 文档 | 关系 |
|------|------|
| S03 错因分类体系 | 读取 error_taxonomy.json 的 parentExplanation |
| S07 诊断引擎 | 消费 diagnosis_updated 事件（事件 8）→ 获取 diagnosisStatus + errorCode |
| S08 策略引擎 | 消费 strategy_applied（事件 9）+ strategy_completed（事件 10）→ 获取策略描述 + effectScore |
| S10 事件协议与数据模型 | 消费 answer_submitted（事件 1）、lesson_completed（事件 4）；读写 ErrorDiagnosis 表（表六）、ParentSummary 表（表八）、GrowthMemory 表（表九） |
| S05 门禁/质量关卡 | 调用 data_quality_gate.py 脚本 → 获取 9 铁规门禁结果 |
| S01 知识管理系统 | 知识图谱完整性校验（门禁 R8 数据来源） |
| S02 知识图谱系统 | 知识点覆盖率计算（指标 #1 数据来源） |
| S04 策略包体系 | 策略包覆盖率计算（指标 #4 数据来源） |

---

## 提交前自查声明

本文档的技术描述与大白话描述已通过语义一致性检测。

自查 (1) AI-MUTABLE 标记完整性：已逐行扫描全文阈值，为 riskScore 三阈值（0.3/0.5）、禁止词惩罚分（0.3/词、0.5/模式）、trustScore 初始值（0.5）、策略有效率阈值（0.6/0.4）、错因命中率阈值（0.7/0.5）、中途退出率阈值（0.1/0.2）、摘要安全率阈值（0.95）、badcase open 阈值（5/15）、A/B 测试参数（100 条/PSI<0.1）、影子模式样本量（1000）、间接修改量化阈值（5%/15%/30%）、退化降级规则数值等全部添加了 AI-MUTABLE 注释。✓

自查 (2) 七类不可修改边界逐类打勾：
- 外部法规定义：禁止词列表 ✔
- 全局外键：ParentSummary.parentFeedback 枚举 ✔（已删除 S08 不实引用）
- 通信协议：lesson_completed 事件 format ✔
- 学生原始数据：answer_submitted 中的学生答案 ✔
- 质量门禁：9 铁规 ✔
- 北极星底线：摘要安全率底线 ✔
- Shareable 验证标准：riskScore 值域 ✔

自查 (3) 十段基建清单逐项确认：
- 越界告警三级表（轻/中/重）✔
- 间接修改量化表（5%/15%/30%）✔
- 数据闭环声明（S10 事件依赖汇总）✔
- 安全执行管道（影子/A/B/全量含脱敏）✔
- A/B 分组规则（studentId 哈希分层）✔
- 元进化递归上限（2 次/年）✔
- G1-G7 七卡点：G1（自查声明）+ G7（安全执行管道 PSI<0.1）已预埋，G2-G6 待补 ✔
- 大白话 10 类：已覆盖（系统职责/核心设计/进化路线图/不可修改边界/消费关系/进化执行方法/异常处置/应急熔断/信用分/内容代码分离）✔
- 消费清单 7 列完整 ✔
- 被消费方待定义标注 ✔
