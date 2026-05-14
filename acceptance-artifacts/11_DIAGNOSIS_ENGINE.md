# 11 错因诊断引擎 v2.4.2

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | - | 初始版本：90 行草案，输入输出散装字段 |
| 2.0 | 2026-05-14 | 对齐 09_EVENT_PROTOCOL v2.0.1：输入改为 answer_submitted 事件（三层结构）；输出改为 diagnosis_attempted 事件完整 Schema；新增 chainId 串联规则；明确四步诊断流程（初筛→匹配→验证→溯源）；补全 probability/confidence 区别；答对跳过三例外；放弃跳过规则；连错确诊与 inconclusive 边界；溯源最深3层规则 |
| 2.1 | 2026-05-14 | 自检修复：补多轮验证中间状态规则（同一 chainId/同一 diagnosisId 发出新 validation_triggered 而非新 diagnosis_attempted）；冷启动 method 改回 rule_engine（通过 confidence 打折标记而非 method 特殊值，对齐 09 号 method 枚举） |
| 2.2 | 2026-05-14 | 对齐 09_EVENT_PROTOCOL v2.0.2（新增 diagnosis_updated 事件）：新增 3.3 节 diagnosis_updated 事件输出规则（status/diagnosisStatus 对照表、策略引擎消费规则）；修正第四节流程图（验证→判断与溯源分支结构）；概率乘法加 min(rawProbability, 0.95) 上限防爆炸；次高假设验证入口规则（probability<0.3 走溯源、同 diagnosisId 发新 validation_triggered）；溯源掌握度加 sampleCount<3 前置校验；4.2 节终止条件补 fallback unknown_error；7.1 节 recommendedStrategies 列明确"本引擎不直接使用"；验收标准改用 09 号字段名；8.3 节事件流补 diagnosis_updated |
| 2.3 | 2026-05-14 | 自检修复：3.3 节表格补"满3轮概率0.5-0.8"状态行（confirmed_with_reservation）+ 策略引擎消费规则补对应条目；4.3 节多轮验证补出口条件（满3轮未达标→confirmed_with_reservation）；4.3 节概率调整公式加 min(0.95) 上限防验证阶段二次突破；第四节流程图补溯源/切换假设分支的 diagnosis_updated 节点 + 图例标注；6.1/6.2 节职责边界修正（诊断引擎输出 recommendedAction 建议，策略引擎执行实际操作）；第九节 Phase 1 实现清单 + 验收清单加 diagnosis_updated 条目与六态全覆盖 |
| 2.4 | 2026-05-14 20:45 | 交叉审计修复（15 项，另有 1 项已修正无需处理）：(1)8.1/8.2 节 09 号协议版本 v2.0.2→v2.0.7；(2)全文「强策略」补跨文档引用 08 §7.1；(3)第九节+验收清单补 Phase 1 溯源范围声明（仅限 G5-G6，1-4 年级图建成后开放完整溯源）；(4)3.1 节 JSON 样例 version 2.0→2.0.3；(5)4.2 节均匀先验 0.5 补 Phase 2 贝叶斯过渡说明；(6)7.3 节验证题库补数据文件名 error_validation_questions.json + 筛选方式；(7)3.3 节补 traced 状态消费规则；(8)6.1/6.2 节 recommendedAction 归属从 diagnosis_updated 修正为 ErrorDiagnosis 记录；(9)4.4 节溯源示例补「真实码以 knowledge.json 为准」注释；(10)2.1 节 answerTimeMs 阈值补 Phase 2 分知识点校准说明；(11)4.1 节「全提示仍错」逻辑从锁定概念问题改为提高概念混淆+前置知识缺失先验；(12)4.2 节「模板」术语补定义（诊断引擎 validation_triggered 推送的解题模板，对应 SP_G_B03）；(13)第五节「邻居节点」补范围定义（一级相邻节点+≥30 条数据阈值）；(14)2.2 节 3σ 例外补冷启动 fallback（年级全局均值替代）；(15)3.1 节 knowledgeCode 已为 M5S1-0 无需修改 |
| 2.4.1 | 2026-05-14 20:52 | 第二轮交叉审计修复：(1)7.2 节 knowledgeCode M5S1-1→M5S1-0；(2)4.3 节 errorVerificationQuestions→error_validation_questions.json |
| 2.4.2 | 2026-05-14 21:26 | 交叉审计修复：7.1 节 error_taxonomy.json 字段名 parentSafeExplanation→parentExplanation（对齐数据文件实际字段名） |

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

这是芽芽助教产品文档集的第 11 号文件，定义四步诊断流程（初筛→匹配→验证→溯源）、六态输出（open/validated/closed/inconclusive/confirmed_with_reservation/traced）、概率调整算法和溯源规则。它回答「学生错在哪里、有多大把握」——消费 answer_submitted 事件，产出 diagnosis_attempted 和 diagnosis_updated 事件。本引擎依赖 06 号（知识图谱做溯源）、07 号（错因分类做匹配）、09 号（事件协议做输入输出）。

## 一、目标

学生做错一道题，诊断引擎回答三个问题：
1. 错在哪里？（定位错因）
2. 有多大把握？（置信度）
3. 怎么验证？（触发验证题）

不强行归因。证据不足时宁可标记 inconclusive，也不贴"粗心"标签。

---

## 二、输入：answer_submitted 事件

诊断引擎消费 `answer_submitted` 事件（完整 Schema 见 09_EVENT_PROTOCOL.md 事件 1）。

### 2.1 必读字段

引擎从事件三层中分别提取：

**answer 层（学生答了什么）**

| 字段 | 用途 |
|------|------|
| studentResponse | 学生的最终答案。用于比对正确答案、提取错误模式 |
| isCorrect | **诊断链启动的开关**。false → 启动；true → 默认跳过（见 2.2 例外） |
| errorOption | 选择题选错时，错误选项本身就是错因线索 |
| steps | 解题步骤（如果能采集到）。step 级的 isCorrect/errorDetail 是诊断的黄金材料 |

**behavior 层（学生怎么答的）**

| 字段 | 用途 |
|------|------|
| answerTimeMs | 过快（< 3 秒）→ 猜测信号；过慢（> 3σ）→ 挣扎信号。Phase 1 使用全局阈值。Phase 2 引入知识点级别作答时间基线后按知识点校准 |
| modifyCount | ≥ 3 次修改 → "蒙对"信号（答对了也要跑诊断） |
| hintUsed | true 且答对 → 提示辅助，未独立掌握。答错但用过提示 → 提示无效 |
| hintLevel | 提示层级，高等级提示后用对 → 掌握度打折 |

**context 层（在什么环境下答的）**

| 字段 | 用途 |
|------|------|
| lessonId | 课堂归属，用于按课堂聚合诊断结果 |
| strategyPack | 当前使用的策略包。如果 strategic_pack 已针对该错因，但学生仍错 → 策略无效信号 |
| stateCard | 状态卡。challenge 模式下错 → 判断是否难度过高 |

### 2.2 诊断链路启动规则

诊断引擎在收到 answer_submitted 事件后，先判断是否启动诊断：

```
isCorrect = false  → 启动（正常流程）
isCorrect = true   → 默认跳过，但以下三个例外强制启动：
  1. answerTimeMs > 该知识点历史均值的 3 倍标准差（异常慢，可能蒙对）。冷启动时该学生在该知识点下无答题记录，以年级全局均值替代。Phase 1 如无年级全局数据，该例外条件暂时不生效
  2. hintUsed = true（答对但借了提示，需确认独立掌握）
  3. modifyCount ≥ 3（反复修改后才对，可能蒙对）
```

以上规则对应 09 号 1.6 节。默认跳过时，chainId 仍然存在，作为"正常作答链"归档，不标记 incomplete。

### 2.3 answer_abandoned 事件

`answer_abandoned` 事件不启动诊断。chainId 标记为 orphan，画像系统单独记录该事件用于参与度评估。同一节课内连续 3 次放弃 → 触发策略引擎的体验保护逻辑。

---

## 三、输出：diagnosis_attempted 事件 + ErrorDiagnosis 记录

诊断完成后同时产出两样东西：
1. 一条 `diagnosis_attempted` 事件（09 号事件 5，实时推送给策略引擎）
2. 一条 `ErrorDiagnosis` 记录（10 号数据模型，持久化存储）

### 3.1 输出格式（对齐 09 号事件 5）

```json
{
  "event": "diagnosis_attempted",
  "version": "2.0.3",
  "chainId": "chain_a1b2c3d4",
  "studentId": "S001",
  "diagnosisId": "diag_20260514_001",
  "sourceQuestionId": "Q_M5S1_DM_045",
  "knowledgeCode": "M5S1-0",
  "lessonId": "L_20260514_001",
  "hypotheses": [
    {
      "hypothesisId": "h1",
      "errorCode": "decimal_point_position_error",
      "probability": 0.62,
      "confidence": 0.74,
      "rank": 1
    },
    {
      "hypothesisId": "h2",
      "errorCode": "calculation_error",
      "probability": 0.28,
      "confidence": 0.45,
      "rank": 2
    }
  ],
  "mainHypothesis": {
    "hypothesisId": "h1",
    "errorCode": "decimal_point_position_error",
    "probability": 0.62,
    "confidence": 0.74
  },
  "status": "open",
  "method": "rule_engine",
  "timestamp": "2026-05-14T10:23:06.500Z"
}
```

### 3.2 字段生成规则

**diagnosisId**：`diag_{YYYYMMDD}_{序号}`，全局唯一。

**hypotheses 数组**：按 probability 降序排列。至少包含 1 个假设，最多 5 个（超出 5 个取 top 5）。每个假设必须同时包含 probability 和 confidence——两者含义不同：
- probability（概率）：这个假设为真的可能性。用贝叶斯更新或规则加权计算。
- confidence（置信度）：诊断引擎对自己判断的把握。取决于证据数量和质量（有多少条行为数据支撑、步骤采集是否完整、历史数据是否充分）。

**mainHypothesis**：hypotheses[0] 的引用。必须同时携带 probability 和 confidence。当 mainHypothesis.confidence < 0.5 时，status 设为 inconclusive。

**status 决策树**：

```
mainHypothesis.confidence < 0.5 → status = "inconclusive"
  不触发验证题。降低难度或分步提示。记录 badcase。

mainHypothesis.confidence ≥ 0.5：
  如果 hypotheses 只有 1 个（其他概率太低被排除）→ status = "open"
  如果 top 2 假设的 probability 差 < 0.15（两个错因都可能）→ 仍为 "open"
  如果该假设已被之前验证确认过 → status = "validated"
  如果该假设被连错 3 道验证题排除 → status = "closed"
```

**method**：当前用 `rule_engine`。Phase 2 引入 `decision_tree`。Phase 3 引入 `ai_assisted`。

### 3.3 验证完成后的状态输出：diagnosis_updated 事件

诊断不是一轮定胜负。每轮验证完成后，诊断引擎发出 `diagnosis_updated` 事件（09 号事件 8），携带更新后的假设集和状态。策略引擎读此事件决定是否介入。

**发出时机**：
- 收到 validation_completed 事件后，重新计算所有假设概率
- 无论概率是否达到阈值，都发出 diagnosis_updated
- 同一 chainId、同一 diagnosisId，不换

**diagnosis_updated 的 status 对照诊断结论**：

| 验证结果 | status | diagnosisStatus | 后续 |
|----------|--------|----------------|------|
| probability ≥ 0.8（验证确认） | validated | confirmed | 停止验证，策略引擎介入 |
| 满 3 轮，probability 在 0.5-0.8 之间 | validated | confirmed_with_reservation | 策略引擎介入，但仅触发轻量策略（基础巩固包），不触发强策略 |
| 连错 3 道（验证排除） | closed | excluded | 切换次高假设或走溯源 |
| 3 轮 inconclusive | inconclusive | inconclusive | 降低难度，记录 badcase |
| 概率未达阈值且未满 3 轮，继续验证 | open | in_progress | 发出新 validation_triggered |

**策略引擎的消费规则**：
- diagnosisStatus = confirmed → 策略引擎根据 mainHypothesis.errorCode 选择策略包，发出 strategy_applied
- diagnosisStatus = confirmed_with_reservation → 策略引擎仅触发轻量策略（基础巩固包），不触发强策略（变式特训包、精准计算包等）
- diagnosisStatus = excluded → 策略引擎等待下一个 diagnosis_updated（诊断引擎正在切换假设）
- diagnosisStatus = traced → 策略引擎不动作，继续等待下一个 diagnosis_updated（诊断引擎正在溯源中）
- diagnosisStatus = in_progress → 策略引擎不动作，继续等待
- diagnosisStatus = inconclusive → 策略引擎触发轻量安全策略（基础巩固包或记忆唤醒包），不触发强策略

> 强策略定义见 08_STRATEGY_PACKS.md §7.1。

---

## 四、诊断流程

```
answer_submitted（isCorrect=false 或三例外）
  ↓
第一步：初筛
  ↓
第二步：匹配 → 输出 diagnosis_attempted（初始假设集）
  ↓
第三步：验证
  ├── 确诊（probability ≥ 0.8）→ 发出 diagnosis_updated（status=validated），停止验证
  ├── 满 3 轮 probability 在 0.5-0.8 → 发出 diagnosis_updated（status=validated, diagnosisStatus=confirmed_with_reservation）
  ├── 排除（连错 3 道）→ 发出 diagnosis_updated（status=closed）→ 判断：
  │     ├── 有次高假设且 probability ≥ 0.3 → 发出 diagnosis_updated（status=open），切换假设继续验证
  │     └── 无可用假设 → 第四步：溯源
  ├── 3 轮 inconclusive → 发出 diagnosis_updated（status=inconclusive），记录 badcase
  └── 概率未达阈值且未满 3 轮 → 发出 diagnosis_updated（status=open），继续下一轮

第四步：溯源
  └── 生成新 diagnosis_attempted → 发出 diagnosis_updated
```

> 图例：诊断引擎在以下节点均发出 diagnosis_updated 事件——每轮验证后（无论确诊/排除/继续/溯源）、最终结论输出前。策略引擎依此决定是否介入。

### 4.1 第一步：初筛

**目标**：判断"是否值得诊断"，排除不值得投入计算资源的情况。

**规则**：

| 输入信号 | 判断 |
|----------|------|
| isCorrect=true 且不满足三例外 | 跳过，chainId 归档 |
| isCorrect=false 但 answerTimeMs < 2 秒 | 疑似"乱点"，降低证据权重 0.5x |
| isCorrect=false 且 hintUsed=true, hintLevel=3 | 全提示仍错 → 提高「概念混淆」和「前置知识缺失」的先验概率，不锁定单一错因 |
| isCorrect=false 且 modifyCount ≥ 5 | 挣扎信号，提高"概念混淆"先验 |
| answer_abandoned | 跳过 |

**初筛后的证据包**：初筛不生成假设，只给后续步骤标注"这条答题记录的证据质量"（高/中/低），影响后续 confidence 计算。

### 4.2 第二步：匹配

**目标**：根据答题信号生成错因假设集。

**匹配的数据源**（按优先级）：

| 优先级 | 数据源 | 说明 |
|--------|--------|------|
| 1 | answer.steps（解题步骤） | 步骤级的 isCorrect/errorDetail 是黄金证据。哪一步开始错 → 缩小错因范围 |
| 2 | answer.errorOption（错误选项） | 选择题的错误选项通常对应特定错因（如选 B 说明混淆了周长和面积） |
| 3 | error_kp_bindings.json | 该知识点绑定了哪些错因。若无绑定 → 回退到该知识点的 questionType → 该题型的 commonErrors |
| 4 | error_taxonomy.json | 候选错因的触发条件/排除条件 |

**匹配算法（规则引擎）**：

```
For each 候选错因（从 error_kp_bindings + 题型错因）:
  检查触发条件是否满足（从 answer.steps / errorOption / behavior 中匹配）
  检查排除条件是否触发（任一排除条件命中 → 该错因概率降为 0.05）
  
  初始概率 = 0.5（均匀先验）。Phase 1 使用均匀先验。Phase 2 引入贝叶斯先验后改用历史错因分布频率
  
  触发条件每命中 1 条 → 概率 × 1.3
  排除条件每命中 1 条 → 概率 × 0.2
  
  如果 answer.steps 中有步骤级错误描述 → 匹配错因定义的关键词
    匹配 → 概率 × 1.5
    无匹配 → 概率 × 0.8
  
  如果有该学生对该错因的历史确诊记录 → 概率 × 1.4（惯性效应）
  如果该错因的历史策略对该学生有效 → 概率 × 0.7（已受过干预，不应反复犯）

  最终概率 = min(rawProbability, 0.95)
  所有乘法操作后取上限 0.95。概率定义域为 [0, 1]，突破 1.0 后归一化会不合理压缩其他假设。
```

**反证优先原则**（来自 07_ERROR_TAXONOMY.md）：

| 规则 | 说明 |
|------|------|
| 列式错误 → 降低"计算失误"概率 | 列式都没对，不能说"只是算错了" |
| 标准题不会 → 不判"迁移失败" | 迁移失败的前提是"标准题能做" |
| 模板后仍不会 → 不判"题型不熟"，改判概念/策略问题 | 看了模板还不会，不是题型的问题。「模板」指诊断引擎在验证阶段通过 validation_triggered 推送的解题模板（对应 08 号 SP_G_B03 的验证动作） |

**生成假设集的终止条件**：
- 所有候选错因都评估完毕
- 已有 1 个假设 probability > 0.8 且第 2 名 < 0.3（明显区分）→ 可提前终止
- 所有候选错因的最终 probability < 0.3 → 生成 fallback 假设（errorCode: "unknown_error", probability: null, confidence: 0），status = "inconclusive"

### 4.3 第三步：验证

**目标**：通过验证题确认或排除主假设。

**触发条件**：仅当 status = "open" 时才触发验证。inconclusive 和 closed 不触发。

**验证链路**（对齐 09 号事件 6 和事件 7）：

```
diagnosis_attempted 发出
  ↓
如果 status = "open" 且 mainHypothesis.confidence ≥ 0.5：
  诊断引擎从 error_taxonomy.json 读取该错因的 validationActions[0]
  选择对应的验证题（从 error_validation_questions.json 题库选取）
  发出 validation_triggered 事件（携带 diagnosisId + hypothesisId + chainId）
  ↓
前端展示验证题，学生作答
  ↓
前端发出 validation_completed 事件（携带同一 chainId）
  ↓
诊断引擎收到 validation_completed，更新假设概率
```

**概率调整公式**：

| validation_completed.result | 操作 | 公式 |
|----------------------------|------|------|
| supported（验证题做对） | 假设概率上升 | probability_new = min(probability_old × 1.15, 0.95) |
| weakened（验证题做错） | 假设概率下降 | probability_new = probability_old × 0.7（不做上限，下降方向不会突破） |
| inconclusive（无法判断） | 概率不变 | probability_new = probability_old |

> 每次乘法后执行 min(probability, 0.95)。概率定义域为 [0, 1]，突破 1.0 后归一化会不合理压缩其他假设。此上限在匹配阶段（4.2 节）和验证阶段（本节）均生效。

**多轮验证规则**：验证不是一轮定胜负。引擎根据每轮 validation_completed 的结果更新概率后，判断是否需要继续验证：

```
每轮验证结束后：
  probability ≥ 0.8 → 确认为主假设，status = "validated"，停止验证
  probability < 0.5 且未满 3 轮 → 继续下一轮验证（同一 chainId、同一 diagnosisId，发出新的 validation_triggered）
  probability 在 0.5-0.8 之间且未满 3 轮 → 继续验证，换一个验证动作（error_taxonomy 的 validationActions 轮转）
  probability 在 0.5-0.8 之间且已满 3 轮 → 有保留地确诊，status = "validated"，diagnosisStatus = "confirmed_with_reservation"，停止验证。策略引擎仅触发轻量策略
  连错 3 道（同一 hypothesisId 连续 3 次 result = "weakened"）→ 确诊为判伪，status = "closed"，切换假设
```

多轮验证全程同一 chainId 和同一 diagnosisId。不重新发出 diagnosis_attempted——诊断假设没变，只是在验证它。

**连错确诊规则**：
同一 hypothesisId 连续 3 次 result = "weakened" → 确诊为判伪（confirmed），该假设被排除。status 变为 "closed"。诊断引擎切换至 hypotheses[1]（第二假设）。

**切换次高假设的规则**：
- 沿用同一 diagnosisId，发出新的 validation_triggered（validationRound 重置为 1）
- 发出 diagnosis_updated（status=open, diagnosisStatus=in_progress）
- 如果 hypotheses[1].probability < 0.3 → 不触发验证，直接走溯源（第四步）
- 如果 hypotheses 只剩 1 个且被 closed → 直接走溯源

**3 轮 inconclusive 规则**：
同一 hypothesisId 验证 3 轮仍全部 result = "inconclusive" → 标记 badcase。降低该知识点难度，不继续验证。记录到 GrowthMemory。

**inconclusive vs weakened 的区别**：
- weakened = 判断了，但学生做错了（假设可能不成立）
- inconclusive = 系统没法判断（验证题设计可能有问题，或学生行为数据不足）

### 4.4 第四步：溯源

**目标**：如果所有候选错因都被排除（status=closed），沿知识图谱向上追溯前置知识。

**触发条件**：
- 主假设被连错 3 道排除后，无其他候选（hypotheses 只剩 1 个且被 closed）
- 或初始生成时所有候选的 confidence 都 < 0.5（status=inconclusive）

**追溯规则**：

```
从当前 knowledgeCode 出发：
  读取 knowledge_graph 中该节点的 prerequisites[]（前置知识列表）
  
  对每个前置知识：
    查该学生对前置知识的掌握度和答题样本数
    如果 sampleCount < 3（冷启动定义：该节点无可靠数据）→ 不使用掌握度，直接推送 1 道前置知识验证题
    如果 sampleCount ≥ 3 且掌握度 < 0.6 → 生成以"前置知识缺失"为主假设的新诊断
    如果 sampleCount ≥ 3 且掌握度 ≥ 0.6 → 跳过
  
  如果前置知识也无问题 → 继续向上追溯（最多 3 层）
  
  3 层追溯仍无结论 → status = "inconclusive"，记录 badcase
```

**追溯深度限制**：最多 3 层。超过 3 层自动终止。

**示例**：
答错"分数除法应用题" → 主假设全部排除 → 追溯前置"分数除法计算" → 掌握度 0.3 → 主假设改为"分数除法计算不熟练" → 触发验证。（示例，真实知识点码以 knowledge.json 为准）

---

## 五、冷启动规则

新学生没有历史数据时，诊断引擎面临"证据不足"的冷启动问题。

**冷启动数据阈值**（非日历时间）：

| 条件 | 行为 |
|------|------|
| 该知识点下学生答题 < 30 条 | 置信度自动打折 × 0.7。禁止触发强策略（强策略定义见 08_STRATEGY_PACKS.md §7.1） |
| 该知识点全局答题 < 120 条 | 该知识点的 error_kp_bindings 权重降低，多依赖 L1 通用错因 |
| 学生画像中该知识点的邻居节点（前置/后续）数据充足 | 借用邻居的错因分布作为先验。「邻居节点」= 与当前节点有 prerequisites 或 next 关系的一级相邻节点。「数据充足」= 该邻居节点下学生答题 ≥ 30 条 |

**冷启动标识**：diagnosis_attempted 的 method 仍为 `rule_engine`，但 hypotheses 中冷启动生成的假设 probability 前加标记：该假设的 confidence 按 5.1 节规则自动打折 ×0.7，策略引擎和画像系统据此识别冷启动状态。

---

## 六、关键边界规则

### 6.1 低置信度防线

```
mainHypothesis.confidence < 0.5 → 不触发验证题
  诊断引擎在 ErrorDiagnosis 记录中设置：
  1. recommendedAction = "reduce_difficulty"（建议降低难度）
  2. recommendedAction = "provide_scaffolding"（建议分步提示，hintLevel=1）
  3. 记录 inconclusive badcase
  策略引擎（12 号文档）消费 ErrorDiagnosis.recommendedAction 字段执行实际操作（降低难度、推送提示）。诊断引擎不负责出题，不直接操作题目难度。
```

低置信度错因绝不能触发强策略（如变式特训包、精准计算包）。只能触发轻量安全策略（基础巩固包或记忆唤醒包）。强策略定义见 08_STRATEGY_PACKS.md §7.1。

### 6.2 无法判断时

以下情况标记 inconclusive，不强归因：
- 所有候选假设的 confidence < 0.5
- answer.steps 为空且无 errorOption（证据太少）
- 触发了反证规则（如列式错误 → 不能判计算失误，但其他假设也不成立）

inconclusive 的后续动作（诊断引擎在 ErrorDiagnosis 记录中发出建议，策略引擎执行）：
1. 诊断引擎在 ErrorDiagnosis 中设置 recommendedAction = "provide_scaffolding"
2. 诊断引擎设置 recommendedAction = "reduce_difficulty"
3. badcase 入池
4. 24 小时内该知识点再有错误 → 重新诊断，此时有更多证据

### 6.3 家长摘要输出

诊断引擎不直接生成家长摘要，但为家长摘要提供数据原料（13_PARENT_SUMMARY_RULES.md）。

**parentSummary 字段**（写入 ErrorDiagnosis 表，供摘要引擎读取）：

| 字段 | 内容 | 用途 |
|------|------|------|
| parentSummary.short | 1 句话，如"今天孩子在找小数点的位置时有些犹豫" | 摘要卡片 |
| parentSummary.full | 包含学习现象 + 芽芽做了什么 + 下一步建议 | 详情页 |
| teacherNote | 内部记录：该诊断涉及的知识点、错因、验证结果、策略建议 | 教学分析 |

**parentSummary 生成规则**：
- 使用 error_taxonomy.json 中该错因的 parentExplanation 作为母版
- 用 answer_submitted 的具体信息填充（哪道题、答了什么、花了多少时间）
- 严格遵守 13 号文档的禁止词和推荐表达方式

---

## 七、所需数据底座

诊断引擎运行前，以下数据必须就绪：

### 7.1 error_taxonomy.json（错因体系）

86 个错因的完整定义，每个错因必须含：

| 字段 | 说明 | 引擎使用方式 |
|------|------|-------------|
| errorCode | 错因编码 | 写入 diagnosis_attempted.errorCode |
| level | L1/L2/L3 | L1 通用优先用于冷启动 |
| name | 中文名称 | 调试日志 |
| definition | 错因定义 | 匹配答案模式的关键词 |
| triggerConditions | 触发条件（数组） | 匹配阶段：命中条件概率上升 |
| exclusionConditions | 排除条件（数组） | 匹配阶段：命中任一排除则概率×0.2 |
| validationActions | 验证动作（数组） | 验证阶段：选择验证题类型 |
| neighborErrors | 相邻错因（数组） | 假设集生成时区分相似错因 |
| recommendedStrategies | 推荐策略包（数组） | 本引擎不直接使用，供策略引擎（12 号文档）读取 |
| parentExplanation | 家长中性解释 | parentSummary.short 母版 |

### 7.2 error_kp_bindings.json（知识点-错因绑定）

每个 A 级知识点绑定 ≥ 3 个错因（来自 06 号图谱规范）。条目格式：

```json
{
  "knowledgeCode": "M5S1-0",
  "errorCodes": [
    "decimal_point_position_error",
    "calculation_error",
    "concept_confusion"
  ]
}
```

引擎使用方式：收到 answer_submitted 后，用 knowledgeCode 查此文件，得到候选错因列表，再逐个匹配触发/排除条件。

如无绑定 → 回退到 knowledge_graph 节点自身的 commonErrors 字段 → 如仍为空 → 使用 L1 通用错因作为兜底。

### 7.3 errorVerificationQuestions（错因验证题库）

每个错因配置 ≥ 2 道验证题。验证题的设计要求：
- 专门探测该错因（不考其他知识）
- 题干简洁，学生在 30 秒内可作答
- 答对说明"没有这个错因"，答错说明"很可能有这个错因"

引擎使用方式：validation_triggered 事件中携带 validationQuestionId，从题库系统 question 表按 validationAction 筛选抽取。数据文件：error_validation_questions.json（待建设）。

### 7.4 knowledge_graph 节点中的 commonErrors 和 prerequisites

来自 primary_math_g5_g6_knowledge.json。

- commonErrors：该知识点自身的常见错因（回退方案）
- prerequisites：溯源时沿此链路向上追溯

---

## 八、与相关文档的接口约定

### 8.1 输入依赖

| 文档 | 依赖内容 |
|------|----------|
| 09_EVENT_PROTOCOL.md (v2.0.7) | answer_submitted 事件格式（含三层结构、chainId、三例外规则）；diagnosis_updated 事件 Schema（事件 8） |
| 06_KNOWLEDGE_GRAPH.md | KnowledgeNode 节点的 commonErrors、questionTypes、prerequisites |
| 07_ERROR_TAXONOMY.md | 三层错因体系、反证优先原则、每类错因的 8 项必须配置 |
| 10_DATA_MODEL.md | ErrorDiagnosis 表结构 |

### 8.2 输出消费

| 文档 | 输出内容 |
|------|----------|
| 09_EVENT_PROTOCOL.md (v2.0.7) | diagnosis_attempted 事件（事件 5）、validation_triggered 事件（事件 6）、diagnosis_updated 事件（事件 8） |
| 12_STRATEGY_ENGINE.md | 策略引擎取 diagnosis_updated 的 mainHypothesis.errorCode 选择策略包 |
| 13_PARENT_SUMMARY_RULES.md | 家长摘要引擎取诊断结果生成 parentSummary |

### 8.3 事件流全景

```
前端发出 answer_submitted（chainId 生成）
  ↓
诊断引擎消费 answer_submitted
  ↓
诊断引擎发出 diagnosis_attempted（同一 chainId）
  ↓
若 status = "open" → 诊断引擎发出 validation_triggered（同一 chainId）
  ↓
前端展示验证题，学生作答
  ↓
前端发出 validation_completed（同一 chainId）
  ↓
诊断引擎消费 validation_completed，更新概率
  ↓
诊断引擎发出 diagnosis_updated（同一 chainId，每轮验证后都发）
  ↓
如果 diagnosis_updated.status = "validated" → 策略引擎消费，发出 strategy_applied
  ↓
策略执行完毕后，前端发出 strategy_completed
```

---

## 九、初期实现方式

优先级排序：

**Phase 1（当前阶段）**：
- 规则引擎。用 error_kp_bindings + error_taxonomy 的触发/排除条件做确定性匹配
- 概率计算用加权乘法（见 4.2 公式）
- 验证链路搭通：diagnosis_attempted → validation_triggered → validation_completed
- diagnosis_updated 事件在每轮验证后发出，携带更新后的 hypotheses 和 diagnosisStatus（六态：confirmed / confirmed_with_reservation / excluded / inconclusive / in_progress / traced）
- 策略引擎消费 diagnosis_updated（status=validated 时介入），不消费 diagnosis_attempted
- 答对三例外、放弃跳过、冷启动阈值全部生效
- 溯源功能：Phase 1 溯源仅限 G5-G6 图覆盖范围，最深追至 5 年级起始节点。1-4 年级图建成后开放完整溯源（最多 3 层）

**Phase 2**：
- 决策树替代加权乘法。用 error_taxonomy 的 neighborErrors 构建区分树
- 引入历史诊断结果作为贝叶斯先验
- lesson_paused / lesson_resumed / idle_timeout 接入后修正 answerTimeMs 的解读

**Phase 3+**：
- AI 辅助解释：对 rule_engine 无法判断的案例（inconclusive），调用 LLM 阅读 answer.steps 的完整步骤文本，给出错因推断
- AI 辅助的结果标记 method = "ai_assisted"，不直接作为主假设，仅修正 probability ± 0.1

---

## 十、验收标准

Phase 1 验收清单：

- [ ] 收到 answer_submitted（isCorrect=false）→ 1 秒内发出 diagnosis_attempted
- [ ] diagnosis_attempted 的 hypotheses 至少含 1 个候选，最多 5 个
- [ ] mainHypothesis 同时含 probability 和 confidence
- [ ] confidence < 0.5 时 status = "inconclusive"，不触发验证题
- [ ] validation_completed.result = 'supported' → 概率 × 1.15，result = 'weakened' → 概率 × 0.7
- [ ] 连错 3 道验证题 → status = "closed"，切换假设
- [ ] 溯源最多 3 层，沿 prerequisites 向上（Phase 1 前提：1-4 年级图谱建成后开放完整溯源）
- [ ] 答对三例外（answerTimeMs 异常 / hintUsed / modifyCount≥3）全部触发诊断
- [ ] answer_abandoned 不触发诊断
- [ ] chainId 从 answer_submitted 到 strategy_completed 全程一致
- [ ] 冷启动时（该知识点答题 < 30 条），confidence 打折，不强策略（强策略定义见 08 §7.1）
- [ ] 每轮验证后均发出 diagnosis_updated，携带最新 hypotheses 和 diagnosisStatus
- [ ] diagnosisStatus 六态全覆盖（confirmed / confirmed_with_reservation / excluded / inconclusive / in_progress / traced）
- [ ] 策略引擎仅在 diagnosis_updated.status = "validated" 时介入
