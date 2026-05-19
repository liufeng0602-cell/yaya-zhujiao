# 14 质量仪表盘 v2.4.1

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | - | 初始版本：96 行，24 指标 + 8 badcase 类型 + 优先级排序 |
| 2.0 | 2026-05-14 | 对齐数据底座：9 铁规门禁集成（data_quality_gate.py v2.0）；指标公式化（每项可计算）；badcase 管理体系完整化；自动 top 10 算法；Phase 1 仪表盘 JSON Schema |
| 2.4.1 | 2026-05-15 03:27 | 地狱级交叉审查（4 项）：(1)§7 删除"提示依赖变化"阈值行——阈值表设了绿黄红但下面注释又把它列入"仅展示指标"，自相矛盾（Phase 1 冷启动永远返回 null，阈值形同虚设）；(2)§4 R3 说明修正——原"相邻 KP 的 keyPoints 不能完全相同"把 data_quality_gate.py 的 R3 检查范围砍掉了 90%，实际 R3 是所有字段跑真实数据分布，>80% 同值触发 WARN；(3)§4 R5/R6 说明修正——R5 原列 6 个字段（name/grade/book/unit/lesson/level）错了 2 个漏了 9 个，改为完整的 15 个必填字段名；R6 原写"level 字段与 levelScore 阈值一致"实为跨文件一致性校验，改为"knowledge.json 的 curriculumLevel 必须与 levels.json 的 level 分类一致"；(4)§5.1 #5 全选 A 触发条件消岐——原"A 选项占比 > 80% 且绝对占比 > 60%"两个"占比"混淆，改为"该题总答题次数 ≥ 10 且 A 选项被选比例 > 80%"，样本量守卫 + 单阈值更清晰 |
| 2.4 | 2026-05-15 00:08 | 地狱级交叉审查（4 项）：(1)§3.3 #16 状态卡选择率移至 Phase 3（换卡动作需 state_card_selected 事件），Phase 1 降级为状态卡类型分布（基于 lesson_started.stateCard）；(2)§7 补 16 项仅展示指标声明，明确不设红黄绿告警阈值；(3)§8 Phase 1 #12 提示依赖变化展开为独立条目，与 #11 格式对齐；(4)§5.1 #2 策略无效补 12 号 §7.2/§8 交叉引用，强调双向独立、修改任一侧需同步 review |
| 2.3 | 2026-05-15 00:03 | 地狱级交叉审查（8 项全修）：(1)§3.1 #4 策略包覆盖率 12/39→14/40，对齐 08 号附录 A；(2)§3.3 #18 家长摘要打开率标注 Phase 3（需 parent_summary_opened 事件）；(3)§3.3 #17 问卷完成率标注 Phase 3（需 preference_survey_submitted 事件）；(4)§3.2 #11 知识点后续正确率标注 Phase 2（需 followup_assessment 事件）Phase 1 值恒为 null；(5)§3.2 #12 提示依赖变化补冷启动规则（样本<30 不计算）；(6)§5.1 #4 摘要表达风险明确 Phase 1 仅 riskScore 触发，投诉类 badcase 人工创建；(7)§5.1 #5 全选 A 补绝对占比下限 + Phase 2 选项数归一化；(8)§5.1 #6 讲解质量问题补 time boundary + Phase 1 实现方式 + Phase 3 扩展说明；(9)第八节重构为 Phase 1/2/3 三级，每个指标标注所属 Phase 及所需事件 |
| 2.2 | 2026-05-14 23:57 | 地狱级交叉审查（6 项，4 修 2 验）：(1)§5.1 #1 错因误判触发条件补"教研手动排查"，明确非自动流程（13 号 §6 inaccurate 不触发自动验证排除）；(2)§5.1 #4 家长投诉标注 Phase 2 待定义（13 号正文无投诉入口）；(3)§3.4 #21 "AI 摘要安全率"→"摘要安全率"（去掉 AI 前缀，与 §7/§9 统一）；(4)§5.1 #5 同题抛弃率/全选 A 补数据来源（09 号 answer_abandoned/answer_submitted 事件）；(5)§5.1 #7 chainId 已验证：09 号 §1.2 有完整定义，不需要修；(6)§3.3 #16 状态卡选择率已验证：stateCard 在 09 号 answer_submitted 和 11 号诊断引擎均有定义，不需要修 |
| 2.1 | 2026-05-14 21:30 | 交叉审计修复（4 项）：(1)第九节接口表补 08_STRATEGY_PACKS.md 和 11_DIAGNOSIS_ENGINE.md；(2)badcase 错因误判触发条件补 inaccurate 英文字段（对齐 12 号 §5.2、13 号 §六）；(3)验证题覆盖率公式「错误码」→「错因码」统一术语；(4)12 号数据来源描述改为「策略有效率、二次正确率」 |

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

这是芽芽助教产品文档集的第 14 号文件，定义 24 个可计算指标（覆盖类 6 + 教学效果类 6 + 用户体验类 6 + 内容质量类 6）、badcase 管理体系和自动 top 10 算法。它回答「系统哪里好、哪里差、先修什么」——是单人维护整个系统的控制台，集成了 data_quality_gate.py 的 9 铁规门禁结果。

## 一、目标

质量仪表盘是一个人维护整个系统的控制台，回答一个问题：**"现在，优先修什么？"**

不是给领导看的 PPT，是给自己看的待修清单。

## 二、仪表盘 JSON Schema

```json
{
  "dashboardId": "qa_20260514",
  "generatedAt": "2026-05-14T12:00:00.000Z",
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

## 三、一级指标（24 项）

### 3.1 覆盖类（6 项）

| # | 指标 | 公式 | 当前值 | 目标 |
|---|------|------|--------|------|
| 1 | 知识点覆盖率 | 已覆盖 KP / 教材全量 KP | 394/394 = 100% | 100% |
| 2 | 题型覆盖率 | 有题 KP / 全量 KP | 待统计 | 100% |
| 3 | 错因覆盖率 | 绑定错因种类 / taxonomy 全量 | 86/86 = 100% | 100% |
| 4 | 策略包覆盖率 | 已实现策略包 / 定义策略包 | 0/40 = 0% | Phase 1: 14/40 = 35%（见 08 号附录 A 策略包清单） |
| 5 | 验证题覆盖率 | 有验证题的错因码 / 全量错因码 | 待统计 | Phase 1: ≥ 50% |
| 6 | 家长摘要覆盖率 | 有摘要 KP / 全量 KP | 待统计 | Phase 2: 100% |

### 3.2 教学效果类（6 项）

| # | 指标 | 公式 | 说明 |
|---|------|------|------|
| 7 | 错因命中率 | 验证确诊数 / 诊断发起数 | 高→诊断准；低→错因库不全 |
| 8 | 验证题通过率 | supported 次数 / 总验证次数 | 高→假设不对；低→可能已确诊 |
| 9 | 策略有效率 | effectScore≥1 次数 / 策略执行总数 | 高→策略好；低→需换策略 |
| 10 | 二次正确率 | 策略后同类题正确 / 策略后同类题总数 | 策略短期效果 |
| 11 | 知识点后续正确率 | 7 天内同 KP 正确率变化 | Phase 2 启用（需 followup_assessment 事件）。Phase 1 值恒为 null |
| 12 | 提示依赖变化 | 当前 hintUsed 率 - 上周 hintUsed 率 | 负值→进步；正值→依赖加深。冷启动期（学生答题样本 < 30）不计算，Phase 1 样本不足时返回 null |

### 3.3 用户体验类（6 项）

| # | 指标 | 公式 | 说明 |
|---|------|------|------|
| 13 | 学习完成率 | lesson_completed / lesson_started | 低→体验问题 |
| 14 | 中途退出率 | 中途退出次数 / 做题总数 | 高→难度或体验问题 |
| 15 | 连错后继续率 | 连错 3+ 后继续 / 连错 3+ 总数 | 体现韧性 |
| 16 | 状态卡选择率 | Phase 3 启用（需 state_card_selected 事件追踪换卡动作）。Phase 1 降级为状态卡类型分布：各状态卡类型占比（基于 lesson_started.stateCard 字段统计），不计算"换卡"次数 | Phase 3 启用。Phase 1 提供状态卡类型分布作为替代指标 |
| 17 | 问卷完成率 | 完成的问卷 / 推送的问卷 | Phase 3 启用（需 preference_survey_submitted 事件） |
| 18 | 家长摘要打开率 | 摘要已读 / 摘要发送 | Phase 3 启用（需 parent_summary_opened 事件） |

### 3.4 内容质量类（6 项）

| # | 指标 | 公式 | 说明 |
|---|------|------|------|
| 19 | AI 生成题目可用率 | 人工通过数 / AI 生成数 | Phase 3 启用 |
| 20 | AI 生成讲解可用率 | 人工通过数 / AI 生成数 | Phase 3 启用 |
| 21 | 摘要安全率 | 未被拦截的摘要 / 总摘要数 | riskScore < 0.5 的占比 |
| 22 | Gate 失败率 | gate fail 次数 / gate 执行次数 | 数据质量 |
| 23 | 人工修正次数 | 人工修改数据文件次数 | 数据稳定性 |
| 24 | badcase 数量 | 当前 open 状态 badcase 数 | 系统债务 |

## 四、9 铁规门禁集成

仪表盘直接读取 data_quality_gate.py v2.0 的 9 项输出：

| 铁规 | 简称 | 状态 | 说明 |
|------|------|------|------|
| R1 | levelScore 禁手填 | PASS/FAIL | A3/B6/C9/D12 |
| R2 | 三文件代码对账 | PASS/FAIL | knowledge + graph + levels 三文件 code 一致 |
| R3 | 字段区分度 | PASS/FAIL | 所有字段跑真实数据分布检查，>80% 同值触发 WARN（不限于 keyPoints，不限于相邻 KP） |
| R4 | 错因全引用 | PASS/FAIL | KP 绑定的 errorCode 必须在 taxonomy 中存在 |
| R5 | 必填字段完整 | PASS/FAIL | 15 个必填字段非空：knowledgeCode / name / unit / book / grade / curriculumLevel / curriculumLevelLabel / levelScore / teachingGoal / keyPoints / commonMistakes / tags / verifiedBy / confidence / status |
| R6 | 级别标签一致 | PASS/FAIL | knowledge.json 的 curriculumLevel 必须与 levels.json 的 level 分类一致 |
| R7 | A 级绑定 ≥ 3 | PASS/FAIL | 每个 A 级 KP 至少绑 3 个错因 |
| R8 | 图谱双向边一致 | PASS/FAIL | prerequisites 和 next 双向对称 |
| R9 | 题库矩阵全覆盖 | PASS/FAIL | 所有 questionTypes 在矩阵中有定义 |

门禁脚本位置：acceptance-artifacts/data_quality_gate.py

仪表盘每次生成时自动跑一次门禁，将结果写入 gateStatus。

## 五、badcase 管理体系

### 5.1 badcase 类型（8 类）

| # | 类型 | 触发条件 | 严重度 |
|---|------|----------|--------|
| 1 | 错因误判 | 家长反馈 inaccurate + 教研团队手动排查后诊断被排除（非自动验证流程，见 13 号 §6 inaccurate 反馈仅扣 trustScore，不触发自动验证排除） | high |
| 2 | 策略无效 | effectScore = -1 连续 3 次或 -2 1 次（禁用规则见 12 号 §7.2 7 天禁用和 §8 全局调权降级；仪表盘 badcase 与策略引擎规则双向独立、各司其职，修改任一侧需同步 review 另一侧） | high |
| 3 | 策略造成依赖 | 提示依赖变化 > +0.3 | medium |
| 4 | 摘要表达风险 | riskScore ≥ 0.5（见 13 号 §5 阈值规则）。Phase 1 仅由 riskScore 触发，不启用家长投诉自动检测（所有投诉类 badcase 由人工手动创建）。家长投诉渠道的自动检测在 Phase 2 定义 | high |
| 5 | 题目质量问题 | 同题抛弃率 > 50%（基于 09 号 answer_abandoned 事件，同一 questionId 抛弃次数/该题出现总次数）；全选 A（同一 questionId 下该题总答题次数 ≥ 10 且 A 选项被选比例 > 80%，基于 answer_submitted 事件。Phase 1 使用固定阈值 80%，Phase 2 引入选项数归一化：阈值 = (100%/选项数) × 3） | medium |
| 6 | 讲解质量问题 | 策略执行后同知识点连续错 ≥ 3 道（基于 strategy_completed 事件之后的 answer_submitted 事件，同一 lessonId 内同一 knowledgeCode 判断）。Phase 3 上线 explanation_replayed 事件后扩展至讲解场景 | medium |
| 7 | 行为数据异常 | chainId 缺失 / timestamp 乱序 | low |
| 8 | Gate 漏检 | 已知错误但门禁未拦截 | critical |

### 5.2 badcase 完整 Schema

```json
{
  "badcaseId": "bc_20260514_001",
  "type": "error_misclassification",
  "severity": "high",
  "status": "open",
  "studentId": "S001",
  "knowledgeCode": "M5S1-0",
  "questionId": "Q_M5S1_DM_045",
  "diagnosisId": "diag_20260514_001",
  "relatedEventIds": ["evt_20260514_001", "evt_20260514_005"],
  "description": "系统判断为计算失误，但家长反馈指出实际是列式错误。后续验证排除了计算失误假设。",
  "rootCause": "calculation_error 的排除条件未覆盖"列式错误+计算数字正确"的组合",
  "fixAction": "在 error_taxonomy.json 的 calculation_error.exclusionConditions 中检查列式错误条件",
  "fixTarget": "error_taxonomy.json → calculation_error → exclusionConditions",
  "createdAt": "2026-05-14T12:00:00.000Z",
  "resolvedAt": null,
  "resolvedBy": null
}
```

### 5.3 badcase 优先级排序

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

## 六、自动 top 10 待修问题

仪表盘每次生成时自动产出 top 10 待修问题（按优先级排序）。

生成算法：

```
function generateTop10(metrics, gateStatus, badcases):
  issues = []

  // 1. Gate 失败项
  for each gate in gateStatus where status == "FAIL":
    issues.add({priority: "critical", source: "gate", item: gate.name + " 校验未通过"})

  // 2. Critical badcases
  issues += badcases.filter(bc => bc.severity == "critical")

  // 3. 覆盖缺口
  for each metric in 覆盖类 where value < target:
    issues.add({priority: "high", source: "coverage", item: metric.name + " 当前" + value + " 目标" + target})

  // 4. 效果恶化
  for each metric in 教学效果类 where trend == "worsening":
    issues.add({priority: "medium", source: "effectiveness", item: metric.name + " 持续恶化"})

  // 5. High badcases
  issues += badcases.filter(bc => bc.severity == "high")

  // 6. 排序：critical > high > medium > low
  // 同类内按出现时间倒序
  return issues.sort().slice(0, 10)
```

## 七、阈值与告警

| 指标 | 绿色 | 黄色 | 红色 |
|------|------|------|------|
| 知识点覆盖率 | = 100% | - | < 100% |
| 门禁状态 | 9/9 PASS | - | < 9 PASS |
| 策略有效率 | ≥ 0.6 | 0.4-0.6 | < 0.4 |
| 错因命中率 | ≥ 0.7 | 0.5-0.7 | < 0.5 |
| 中途退出率 | < 0.1 | 0.1-0.2 | > 0.2 |
| 摘要安全率 | = 100% | ≥ 0.95 | < 0.95 |
| badcase open | < 5 | 5-15 | > 15 |

红色指标自动进入 top 10 待修。

> 其余 16 项指标（#2 题型覆盖率、#4 策略包覆盖率、#5 验证题覆盖率、#6 家长摘要覆盖率、#10 二次正确率、#11 知识点后续正确率、#12 提示依赖变化、#13 学习完成率、#15 连错后继续率、#16 状态卡选择率、#17 问卷完成率、#18 家长摘要打开率、#19 AI 生成题目可用率、#20 AI 生成讲解可用率、#22 Gate 失败率、#23 人工修正次数）为仅展示指标，不设红黄绿告警阈值。Phase 2/3 启用后逐步追加阈值定义。

## 八、Phase 实现范围

Phase 1 实现：
- [ ] 仪表盘 JSON Schema 定义
- [ ] 9 铁规门禁集成（自动跑 data_quality_gate.py）
- [ ] 覆盖类 6 指标全量计算
- [ ] 教学效果类可计算指标：#7 错因命中率、#8 验证题通过率、#9 策略有效率、#10 二次正确率。不计算：#11 知识点后续正确率（需 followup_assessment 事件 → Phase 2）、#12 提示依赖变化（冷启动期样本 < 30 返回 null，Phase 2 启用完整计算）
- [ ] 用户体验类可计算指标：#13 学习完成率、#14 中途退出率、#15 连错后继续率（#16 状态卡选择率需 state_card_selected 事件 → Phase 3；#17 问卷完成率需 preference_survey_submitted → Phase 3；#18 家长摘要打开率需 parent_summary_opened → Phase 3）
- [ ] 内容质量类可计算指标：#21 摘要安全率、#22 Gate 失败率、#23 人工修正次数、#24 badcase 数量（#19/20 AI 生成题目/讲解可用率 → Phase 3）
- [ ] badcase 录入/查询/统计
- [ ] 自动 top 10 生成
- [ ] 红黄绿阈值告警

Phase 2 补齐：
- [ ] #11 知识点后续正确率（需 followup_assessment 事件）
- [ ] 家长投诉自动检测（badcase #4 扩展）
- [ ] badcase → 教研修正的自动化流程
- [ ] 全选 A 选项数归一化（阈值动态计算）

Phase 3 补齐：
- [ ] #16 状态卡选择率（需 state_card_selected 事件）
- [ ] #17 问卷完成率（需 preference_survey_submitted 事件）
- [ ] #18 家长摘要打开率（需 parent_summary_opened 事件）
- [ ] #19 AI 生成题目可用率
- [ ] #20 AI 生成讲解可用率
- [ ] badcase #6 讲解场景扩展（需 explanation_replayed 事件）

## 九、与相关文档的接口约定

| 文档 | 关系 |
|------|------|
| 05_COVERAGE_GATE.md | 门禁规则定义 |
| 08_STRATEGY_PACKS.md | 策略包定义清单、覆盖率目标参考 |
| 09_EVENT_PROTOCOL.md | badcase 关联事件 ID |
| 10_DATA_MODEL.md | badcase 表结构 |
| 11_DIAGNOSIS_ENGINE.md | 错因命中率、验证题通过率数据来源 |
| 12_STRATEGY_ENGINE.md | 策略有效率、二次正确率数据来源 |
| 13_PARENT_SUMMARY_RULES.md | 摘要安全率数据来源 |
| data_quality_gate.py | 门禁执行脚本，仪表盘直接调用 |
