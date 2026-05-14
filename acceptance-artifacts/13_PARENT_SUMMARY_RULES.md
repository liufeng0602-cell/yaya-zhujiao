# 13 家长端摘要安全规则 v2.6.1

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | - | 初始版本：69行，摘要公式+禁止词+推荐表达+家长反馈 |
| 2.0 | 2026-05-14 | 对齐数据底座：摘要生成从 diagnosis_updated 事件取数据；补全 parentExplanation 模板体系；新增风险评分算法；新增家长反馈闭环；Phase 1 实现范围 |
| 2.6.1 | 2026-05-15 03:21 | 地狱级交叉审查（4 项）：(1)§6 trustScore/positiveFeedbackCount 存储声明修正——原写"ParentSummary 表新增字段"但 10 号 Schema 中不存在两个字段，改为明确标注"Phase 2 新增字段，需同期更新 10_DATA_MODEL.md"，消除接口断裂；(2)§9 接口约定表补 4 个缺失数据源（answer_submitted 事件 1、lesson_completed 事件 4、ErrorDiagnosis 表、GrowthMemory 表），原接口表仅列 09/07/10/11/12/14 五个文档，漏了 4 个输入入口；(3)§5 inaccurate 查询路径统一为"该学生同一 errorCode"（原写"该知识点"和"同一 errorCode"前后矛盾）；(4)§7 L2 回退规则补 L1 最终兜底——L1 错因无 parentL1 字段，若其自身 parentExplanation 意外为空，使用通用安全措辞 |
| 2.6 | 2026-05-14 23:48 | 地狱级交叉审查 - 验收标准修复（2 项）：(1)§10 #4 fullSummary 验收补中断场景（completionStatus≠completed 时跳过 effectScore 分支）；(2)§10 #8 家长反馈记录从 5 种改为 4 种（reobserve 不写 parentFeedback，触发重诊断） |
| 2.4 | 2026-05-14 23:35 | 地狱级交叉审查（5 项）：(1)§5 "家长上次反馈 inaccurate"补查询路径（ParentSummary 表，同一 errorCode，最近一条 parentFeedback≠null）；(2)§6 mentionPriority 字段标注 Phase 2 新增 + Phase 1 临时实现方案；(3)§5 禁止词检测明确时机（完整文本生成后，含填充的动态数据）；(4)§3.2 traced 分支明确 ErrorDiagnosis 读取条件（同一 diagnosisId + diagnosisStatus=traced 的最新记录）；(5)§8 Phase 1 shortSummary 明确全部 5 种 diagnosisStatus 实现 |
| 2.3 | 2026-05-14 23:24 | 地狱级交叉审查（12 项）：(1)§2 lesson_completed 字段名对齐 09 号协议（questionCount/correctCount→outcome.questionsAnswered/outcome.questionsCorrect）；(2)§3.2 traced 分支移除空引用 tracedPrerequisite.name，改为从 ErrorDiagnosis.parentSummary.short 读取；(3)§7 补 L2 错因覆盖说明 + parentL1 回退规则；(4)§6 定义 trustScore 存储位置/初始值/值域/Phase 1 降级；(5)§6 反馈动作具体化（准确/有帮助/不适合→具体数据操作 + Phase 1 仅记录原始反馈）；(6)§3.2 函数参数 status→diagnosisStatus（对齐 diagnosis_updated 实际字段枚举）；(7)§9 合并重复 09 号引用为一行；(8)§2 strategy_completed 行补字段用途说明；(9)§5 inconclusive 计数器增加实现说明；(10)§3.3 in_progress 边界增加异常场景说明；(11)§3.3 effectScore 标注来源 strategy_completed 事件；(12)§7 expression_format_error 补句号 |
| 2.2 | 2026-05-14 22:56 | 交叉审查修复（8 项）：(1)§2 数据源表补 strategy_applied 和 strategy_completed 事件；(2)§3.2 traced 分支 prerequisiteName 来源明确为 diagnosis_updated.tracedPrerequisite.name；(3)§5「连续 3 次 inconclusive」增加时间范围（同一 lessonId 内）；(4)§5 家长反馈措辞统一（不准确→inaccurate）；(5)§8 Phase 1 补 strategy_completed 事件消费；(6)§9 接口表补 strategy_completed（事件 10）；(7)§2 GrowthMemory.masteryScore 标注 Phase 1 可用性；(8)标题版本升至 v2.2 |
| 2.1 | 2026-05-14 21:26 | 交叉审计修复（7 项）：(1)全篇 parentSafeExplanation→parentExplanation（对齐 error_taxonomy.json 实际字段名）；(2)第九节 strategy_applied 事件编号 10→9（对齐 09 号 v2.0.7）；(3)第九节接口表补 12_STRATEGY_ENGINE.md；(4)第六节家长反馈补 parentFeedback 中英文枚举映射（对齐 12 号 §5.2）；(5)第八节 Phase 1 补 ErrorDiagnosis.parentSummary 数据源；(6)第二节数据源表补 ErrorDiagnosis 行；(7)同步修复 10 号 §八 riskScore 交叉引用「第四节」→「第五节」、11 号 parentSafeExplanation→parentExplanation |

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

这是芽芽助教产品文档集的第 13 号文件，定义家长摘要的生成模板（shortSummary/fullSummary/progress）、风险评分算法、禁止词清单和家长反馈闭环。它回答「怎么让家长看到 AI 做了什么支持，而不是孩子被贴了什么标签」——消费 diagnosis_updated 和 strategy_applied 事件，结合 error_taxonomy.json 的 parentExplanation 字段生成摘要。

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
| error_taxonomy.json | parentExplanation | 每个错因的"安全版解释"，作为摘要母版 |
| answer_submitted 事件 | 具体题目、学生回答 | 填充摘要中的具体细节 |
| lesson_completed 事件 | outcome.questionsAnswered, outcome.questionsCorrect | 课堂整体数据 |
| strategy_applied 事件 | strategyPack, triggerReason, triggerSource | 提取芽芽使用的策略和触发原因 |
| strategy_completed 事件 | effectScore（用于风险评分 §5 + fullSummary 措辞 §3.3）；exitReason（暂未使用） | 策略效果评估，影响摘要措辞和风险评分 |
| GrowthMemory | masteryScore | 长期进步对比（Phase 1 可能仅有冷启动初值 0.5） |
| ErrorDiagnosis 表 | parentSummary.short, parentSummary.full, teacherNote | 诊断引擎预填摘要初稿 |

**摘要引擎触发时机**：摘要引擎在收到 `lesson_completed` 事件后触发，汇总该 lessonId 内的所有 `diagnosis_updated` 和 `strategy_applied`/`strategy_completed` 事件，为该课堂生成一次摘要。一节课内的多轮诊断（多个 diagnosis_updated）不单独触发摘要，统一在课堂结束时生成。若课堂异常中断（completionStatus=interrupted/timeout），仍触发摘要生成，但风险评分中 effectScore 因子不再适用（因策略未完整执行）。

## 三、摘要模板

### 3.1 模板结构

```
【一句话亮点】{shortSummary}

【课堂回顾】{fullSummary}

【成长看得见】{progress}
```

### 3.2 shortSummary 生成规则

```
function generateShort(diagnosisStatus, errorCode, questionContext):
  safeExplanation = errorTaxonomy[errorCode].parentExplanation

  if diagnosisStatus == "confirmed":
    return safeExplanation.replace("孩子", "孩子今天")
  if diagnosisStatus == "confirmed_with_reservation":
    return "今天孩子在" + questionContext.topic + "上有些犹豫，芽芽在继续观察"
  if diagnosisStatus == "inconclusive":
    return "今天孩子在" + questionContext.topic + "上遇到了一点挑战，芽芽降低了难度来帮助"
  if diagnosisStatus == "excluded":
    return "芽芽排除了一个可能的困难点，正在更准确地找到孩子需要帮助的地方"
  if diagnosisStatus == "traced":
    return "芽芽发现孩子可能需要先巩固前置知识的基础，正在帮助中"  // 具体前置知识点名称从该诊断链（同一 diagnosisId）最新一条 diagnosisStatus=traced 的 ErrorDiagnosis 记录的 parentSummary.short 中读取
```

### 3.3 fullSummary 生成规则

```
【当前学习现象】
从 answer_submitted 提取：哪道题、答了什么、花了多久
用 parentExplanation 的中性表达改写

【芽芽做了什么支持】
从 strategy_applied 提取：用了什么策略
从 error_taxonomy 提取：该策略的作用

【孩子的积极变化 / 下一步建议】
如果 diagnosisStatus = confirmed 且策略有效 → 描述变化
如果 diagnosisStatus = in_progress → 描述"芽芽正在观察"（注意：in_progress 状态下诊断引擎仍在验证，通常不触发摘要生成。若因异常收到此状态，使用通用安全措辞，不提及具体错因）
如果 effectScore >= 1 → 强调进步（effectScore 取自 strategy_completed 事件）
如果 effectScore <= 0 → 强调"继续用另一种方式帮助"（effectScore 取自 strategy_completed 事件）
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
| 含有禁止词 | +0.3/词 | 每个禁止词。检测在完整摘要文本生成后执行（即模板填充所有动态数据之后），确保填充内容（如学生答案中的词汇）也被覆盖 |
| 含有禁止表达模式 | +0.5/模式 | 模式匹配 |
| diagnosisStatus = inconclusive | +0.1 | 不确定时措辞更难把握 |
| 同一 lessonId 内连续 3 次 diagnosisStatus = inconclusive | +0.2 | 累积不确定（同一课堂内） |
| 家长上次反馈为"inaccurate" | +0.3 | 信任已受损。查询路径：从 ParentSummary 表查该学生同一 errorCode 最近一条 parentFeedback 不为 null 的记录。若为 inaccurate 则触发 |
| effectScore = -2 | +0.2 | 策略有害，摘要可能引起焦虑 |

**风险阈值**：
- riskScore < 0.3：自动发送
- 0.3 ≤ riskScore < 0.5：发送但标记"建议人工复查"
- riskScore ≥ 0.5：不发送，进入人工复审队列

> **inconclusive 计数器实现说明**："同一 lessonId 内连续 3 次 inconclusive"的计数在摘要引擎单次 lesson 处理上下文中维护内存计数器，lesson 结束后自动重置。服务重启期间未完成的 lesson 计数不保留（视为新 lesson 重新计数）。

## 六、家长反馈闭环

家长可以反馈（见 ParentSummary 表）。下表同时给出 UI 中文标签和数据库存储的英文字段值（parentFeedback 枚举），对齐 12 号策略引擎 §5.2：

| 反馈选项 | parentFeedback 枚举 | 系统动作 |
|----------|---------------------|----------|
| 准确 | accurate | 信任度 +0.1（见下方信任度定义）。Phase 1 仅记录原始反馈至 ParentSummary.parentFeedback 字段，不自动调整模板偏好 |
| 不准确 | inaccurate | 信任度 -0.2，该摘要进入 badcase 池（记录于 ParentSummary.riskFlags），下次生成时 riskScore +0.3 |
| 有帮助 | helpful | 记录该 parentExplanation 模板的正向反馈计数。`positiveFeedbackCount` 为 Phase 2 新增字段（ParentSummary 表），需同期更新 10_DATA_MODEL.md 的 ParentSummary Schema。Phase 1 暂不实现，仅记录原始反馈 |
| 不适合 | unsuitable | 将该错因在 ParentSummary 表的 `mentionPriority` 字段置为 -1（降低提及优先级），优先用 parentL1 的通用描述替代。`mentionPriority` 为 ParentSummary 表 Phase 2 新增字段（值域 -1/0/1，默认 0），需同步更新 10_DATA_MODEL.md 的 ParentSummary Schema。Phase 1 通过摘要引擎内存中的临时映射表实现同等效果 |
| 请芽芽重新观察 | reobserve | 触发该知识点重新诊断：后端在下次该学生该知识点的 answer_submitted 事件后，强制重跑完整诊断链路（标记 ignoreCache=true），不等画像推送 |

**重要规则**：家长反馈不能直接修改诊断结果或学生画像。只能影响摘要生成策略、置信度调整、badcase 复盘优先级。

**信任度（trustScore）定义**：trustScore 是摘要引擎内部维护的指标，初始值 0.5，值域 [0, 1]。每次家长反馈后更新：accurate → +0.1，inaccurate → -0.2（下限 0，上限 1）。trustScore 降至 0 后，若再次触发 inaccurate，不再扣减 trustScore 数值，但向 badcase 池追加一条优先级标记（badcase 池按标记次数排序，标记次数越多复盘优先级越高）。trustScore 为 Phase 2 新增字段（ParentSummary 表），需同期更新 10_DATA_MODEL.md 的 ParentSummary Schema。Phase 1 未实现 ParentSummary 表结构变更时，信任度计算仅在摘要引擎内存中维护，服务重启后重置为初始值 0.5。

## 七、parentExplanation 模板体系

error_taxonomy.json 中每个错因的 `parentExplanation` 字段是摘要母版。引擎从中提取关键元素：

| 错因 errorCode | parentExplanation（示例） | 摘要中使用方式 |
|---------------|------------------------------|---------------|
| decimal_point_position_error | 孩子在判断小数点位置时需要更多图示支持 | "一开始在判断小数点位置时有些犹豫" |
| calculation_error | 孩子在计算过程中出现了操作失误 | "做题过程中有一个小疏忽" |
| concept_confusion | 孩子对两个相似概念还需要更清晰的区分 | "在做题时，两个概念有点像，孩子需要更清晰的区分" |
| info_omission | 孩子在读题时可能遗漏了关键信息 | "这道题里有个小细节需要再仔细看看" |
| transfer_failure | 孩子在遇到变化后的题目时需要更多引导 | "题目变了一点点形式后，孩子需要一些引导来适应" |
| strategy_missing | 孩子在面对某些题型时还需要更多方法引导 | "知识点理解了，解题方法可以再练练" |
| question_type_unfamiliar | 孩子对这类题型的答题方式还不太熟悉 | "遇到了新的题型，芽芽给了个模板先试试" |
| expression_format_error | 孩子能把题做对，只是书写格式上需要更规范的习惯。 | "做题的时候格式上稍微注意一下就更好了" |
| prerequisite_gap | 孩子需要巩固一下之前学过的基础知识 | "需要先复习一下之前学过的内容" |
| memory_retrieval_failure | 孩子一时想不起来之前学过的方法 | "之前学过的方法暂时没想起来，芽芽给了一点提示" |
| comprehension_bias | 孩子对题目的理解可能和出题意图不完全一致 | "这道题的理解方向可以调整一下" |

模板的核心技巧：**永远不说是孩子的问题，而是描述"现象 + 芽芽在帮"。**

> **L2 错因覆盖说明**：error_taxonomy.json 中共有 86 个错因（L1 通用 10 个 + L2 数学特有 76 个），所有错因的 `parentExplanation` 字段已 100% 就绪。上表仅列 L1 作为示例。L2 错因（如 decimal_point_position_error 等）的 parentExplanation 直接读取自身字段即可。回退规则：若某错因 parentExplanation 意外为空 → 通过该错因的 `parentL1` 字段找到对应 L1 错因的 parentExplanation 作为兜底。L1 错因无 `parentL1` 字段，若其自身 parentExplanation 意外为空，使用通用安全措辞「孩子在练习中遇到了一些困难，芽芽正在帮助中」作为最终兜底。

## 八、Phase 1 实现范围

Phase 1 实现：
- [ ] 从 ErrorDiagnosis.parentSummary 读取诊断引擎预填的 short/full 作为初稿
- [ ] diagnosisStatus = confirmed → 基于 parentExplanation 生成完整摘要
- [ ] diagnosisStatus = confirmed_with_reservation → 保守措辞摘要
- [ ] diagnosisStatus = inconclusive → 通用安全摘要（不提具体错因）
- [ ] 禁止词过滤器（4.1 全量生效）
- [ ] 风险评分 + 阈值拦截（riskScore ≥ 0.5 不发送）
- [ ] 家长反馈记录（ParentSummary 表更新）
- [ ] 消费 strategy_completed 事件（事件 10），获取 effectScore 用于风险评分和摘要措辞
- [ ] shortSummary 一句话生成（Phase 1 实现全部 5 种 diagnosisStatus 的生成规则：confirmed / confirmed_with_reservation / inconclusive / excluded / traced，其中 traced 和 excluded 状态在 Phase 1 极少出现，但仍按 §3.2 规则实现）

Phase 2 补齐：
- [ ] 周/月/学期摘要
- [ ] 长期进步趋势可视化描述
- [ ] 个性化模板偏好学习

## 九、与相关文档的接口约定

| 文档 | 关系 |
|------|------|
| 09_EVENT_PROTOCOL.md | 消费 answer_submitted（事件 1，提取题目/学生回答）、lesson_completed（事件 4，提取 outcome.questionsAnswered/outcome.questionsCorrect + completionStatus 判断是否课堂中断）、diagnosis_updated（事件 8）、strategy_applied（事件 9）、strategy_completed（事件 10，获取 effectScore 进行风险评分） |
| 07_ERROR_TAXONOMY.md | 读取 parentExplanation |
| 10_DATA_MODEL.md | 读取 ErrorDiagnosis 表（parentSummary.short/full/teacherNote）、GrowthMemory 表（masteryScore）；写入 ParentSummary 表 |
| 11_DIAGNOSIS_ENGINE.md | 诊断引擎预填 parentSummary.short/full/teacherNote |
| 12_STRATEGY_ENGINE.md | 消费 strategy_applied（事件 9），提取策略名称、策略包类型 |
| 14_QUALITY_DASHBOARD.md | 摘要安全率、家长投诉率指标 |

## 十、验收标准

Phase 1 摘要引擎需通过以下验收项：

| # | 验收项 | 通过标准 | 对应章节 |
|---|--------|----------|----------|
| 1 | 触发时机 | lesson_completed 事件触发，课堂异常中断仍生成 | §2 |
| 2 | 数据读取 | 从 ErrorDiagnosis.parentSummary 读取初稿，从 error_taxonomy.json 读取 parentExplanation | §2, §7 |
| 3 | shortSummary 生成 | 5 种 diagnosisStatus 全部生成对应措辞（confirmed/confirmed_with_reservation/inconclusive/excluded/traced） | §3.2 |
| 4 | fullSummary 生成 | 含"当前学习现象+芽芽支持+下一步建议"三段。课堂中断时（completionStatus=interrupted/timeout），跳过 effectScore 相关分支（≥1/≤0），使用通用措辞 | §3.3, §2 |
| 5 | 禁止词过滤 | 完整文本生成后扫描，4.1 全量禁止词 + 4.2 禁止表达模式，检出率 100% | §4.1, §4.2 |
| 6 | 风险评分计算 | 6 项风险因素全部参与计算，riskScore ∈ [0,1]，阈值拦截逻辑正确 | §5 |
| 7 | 风险阈值拦截 | riskScore ≥ 0.5 → 不发送进复审；0.3-0.5 → 发送+标记；<0.3 → 直接发送 | §5 |
| 8 | 家长反馈记录 | 4 种 parentFeedback 选项（accurate/inaccurate/helpful/unsuitable）全部可记录至 ParentSummary.parentFeedback。reobserve 选项触发重诊断流程（标记 ignoreCache=true），不写入 parentFeedback 字段 | §6 |
| 9 | trustScore 更新 | accurate +0.1, inaccurate -0.2, 下限 0 上限 1, 触底后追加 badcase 优先级标记 | §6 |
| 10 | strategy_completed 消费 | 正确消费事件 10，提取 effectScore 参与风险评分和 fullSummary 措辞 | §5, §3.3 |
| 11 | L2 错因覆盖 | 76 个 L2 错因 parentExplanation 直接读取自身字段；意外为空时通过 parentL1 回退 | §7 |
| 12 | 课堂中断处理 | completionStatus=interrupted/timeout 仍生成摘要，effectScore 因子不适用 | §2 |

Phase 2 追加验收项（本次不纳入）：
- 周/月/学期摘要生成
- 长期进步趋势可视化描述
- 个性化模板偏好学习（positiveFeedbackCount + mentionPriority 自动调权）