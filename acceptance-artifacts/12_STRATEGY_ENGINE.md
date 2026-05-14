# 12 策略调度引擎 v2.0

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | - | 初始版本：63 行骨架，散装输入/输出字段，5 步调度顺序 |
| 2.0 | 2026-05-14 | 对齐数据底座：输入改为 diagnosis_updated 事件（09 号事件 8）；6 态调度决策树（confirmed/confirmed_with_reservation/excluded/inconclusive/in_progress/traced）；策略选择算法含效能历史叠加；安全护栏（强策略触发条件、轻量兜底、滥用防护）；输出 strategy_applied 事件完整 Schema |

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

这是芽芽助教产品文档集的第 12 号文件，定义六态调度决策树（根据 diagnosisStatus 走不同分支）、策略选择算法（含效能历史叠加）、安全护栏（强策略触发条件、轻量兜底、滥用防护）。它回答「芽芽该做什么」——消费 diagnosis_updated 事件，产出 strategy_applied 事件。本引擎依赖 08 号（策略包定义）、09 号（事件协议）、11 号（诊断结果）。

## 一、职责定义

策略引擎是诊断后的"行动系统"。诊断引擎告诉你"学生错在哪里"，策略引擎决定"芽芽该做什么"。

不负责出题、不负责讲解内容生成、不负责难度调整。只负责**选择策略包 + 设置参数**，由执行层（前端/题库服务）落地。

## 二、输入：diagnosis_updated 事件

策略引擎直接消费 diagnosis_updated 事件（09 号事件 8）。如果当前诊断只有一轮（没有触发验证），fallback 到 diagnosis_attempted（09 号事件 6）。

### 2.1 必读字段

从 diagnosis_updated 事件中提取：

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
  如果 diagnosis_attempted.stats = "open"：
    不触发策略，等待 diagnosis_updated
  如果 diagnosis_attempted.stats = "validated"：
    视为 diagnosisStatus = "confirmed"
  如果 diagnosis_attempted.stats = "inconclusive"：
    视为 diagnosisStatus = "inconclusive"
    只触发轻量策略
```

## 三、输出：strategy_applied 事件

策略选择完成后发出 strategy_applied 事件（09 号事件 10）。

```json
{
  "event": "strategy_applied",
  "version": "2.0",
  "chainId": "chain_a1b2c3d4",
  "studentId": "S001",
  "diagnosisId": "diag_20260514_001",
  "strategyCode": "SP_M_02",
  "strategyName": "小数点定位包",
  "reason": "主错因小数点定位错误确诊，概率0.88，适合强策略",
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

策略引擎根据 diagnosisStatus 走不同分支：

### 4.1 diagnosisStatus = confirmed（确诊）

```
mainHypothesis.probability ≥ 0.85：
  confidence ≥ 0.7 → 允许强策略（变式特训/精准计算/错因专项）
  confidence < 0.7 → 只用中策略（分步引航/审题侦探）

mainHypothesis.probability < 0.85：
  只用中策略

选策略：
  从 error_taxonomy.json 读该 errorCode 的 recommendedStrategies
  映射到策略包编码（08_STRATEGY_PACKS.md 映射表）
  叠加学生历史策略效果（有效升权、无效/有害降权）
  检查策略滥用防护（7.3 节）
  输出 strategy_applied
```

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
  如果超过 30 秒未收到新 diagnosis_updated → 降级：发轻量策略（基础巩固包），记录 badcase
```

### 4.4 diagnosisStatus = inconclusive（无法判断）

```
触发轻量安全策略：
  1. 基础巩固包 SP_G_C01（降低该知识点难度 + 减题量）
  2. 舒缓讲解包 SP_G_D01（如果连续错误 ≥ 3）
  参数设置：
    questionCount = 1~2
    difficultyAdjustment = -0.2
    hintLevel = 1
```

### 4.5 diagnosisStatus = in_progress（验证进行中）

```
不动作。策略引擎继续等待下一个 diagnosis_updated。
不记录策略事件。
```

### 4.6 diagnosisStatus = traced（切入溯源）

```
诊断引擎已对前置知识点发起新诊断。
策略引擎跟踪 parentChainId，但不直接对原始知识点触发策略。
如果溯源的 diagnosis_updated.diagnosisStatus = "confirmed" → 对该前置知识点触发策略（回到 4.1）
如果溯源 3 层仍 inconclusive → 对原始知识点触发轻量安全策略（回到 4.4）
```

## 五、策略选择算法

### 5.1 核心匹配

```
function selectStrategy(diagnosisUpdated, studentHistory):
  errorCode = diagnosisUpdated.mainHypothesis.errorCode
  knowledgeCode = diagnosisUpdated.knowledgeCode

  // Step 1: 从 taxonomy 取候选策略
  candidateStrategies = errorTaxonomy[errorCode].recommendedStrategies
  // 映射到策略包编码（08_STRATEGY_PACKS.md 映射表）

  // Step 2: 根据 diagnosisStatus 过滤强度
  if diagnosisStatus == "confirmed_with_reservation" or "inconclusive":
    candidateStrategies = filterLightOnly(candidateStrategies)

  // Step 3: 叠加知识点专属策略
  kpStrategies = knowledgeGraph[knowledgeCode].strategyPacks
  candidateStrategies += kpStrategies

  // Step 4: 历史效果调整权重
  for each strategy in candidateStrategies:
    historyEffect = queryStrategyEffect(studentId, strategy)
    if historyEffect >= 1: weight × 1.3
    if historyEffect == -1: weight × 0.5
    if historyEffect == -2: remove(strategy)  // 禁用 7 天

  // Step 5: 滥用防护
  removeOverusedStrategies(candidateStrategies)

  // Step 6: 选最高权重
  return topWeighted(candidateStrategies)
```

### 5.2 权重因子

| 因子 | 作用 | 权重 |
|------|------|------|
| taxonomy 推荐 | 主错因的直接推荐策略 | × 1.0（基准） |
| 知识点专属 | 该 KP 绑定的策略包 | × 0.8 |
| 历史有效 | StudentStrategyEffect > 0 | × 1.3 |
| 历史无效 | StudentStrategyEffect < 0 | × 0.5 |
| 历史有害 | StudentStrategyEffect = -2 | 移除 |
| 冷启动折扣 | sampleCount < 30 | × 0.7 |
| 同天频次 > 3 | 疲劳防护 | 移除 |
| 家长标记 | parentFeedback = "unsuitable" | × 0.3 |

## 六、体验保护覆盖规则

在策略选择之前，先检查体验保护条件：

| 条件 | 覆盖动作 | 优先级 |
|------|----------|--------|
| 同一知识点连续错 ≥ 3 道 | 能量恢复包 SP_G_D03 | 最高 |
| 学习能量状态 = "low" | 舒缓讲解包 SP_G_D01 | 最高 |
| 答题时间 > 历史均值 3σ（挣扎） | 能量恢复包 SP_G_D03 + difficultyAdjustment = -0.3 | 高 |
| 上一策略 effectScore = -2 | 基础巩固包 SP_G_C01（安全兜底） | 高 |
| 5 分钟内连续退出 | 下次进入时能量恢复包 | 中 |

体验保护条件触发后，跳过主错因匹配——先恢复状态，再谈策略。

## 七、安全护栏

### 7.1 强策略触发条件

以下策略为"强策略"：变式特训包 SP_G_C02 / 精准计算包 SP_G_C05 / 错因专项包 SP_G_C03

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
| 同策略连续使用 ≤ 5 次 | 第 6 次强制切换变式 |
| 强策略同天 ≤ 2 种不同类型 | 防止过度干预 |
| effectScore = -2 的策略 7 天内禁用 | 给策略冷却期 |

### 7.3 冷启动保护

sampleCount < 30 时：
- 所有强策略关闭
- 策略参数自动降级：questionCount 减半，hintLevel + 1，difficultyAdjustment - 0.2
- 优先使用通用轻量策略（不依赖学科数据）

## 八、策略效能回写

策略执行完成（收到 strategy_completed 事件）后：

1. 记录 StrategyEffect（见 10_DATA_MODEL.md）
2. 更新 GrowthMemory 中的 strategyHistory
3. 如果 effectScore = -2：标记该策略对应该学生的"禁用 7 天"
4. 如果连续 3 次 effectScore ≤ 0：降级该策略的默认权重（全局生效）

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
| 09_EVENT_PROTOCOL.md | 输入：diagnosis_updated（事件 8）、diagnosis_attempted（事件 6，fallback）。输出：strategy_applied（事件 10）。消费：strategy_completed（事件 11） |
| 08_STRATEGY_PACKS.md | 读取策略包定义、映射表、安全边界 |
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
