# 12 策略调度引擎 v2.2.2

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | - | 初始版本：63 行骨架，散装输入/输出字段，5 步调度顺序 |
| 2.0 | 2026-05-14 | 对齐数据底座：输入改为 diagnosis_updated 事件（09 号事件 8）；6 态调度决策树（confirmed/confirmed_with_reservation/excluded/inconclusive/in_progress/traced）；策略选择算法含效能历史叠加；安全护栏（强策略触发条件、轻量兜底、滥用防护）；输出 strategy_applied 事件完整 Schema |
| 2.1 | 2026-05-14 21:21 | 交叉审计修复（17 项 + 1 笔误修正）：(1)5.1 Step 4 历史效果查询补范围（学生+策略+知识点，样本<3 扩大到学科）；(2)第五节补学习能量状态来源声明（画像系统 GrowthMemory，Phase 1 暂不生效）；(3)4.3 excluded 超时 30s→120s；(4)第五节 effectScore=-2 补触发时序说明（基于 chainId 内 strategy_completed 即时判断）；(5)5.1 Step 3 kpStrategies 从 KnowledgeNode.strategyPacks 改为 taxonomy 映射路径，对齐 10 号权威性声明；(6)5.1 算法末尾补 Step 7 强策略最终安检；(7)第五节补「连续退出」定义 + answer_abandoned 保护规则；(8)第八节补全局 vs 个人两层权重关系说明；(9)3.1 JSON 样例 alignment 09 号 v2.0.7（strategyCode→strategyPack，删 strategyName/reason，version→2.0.3）；(10)2.2 事件编号 6→5；(11)第十节事件编号修正（6→5, 10→9, 11→10）；(12)5.2 家长反馈权重补全五种枚举映射；(13)7.2「强策略同天 ≤ 2 次」明确为总次数而非种类限制；(14)4.6 移除 parentChainId 引用；(15)补充 answer_abandoned 保护规则；(16)4.4 与第五节连续错误规则统一（学习能量正常→舒缓讲解包，低能量→能量恢复包）；(17)第十一节验收标准补 4 项；(bonus)2.2 fallback 逻辑 stats 笔误→status |
| 2.2 | 2026-05-14 22:09 | 全量地狱审查修复（19 项）：(1)7.1 强策略列表移除 SP_G_C05（对齐 08 号），4.1 同步修正；(2)3 节 strategy_applied 补 triggerReason + triggerSource（对齐 09 号 v2.0.7 事件 9）；(3)2.2 删除 diagnosis_attempted.status='validated' 死代码（11 号已明确此状态不出现在该事件）；(4)5.1 Step 1 明确引用 strategy_mapping.json；(5)4.1 增加中策略定义（分步引航/审题侦探/精准计算，引用 08 号中度策略）；(6)第五节体验保护优先级冲突修复：两个最高合并并区分低能量/正常；(7)4.4 inconclusive 增加 Phase 1 学习能量降级规则；(8)第五节连续退出跨 lesson 记忆明确存储位置（GrowthMemory.pendingAction）；(9)7.2「强制切换变式」→「强制轮换备选策略包」；(10)第八节全局调权标 Phase 3；(11)第六节答题时间历史均值明确来源；（学生个人→全局 fallback）；(12)5.1 新增 Step 2 读取 ErrorDiagnosis.recommendedAction；(13)第四节增调度顺序声明（体验保护先于六态决策）；(14)7.3 引 08 号 §7.3；(15)4.6 溯源 3 层 inconclusive 判断逻辑补 traceDepth 条件；(16)第十一节验收标准补连续退出+recommendedAction；(17)同(2)；(18)多处 08 引用统一补节号；(19)5.2 历史有害行引 7.2 禁用规则 |
| 2.2.2 | 2026-05-14 22:43 | 第三轮审查修复（3 项）：(1)删除变更记录中重复的 v2.2 条目；(2)4.1 正文补「精准计算」，三策略与中策略定义框完全对齐；(3)3 节 JSON 样例 triggerSource 从 diagnosis_updated 改为 error_diagnosis（对齐 09 号 v2.0.7 事件 9 的枚举值） |
| 2.2.1 | 2026-05-14 22:21 | 第二轮审查修复（3 项）：(1)4.1 中策略编码修正（SP_G_C04→SP_G_B01 分步引航包、SP_G_D02→SP_G_B04 审题侦探包，对齐 08 号 v2.1.1）；(2)3 节 JSON 样例 triggerReason 从 comprehension_bias 改为 decimal_point_position_error（与 strategyPack=SP_M_02 上下文一致）；(3)5.2 权重表补「历史中性 effectScore=0 → ×1.0」消除逻辑空档 |
| 字段 | 用途 |
|------|------|
| diagnosisStatus | **调度分支的开关**。六态：confirmed / confirmed_with_reservation / excluded / inconclusive / in_progress / traced |
| mainHypothesis.errorCode | 主错因编码。用于选择核心策略包 |
| mainHypothesis.probability | 概率。决定策略强度（高风险用轻策略） |
| mainHypothesis.confidence | 置信度。决定是否允许强策略 |
| hypotheses[] | 完整假设集。如果主假设强制策略有风险，回退到次假设 |
| diagnosisId | 用于关联策略效果 |
| chainId | 用于追踪完整事件链 |
| studentId | 查历史策略效果 |
| knowledgeCode | 查学科专属策略 |

### 2.2 fallback 逻辑

```
如果 diagnosis_updated 不存在（老版本数据）：
  取 diagnosis_attempted
  如果 diagnosis_attempted.status = "open"：
    不触发策略，等待 diagnosis_updated
  如果 diagnosis_attempted.status = "inconclusive"：
    视为 diagnosisStatus = "inconclusive"
    只触发轻量策略
  如果 diagnosis_attempted 不存在且没有 diagnosis_updated：
    等待 diagnosis_updated 到达再做调度决策
    不基于 diagnosis_attempted.status 直接做策略选择
```

## 三、输出：strategy_applied 事件

策略选择完成后发出 strategy_applied 事件（09 号事件 9）。

```json
{
  "event": "strategy_applied",
  "version": "2.0.3",
  "chainId": "chain_a1b2c3d4",
  "studentId": "S001",
  "diagnosisId": "diag_20260514_001",
  "strategyPack": "SP_M_02",
  "triggerReason": "decimal_point_position_error",
  "triggerSource": "error_diagnosis",
  "confidenceBefore": 0.88,
  "params": {
    "difficultyAdjustment": 0,
    "questionCount": 3,
    "hintLevel": 0,
    "useTimer": false
  },
  "timestamp": "2026-05-14T10:24:00.000Z"
}
```

## 四、六态调度决策树

> **调度顺序声明**：体验保护检查（第六节）在六态决策之前执行。体验保护条件触发后直接覆盖策略选择，不再进入 4.1-4.6 的分支判断。也即：先查是否要"抢救"（体验保护），再查"怎么治"（六态决策）。

策略引擎根据 diagnosisStatus 走不同分支：

### 4.1 diagnosisStatus = confirmed（确诊）

```
mainHypothesis.probability ≥ 0.85：
  confidence ≥ 0.7 → 允许强策略（变式特训/错因专项）
  confidence < 0.7 → 只用中策略（分步引航/审题侦探/精准计算，见中策略定义框）

mainHypothesis.probability < 0.85：
  只用中策略

选策略：
  从 error_taxonomy.json 读该 errorCode 的 recommendedStrategies
  映射到策略包编码（08_STRATEGY_PACKS.md 映射表）
  叠加学生历史策略效果（有效升权、无效/有害降权）
  检查策略滥用防护（7.3 节）
  输出 strategy_applied
```

> **中策略定义**：介于强策略和轻量策略之间的策略包，包括分步引航包 SP_G_B01、审题侦探包 SP_G_B04、精准计算包 SP_G_C05（08 号将其归类为"中度策略"）。中策略的触发条件比强策略宽松：probability ≥ 0.5 即可，不要求 confidence ≥ 0.7。

### 4.2 diagnosisStatus = confirmed_with_reservation（有保留确诊）

```
probability 在 0.5-0.85，满 3 轮验证：
  只触发轻量策略：
    - 基础巩固包 SP_G_C01
    - 记忆唤醒包 SP_G_C06
  不触发强策略
  不触发中策略
  参数设置：
    questionCount = 2（低题量）
    hintLevel = 1（提供提示）
    difficultyAdjustment = -0.1（略降难度）
```

### 4.3 diagnosisStatus = excluded（假设被排除）

```
等待下一个 diagnosis_updated（诊断引擎正在切换假设）
  如果下一个 diagnosis_updated 的 diagnosisStatus = "traced" → 见 4.6
  如果下一个 diagnosis_updated 的 diagnosisStatus = "in_progress" → 不动作，继续等待
  如果超过 120 秒未收到新 diagnosis_updated → 降级：发轻量策略（基础巩固包），记录 badcase
```

### 4.4 diagnosisStatus = inconclusive（无法判断）

```
触发轻量安全策略：
  1. 基础巩固包 SP_G_C01（降低该知识点难度 + 减题量）
  2. 能量恢复包 SP_G_D03 或 舒缓讲解包 SP_G_D01（取决于学习能量状态）：
     - 连续错误 ≥ 3 且学习能量正常 → 舒缓讲解包 SP_G_D01
     - 连续错误 ≥ 3 且学习能量低或出现退出倾向 → 能量恢复包 SP_G_D03
  参数设置：
    questionCount = 1~2
    difficultyAdjustment = -0.2
    hintLevel = 1
```

> **Phase 1 学习能量降级规则**：Phase 1 如未接入画像系统的学习能量计算（见第五节声明），inconclusive 时统一按连续错误 ≥ 3 判断：连续错误 ≥ 3 → 舒缓讲解包 SP_G_D01；连续错误 < 3 → 基础巩固包 SP_G_C01（减半题量）。

### 4.5 diagnosisStatus = in_progress（验证进行中）

```
不动作。策略引擎继续等待下一个 diagnosis_updated。
不记录策略事件。
```

### 4.6 diagnosisStatus = traced（切入溯源）

```
诊断引擎已对前置知识点发起新诊断。
策略引擎通过 diagnosis_updated 的 diagnosisStatus=traced + 同一 diagnosisId 关联溯源链，不直接对原始知识点触发策略。
如果溯源的 diagnosis_updated.diagnosisStatus = "confirmed" → 对该前置知识点触发策略（回到 4.1）
如果溯源 3 层仍 inconclusive → 对原始知识点触发轻量安全策略（回到 4.4）。判断方式：策略引擎收到 diagnosis_updated.diagnosisStatus = 'inconclusive'，且该诊断链的 ErrorDiagnosis.traceDepth = 3（诊断引擎在溯源结束时写入），两个条件同时满足则触发。
```

## 五、策略选择算法

### 5.1 核心匹配

```
function selectStrategy(diagnosisUpdated, studentHistory):
  errorCode = diagnosisUpdated.mainHypothesis.errorCode
  knowledgeCode = diagnosisUpdated.knowledgeCode

  // Step 1: 从 taxonomy 取候选策略
  candidateStrategies = errorTaxonomy[errorCode].recommendedStrategies
  // 查 strategy_mapping.json 得到策略包编码（见 08 号第五节映射表）

  // Step 2: 读取诊断引擎的 recommendedAction（11 号 v2.4 在低置信度/inconclusive 时设置）
  recommendedAction = diagnosisUpdated.mainHypothesis.recommendedAction  // 可选字段
  if recommendedAction:
    if recommendedAction == "reduce_difficulty": applyDifficultyAdjustment = -0.2
    if recommendedAction == "provide_scaffolding": applyScaffolding = true (hintLevel + 1)

  // Step 3: 根据 diagnosisStatus 过滤强度
  if diagnosisStatus == "confirmed_with_reservation" or "inconclusive":
    candidateStrategies = filterLightOnly(candidateStrategies)

  // Step 4: 叠加知识点专属策略（学科专属 SP_M_*，通过 taxonomy 映射路径获取）
  // 不使用 KnowledgeNode.strategyPacks（该字段仅供教研参考，见 10 号 §4 权威性声明）
  kpStrategies = 从 taxonomy 映射后的策略包中，筛选该知识点的学科专属策略包（08 号第四节 SP_M_*）
  if kpStrategies 非空: candidateStrategies += kpStrategies

  // Step 5: 历史效果调整权重
  for each strategy in candidateStrategies:
    // 查询范围：该学生 + 该策略包 + 该知识点 的 history effectScore 均值
    // 如果该知识点下样本量 < 3，扩大到该学科下该策略的均值
    historyEffect = queryStrategyEffect({
      studentId,
      strategy,
      knowledgeCode,
      minSamples: 3,
      fallbackScope: "subject"  // 知识点样本不足时扩大到学科
    })
    if historyEffect >= 1: weight × 1.3
    if historyEffect == -1: weight × 0.5
    if historyEffect == -2: remove(strategy)  // 见 7.2 节 7 天禁用规则

  // Step 6: 滥用防护
  removeOverusedStrategies(candidateStrategies)

  // Step 7: 选最高权重
  selectedStrategy = topWeighted(candidateStrategies)

  // Step 8: 强策略最终安检
  // 如果 selectedStrategy 属于强策略（见 08 号 §7.1），再次检查 7.1 节五条件
  // 任一条件不满足 → 降级为该错因的中策略或轻量策略
  if isStrongStrategy(selectedStrategy):
    if not checkStrongConditions(selectedStrategy, diagnosisUpdated):
      selectedStrategy = fallbackToMedium(selectedStrategy.errorCode)

  return selectedStrategy
```

### 5.2 权重因子

| 因子 | 作用 | 权重 |
|------|------|------|
| taxonomy 推荐 | 主错因的直接推荐策略 | × 1.0（基准） |
| 知识点专属 | 该 KP 绑定的策略包 | × 0.8 |
| 历史有效 | StudentStrategyEffect > 0 | × 1.3 |
| 历史中性 | StudentStrategyEffect = 0 | × 1.0（不调整权重） |
| 历史无效 | StudentStrategyEffect < 0 | × 0.5 |
| 历史有害 | StudentStrategyEffect = -2 | 标记为禁用（见 7.2 节 7 天禁用规则） |
| 冷启动折扣 | sampleCount < 30 | × 0.7 |
| 同天频次 > 3 | 疲劳防护 | 移除 |
| 家长标记 | parentFeedback = "unsuitable" → × 0.3；parentFeedback = "helpful" → × 1.2；parentFeedback = "accurate" / "inaccurate" → 不影响权重（标记人工复核）；parentFeedback = "reobserve" → 不影响权重但降低该策略的 confidence 贡献 |

## 六、体验保护覆盖规则

在策略选择之前，先检查体验保护条件：

| 条件 | 覆盖动作 | 优先级 |
|------|----------|--------|
| 同一知识点连续错 ≥ 3 道 + 学习能量状态 = "low" | 能量恢复包 SP_G_D03 | 最高 |
| 同一知识点连续错 ≥ 3 道 + 学习能量正常 | 舒缓讲解包 SP_G_D01 | 高 |
| 答题时间 > 历史均值 3σ（挣扎） | 能量恢复包 SP_G_D03 + difficultyAdjustment = -0.3 | 高 |

> **历史均值说明**：指该学生该知识点的作答时间均值。冷启动时（学生该知识点样本 < 3）使用该年级该知识点的全局均值作为 fallback。
| 上一策略 effectScore = -2 | 基础巩固包 SP_G_C01（安全兜底） | 高 |

> **effectScore = -2 的触发时序**：此条件基于当前 chainId 内的 strategy_completed 事件即时判断，不等 StrategyEffect 表异步写入。触发一次基础巩固包兜底后，同时将该策略标记为待禁用——由 7.2 节的 7 天禁用规则接管后续保护。
| 5 分钟内连续退出 | 下次进入时能量恢复包 | 中 |
| 同一 lessonId 内连续 3 次 answer_abandoned | 能量恢复包 SP_G_D03 或舒缓讲解包 SP_G_D01 | 高 |

> **学习能量状态来源**：由画像系统根据连续错误次数、答题时长趋势、求助频率等行为信号综合计算，存储在 GrowthMemory 表中。Phase 1 如未接入画像系统的学习能量计算，该条件暂时不生效。
>
> **连续退出定义**：同一 lessonId 内连续 2 次 answer_abandoned，或 lesson_completed.completionStatus = interrupted。触发后，将该标记写入 GrowthMemory 的 pendingAction 字段（如 `{"type": "energy_recovery", "trigger": "consecutive_exit"}`），下一次 lesson_started 时策略引擎读取该字段并预设能量恢复包，读取后清除。

体验保护条件触发后，跳过主错因匹配——先恢复状态，再谈策略。

## 七、安全护栏

### 7.1 强策略触发条件

以下策略为"强策略"：变式特训包 SP_G_C02 / 错因专项包 SP_G_C03

必须同时满足：
1. diagnosisStatus = confirmed
2. mainHypothesis.probability ≥ 0.85
3. mainHypothesis.confidence ≥ 0.7
4. sampleCount ≥ 30（非冷启动）
5. 该策略历史 effectScore 不低于 -1

### 7.2 策略频率限制

| 限制 | 说明 |
|------|------|
| 同策略同天 ≤ 3 次 | 超过后当天禁用 |
| 同策略连续使用 ≤ 5 次 | 第 6 次强制轮换为备选策略包（如当前用审题侦探包则切换到同错因的分步引航包） |
| 强策略同天 ≤ 2 次 | 同一天内强策略触发总次数 ≤ 2 次，不受策略包种类限制 |
| effectScore = -2 的策略 7 天内禁用 | 给策略冷却期 |

### 7.3 冷启动保护

sampleCount < 30 时：
- 所有强策略关闭
- 策略参数自动降级：questionCount 减半，hintLevel + 1，difficultyAdjustment - 0.2
- 优先使用 08 号 §7.3 定义的轻量安全策略（不依赖学科数据）

## 八、策略效能回写

策略执行完成（收到 strategy_completed 事件）后：

1. 记录 StrategyEffect（见 10_DATA_MODEL.md）
2. 更新 GrowthMemory 中的 strategyHistory
3. 如果 effectScore = -2：标记该策略对应该学生的"禁用 7 天"
4. （Phase 3）如果连续 3 次 effectScore ≤ 0：降级该策略的默认权重（全局生效）。Phase 1 仅做学生级权重调整（5.1 节 Step 5），不做全局自动调权。

> **两层权重关系**：学生个人权重（5.1 节 Step 4）作用于单次策略选择。全局权重（本节）作用于策略包的基准权重，影响所有学生对该策略的初始倾向。两者独立计算，不叠乘。全局权重 < 0.3 时该策略包进入教研复审流程，不在引擎内自动下线。

## 九、Phase 1 实现边界

Phase 1 策略引擎实现范围：

- [ ] 消费 diagnosis_updated 事件（六态全处理）
- [ ] 6 态决策树（4.1-4.6）
- [ ] 体验保护覆盖逻辑（第五节）
- [ ] 安全护栏（强策略条件 + 频率限制 + 冷启动保护）
- [ ] 策略选择算法（核心匹配 + 5 权重因子）
- [ ] 输出 strategy_applied 事件
- [ ] 消费 strategy_completed 事件 + 回写策略效果

Phase 1 不实现：
- 家长偏好叠加（Phase 2）
- 策略效能全局自动调权（Phase 3）
- 多策略并行对比实验（Phase 3）

## 十、与相关文档的接口约定

| 文档 | 消费关系 |
|------|----------|
| 09_EVENT_PROTOCOL.md | 输入：diagnosis_updated（事件 8）、diagnosis_attempted（事件 5，fallback）。输出：strategy_applied（事件 9），含 triggerReason、triggerSource（见 09 号事件 9 Schema）。消费：strategy_completed（事件 10） |
| 08_STRATEGY_PACKS.md | 读取策略包定义、第五节映射表（strategy_mapping.json）、安全边界 |
| 07_ERROR_TAXONOMY.md | 读取错因的 recommendedStrategies |
| 10_DATA_MODEL.md | 写入 StrategyEffect；读取 StudentStrategyEffect 历史 |
| 11_DIAGNOSIS_ENGINE.md | 诊断引擎只输出 recommendedAction 建议，策略引擎执行实际操作 |
| 14_QUALITY_DASHBOARD.md | 策略有效率、提示依赖变化指标的数据来源 |

## 十一、验收标准

- [ ] diagnosisStatus = confirmed + prob≥0.85 → 1 秒内发出 strategy_applied（含强策略）
- [ ] diagnosisStatus = confirmed_with_reservation → 仅轻量策略，无强策略
- [ ] diagnosisStatus = inconclusive → 仅基础巩固包
- [ ] 体验保护条件触发 → 覆盖主错因匹配
- [ ] 同策略同天 ≤ 3 次生效
- [ ] sampleCount < 30 → 所有强策略关闭
- [ ] strategy_completed 后回写 StrategyEffect
- [ ] effectScore = -2 → 该策略 7 天内禁用于该学生
- [ ] diagnosisStatus = traced → 策略引擎跟踪溯源链，不直接对原始知识点触发策略
- [ ] diagnosisStatus = excluded 且超时 120 秒 → 降级为轻量策略
- [ ] 体验保护「同一 lessonId 内连续 3 次 answer_abandoned」正确触发能量恢复包
- [ ] 强策略五条件全部满足时才触发（缺一不可）
- [ ] 连续退出（2 次 answer_abandoned 或 lesson_completed.interrupted）后，下次 lesson_started 时预设能量恢复包（通过 GrowthMemory.pendingAction 传递）
- [ ] 策略引擎读取 ErrorDiagnosis.recommendedAction 并据此调整 params（如 reduce_difficulty → difficultyAdjustment = -0.2）