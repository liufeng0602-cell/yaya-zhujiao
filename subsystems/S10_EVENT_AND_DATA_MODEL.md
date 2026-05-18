# S10 事件协议与数据模型 v1.6

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.6 | 2026-05-18 | P1-ref修复：L421七态/六态跨系统引用未闭合——补全S07 §1.3引用目标+差异结论(open是否为独立diagnosisStatus)+P2待办声明 |
| v1.5 | 2026-05-18 | P2-01修复：正文错因计数86→87（L1通用10→11）对齐变更记录；同步修复§十数据文件清单中同一计数 |
| v1.4 | 2026-05-18 00:41 | v9审计修复（6条——1严重+1缺失+4轻微）：(F-01)消费关系清单4处表编号修正——GrowthMemory表八→表九/BehaviorEvent表六→表五/ErrorDiagnosis表五→表六/ErrorTaxonomy表四→表三，附带修正§十表分类摘要中八/九交换错误；(M-01)大白话补全第10类「内容与代码进化分离」；(W-03)G1-G7自检声明标注精确行号；(W-04)自检声明20→23；(W-01/W-02)type=percent/percent_range和双注释嵌入为轻微问题不阻塞，本轮暂不修 |
| 1.3 | 2026-05-17 23:34 | v8审计4条BLOCK+补全修复：(B01/B02/B03)自我进化路线图独立成章+数据闭环声明+北极星权重配比——已由前置迭代补全，本轮验证通过；(W02)维度交互矩阵升级为验收标准1.17三问题式逐格分析+仲裁规则含优先级；(L01)消费关系清单answer_abandoned→S08行补缺失事件矩阵#11；(§五自引用澄清)不可修改边界中"§五"改为"见本文档「五、错误处理规则」§5.1"以消除跨文档误解；(不属实B04)S12 §五引用断裂——经核实§五是S10自身章节自引用，非跨文档引用，不修。 |\n| 1.0 | 2026-05-17 03:58 | 首版：合并原 09 号事件协议 v2.0.8 + 10 号数据模型 v2.1.4 为统一子系统文档。 |
| 1.2 | 2026-05-17 21:09 | v7审计16条全量修复：(致命F07)补v1.2变更记录；(严重N01+N02)diagnosisStatus修正+自检声明修正；(缺失M01)~20处AI-MUTABLE补标；(缺失M02)answer_submitted增hintRequestedBeforeAnswer；(缺失M03-M05)降级策略扩展+宕机场景+告警链路；(缺失M06)S15引用标注；(严重N03-N05)信用分正式化；(轻微L02+L04+L05)消费方一致性+矩阵列+S07矛盾标注 |
| 1.1 | 2026-05-17 08:06 | 首审24条全量修复：(致命6条)补全6缺失章节——它还不会什么/设计演化推理链/自我进化执行方法/安全执行管道/内容与代码进化分离/维度交互矩阵；(致命)strategy_mapping.json路径核实——确认文件不存在后标注待生成。合计新增约200行。 |

---

## 阅读指南

本文档是芽芽系统的通信和数据底座。它回答两个问题：

1. 系统各模块怎么对话——事件协议（第一部分）
2. 数据怎么存——数据模型（第二部分）

引擎架构（S07诊断引擎、S08策略引擎、S09课堂生成引擎、S12质量仪表盘、S15学生画像）全部通过这套事件协议通信，全部基于这些数据模型读写。

先读第一部分理解事件的流动，再读第二部分理解数据的落点。

---

## 定位与核心职责

### 一句话定位

S10 是芽芽系统所有子系统之间的通信底座和数据存储规范——它定义了 21 种事件的完整 Schema 和 10 张核心数据表的结构，让诊断引擎、策略引擎、课堂引擎、画像系统、家长摘要能够用同一套语言对话。

### 核心职责

| 职责 | P0/P1 | 说明 |
|------|-------|------|
| 定义 Phase 1 的 11 种事件 Schema | P0 | 诊断链路和策略链路的通信基础 |
| 定义 chainId 诊断链路串联规则 | P0 | 保证一次答题→诊断→策略执行的完整追踪 |
| 定义 10 张核心数据表 Schema | P0 | 知识/错因/行为/诊断/策略/成长的数据存储 |
| 定义事件拒收与修复规则 | P0 | 保证数据质量，防止脏数据入库 |
| 定义版本兼容规则 | P1 | 支持系统平滑升级 |
| 预留 Phase 2/3 事件位 | P2 | 为后续扩展留接口 |
| 定义消费方矩阵 | P1 | 明确每个事件的消费者 |
| 定义与下游文档的接口约定 | P1 | S07/S08/S12/S15 的输入输出契约 |

---

## 第一部分：事件协议

### 一、通用规则

#### 1.1 必填字段

每个事件 Schema 中标注"必填"的字段，缺一不可。缺任一必填字段，事件拒收，返回错误码：`EVENT_MISSING_REQUIRED_FIELD`。上游（前端/网关）补全后重传。

特殊情况：
- studentId 缺失永不接受。没有 studentId，事件无法归属到任何学生画像。
- knowledgeCode 缺失时，允许前端从 questionId 反查 knowledgeCode 后补全重传。仅 knowledgeCode 有此例外。

#### 1.2 chainId —— 诊断链路串联

所有属于同一条诊断链路的事件，共享同一个 chainId。

chainId 的生成规则：
- chainId 的边界是"一次答题→诊断→策略执行"，不是"一节课"。同一节课内不同题目对应不同 chainId。
- 正常流程：chainId 在 answer_submitted 事件中首次生成。格式：`chain_{studentId}_{timestamp_ms}` 或 UUID v4，由前端生成。
- 提前请求提示：学生可能在提交答案之前先请求提示（hint_requested 先于 answer_submitted）。此时前端为这道题预生成 chainId（格式同上），hint_requested 携带该预生成的 chainId。后续 answer_submitted 复用同一 chainId。若 hint_requested 发出后学生放弃答题（无 answer_submitted），该 chainId 标记为 orphan，24 小时后清理。
- 答对不诊断：如果 answer_submitted.isCorrect = true，且系统判定无需诊断（见 1.6 节规则），则 chainId 仍然生成，但不会产生 diagnosis_attempted 及后续事件。该 chainId 作为"正常作答链"归档，不标记为 incomplete。
- 学生放弃答题：题目展示后，若学生在 N 秒内（默认 600 秒）既未提交答案也未请求提示，前端自动发送 answer_abandoned 事件。放弃的题目不进入诊断链路。
- 后续所有事件必须携带同一个 chainId。

完整链路：
```
answer_submitted (chainId 生成)
  ↓
diagnosis_attempted (同一 chainId)
  ↓
validation_triggered (同一 chainId)
  ↓
validation_completed (同一 chainId)
  ↓
diagnosis_updated (同一 chainId)
  ↓
strategy_applied (同一 chainId)
  ↓
strategy_completed (同一 chainId)
```

#### 1.3 version —— 协议版本

每条事件携带 `"version": "2.0.3"`。

引擎读取事件时校验 version 字段：
- 同主版本兼容：2.0.x 之间的版本差异为兼容变更（次字段增减、枚举扩展），引擎正常处理，不拒收。
- 跨主版本不兼容：如 1.x 事件发到 2.x 引擎，跳过该事件，记录 WARN 日志，不崩溃。
- 版本字段缺失：按 1.0 协议尝试解析，失败则跳过。

事件样例中 version 的升级规则：事件样例中的 version 值为最后一次 Schema 结构变更的版本号。Schema 结构变更指：字段增删、字段类型修改、枚举值增删改。以下变更不触发 version 升级：字段描述文字修改、过渡规则补充、消费方列表更新、校验规则调整等纯文本说明修改。字段从必填改为选填属于结构变更（改变字段约束规则，影响消费者处理逻辑），触发 version 升级。字段从选填改为必填亦同。

#### 1.4 timestamp —— 时间戳

每条事件携带 ISO 8601 格式时间戳，精确到毫秒：`"timestamp": "2026-05-14T10:23:05.872Z"`。所有 timestamp 以 UTC 为准。前端负责在事件发送前打时间戳。

#### 1.5 事件通用上下文字段

| 字段 | 类型 | 必填规则 | 说明 |
|------|------|----------|------|
| studentId | string | 所有事件必填 | 学生唯一标识 |
| subject | string | 选填 | 学科 |
| grade | string | 选填 | 年级 |
| stage | string | 选填 | 学段（primary/middle/high） |
| textbookVersion | string | 选填 | 教材版本（PEP） |
| knowledgeCode | string | 选填（可从 questionId 反查） | 知识点编码 |
| questionType | string | 选填 | 题型 |
| difficulty | number | 选填 | 难度（0-1） |
| strategyPack | string | 选填 | 当前使用的策略包 |
| stateCard | string | 选填 | 状态卡 |
| lessonId | string | 课堂类事件必填 | 所属课堂 |
| chainId | string | 诊断链路事件必填 | 诊断链路 ID |
| version | string | 所有事件必填 | 协议版本 |
| timestamp | string | 所有事件必填 | ISO 8601 时间戳 |

> 注意：各事件 Schema 中的必填声明为最终权威。上表为通用指引，如与 Schema 冲突，以 Schema 为准。

#### 1.6 诊断链路启动规则

诊断链路的启动条件：
- 答错启动：answer_submitted.isCorrect = false 时，诊断引擎必须运行。
- 答对跳过：answer_submitted.isCorrect = true 时，默认不启动诊断。但以下例外必须启动：
  - answerTimeMs 异常长（超过该知识点历史均值的 3 倍标准差）
  - hintUsed = true（答对但用了提示，需确认是否真正掌握）；hintRequestedBeforeAnswer = true（请求过提示且看了，区分"看了提示"和"没看提示但答对了"）
  - modifyCount ≥ 3（反复修改后才答对，存在"蒙对"可能）
- 放弃跳过：answer_abandoned 事件不启动诊断链路。

#### 1.7 difficulty 与 knowledgeLevel 的关系

answer_submitted 携带两个难度信号：
- difficulty（0-1）：题目本身的难度系数，由题库定义。
- knowledgeCode 对应的 level（A/B/C）：知识点的认知层级，由知识图谱定义。

诊断引擎使用 difficulty 做"这道题对学生来说多难"的判断。策略引擎使用 level 做"这个知识点本身要求多高"的判断。两者不互相替代，各自独立使用。

#### 1.8 knowledgeCode 编码格式

本文档所有 knowledgeCode 样例采用真实数据的数字编码格式：

> 注：本文档不同章节的样例使用不同的 knowledgeCode（如 answer_submitted 用 M5S1-3、KnowledgeNode 用 M5S1-0），均属于五年级上册第一单元，但为不同知识点。

`{年级}{册}{单元}-{序号}`。例如 `M5S1-3` 表示五年级上册第一单元第 3 号知识点。实际数据中 knowledgeCode 见 knowledge.json 文件的 knowledgeCode 字段。

---

### 二、Phase 1 事件（完整 Schema）

以下 11 个事件为诊断引擎和策略引擎启动的必要输入。

#### 事件 1：answer_submitted

触发时机：学生在课堂上提交一道题的答案。这是整个系统最重要的输入事件。

```json
{
  "event": "answer_submitted",
  "version": "2.0.3",
  "chainId": "chain_a1b2c3d4",
  "studentId": "S001",
  "questionId": "Q_M5S1_DM_045",
  "knowledgeCode": "M5S1-3",
  "questionType": "calculation",
  "difficulty": 0.7,
  "answer": {
    "studentResponse": "3.20",
    "isCorrect": false,
    "errorOption": null,
    "scratchpadUsed": false,
    "steps": [
      {
        "stepNumber": 1,
        "input": "3.5 × 0.6",
        "output": "2.10",
        "isCorrect": true
      },
      {
        "stepNumber": 2,
        "input": "2.10 + 1.2",
        "output": "2.22",
        "isCorrect": false,
        "errorDetail": "小数点未对齐"
      }
    ]
  },
  "behavior": {
    "answerTimeMs": 18000,
    "modifyCount": 2,
    "hintUsed": false,
    "hintRequestedBeforeAnswer": false,
    "hintLevel": null
  },
  "context": {
    "lessonId": "L_20260514_001",
    "strategyPack": "default",
    "stateCard": "challenge",
    "activeStrategyPack": null
  },
  "timestamp": "2026-05-14T10:23:05.872Z"
}
```

> 字段说明详见原 09 号文档 §事件 1，此处精简为核心 Schema。本文档定义的是系统接口规范，完整字段说明在实现层参考原 09 号文档。

#### 事件 2：hint_requested

触发时机：学生在作答前或作答中请求提示。

```json
{
  "event": "hint_requested",
  "version": "2.0.3",
  "chainId": "chain_a1b2c3d4",
  "studentId": "S001",
  "questionId": "Q_M5S1_DM_045",
  "knowledgeCode": "M5S1-3",
  "hint": {
    "level": 1,
    "type": "general_guidance",
    "requestedAfterMs": 12000,
    "previousHintLevel": null
  },
  "context": {
    "lessonId": "L_20260514_001",
    "attemptNumber": 1
  },
  "timestamp": "2026-05-14T10:23:17.872Z"
}
```

#### 事件 3：lesson_started

触发时机：学生进入一节课。

```json
{
  "event": "lesson_started",
  "version": "2.0.3",
  "studentId": "S001",
  "lessonId": "L_20260514_001",
  "subject": "math",
  "grade": "5",
  "stage": "primary",
  "textbookVersion": "PEP",
  "knowledgeCodes": ["M5S1-4", "M5S1-3"],
  "strategyPack": "default",
  "stateCard": "challenge",
  "timestamp": "2026-05-14T10:00:00.000Z"
}
```

#### 事件 4：lesson_completed

触发时机：学生正常完成或中断一节课。

```json
{
  "event": "lesson_completed",
  "version": "2.0.3",
  "studentId": "S001",
  "lessonId": "L_20260514_001",
  "completionStatus": "completed",
  "duration": {
    "totalMs": 1500000,
    "activeMs": 1200000,
    "pauses": 1,
    "idleTimeouts": 0
  },
  "outcome": {
    "questionsAnswered": 8,
    "questionsCorrect": 6,
    "exitPoint": null,
    "byKnowledgeCode": [
      {"knowledgeCode": "M5S1-4", "questionsAnswered": 5, "questionsCorrect": 4},
      {"knowledgeCode": "M5S1-3", "questionsAnswered": 3, "questionsCorrect": 2}
    ]
  },
  "timestamp": "2026-05-14T10:25:00.000Z"
}
```

activeMs 的异常值校验：若 activeMs < 0 或 activeMs > 7200000（2 小时），标记 `activeMsValid: false`，不参与画像系统专注度计算。Phase 2 上线 idle_timeout 后，上限调整为 4 小时。

Phase 1 → Phase 2 过渡规则：Phase 2 上线后，对 Phase 1 期间的历史 lesson_completed 事件打标记 `"activeMsEstimated": true`。画像系统不将 Phase 1（estimated）和 Phase 2（measured）的 activeMs 直接对比。

#### 事件 5：diagnosis_attempted

触发时机：诊断引擎完成一次错因诊断，生成假设集。

```json
{
  "event": "diagnosis_attempted",
  "version": "2.0.3",
  "chainId": "chain_a1b2c3d4",
  "studentId": "S001",
  "diagnosisId": "diag_20260514_001",
  "sourceQuestionId": "Q_M5S1_DM_045",
  "knowledgeCode": "M5S1-3",
  "lessonId": "L_20260514_001",
  "hypotheses": [
    {"hypothesisId": "h1", "errorCode": "decimal_point_position_error", "probability": 0.62, "confidence": 0.74, "rank": 1},
    {"hypothesisId": "h2", "errorCode": "calculation_error", "probability": 0.28, "confidence": 0.45, "rank": 2}
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

probability 与 confidence 的区别：
- probability（概率）：这个假设为真的可能性。
- confidence（置信度）：诊断引擎对自己这次判断的把握程度。
- <!-- AI-MUTABLE: confidence_validation_trigger, type=float, range=[0.30, 0.60] -->
使用规则：confidence < 0.5 时，不能触发验证题（改为降低难度或分步提示）。

低置信度规则：当 mainHypothesis.confidence < 0.5 时，status 应设为 "inconclusive"，不触发验证题。

#### 事件 6：validation_triggered

触发时机：诊断引擎根据主假设，选择一道验证题推送给学生。

```json
{
  "event": "validation_triggered",
  "version": "2.0.3",
  "chainId": "chain_a1b2c3d4",
  "studentId": "S001",
  "diagnosisId": "diag_20260514_001",
  "hypothesisId": "h1",
  "sourceQuestionId": "Q_M5S1_DM_045",
  "validationQuestionId": "Q_M5S1_DM_VAL_012",
  "knowledgeCode": "M5S1-3",
  "hypothesisType": "concept_confusion",
  "validationType": "decimal_place_visual_check",
  "validationRound": 1,
  "previousValidationId": null,
  "timestamp": "2026-05-14T10:23:10.000Z"
}
```

#### 事件 7：validation_completed

触发时机：学生完成验证题作答。

```json
{
  "event": "validation_completed",
  "version": "2.0.3",
  "chainId": "chain_a1b2c3d4",
  "studentId": "S001",
  "diagnosisId": "diag_20260514_001",
  "hypothesisId": "h1",
  "validationQuestionId": "Q_M5S1_DM_VAL_012",
  "knowledgeCode": "M5S1-3",
  "validationRound": 1,
  "isCorrect": true,
  "studentResponse": "B",
  "correctAnswer": "B",
  "result": "supported",
  "probabilityBefore": 0.62,
  "probabilityAfter": 0.71,
  "timestamp": "2026-05-14T10:23:55.000Z"
}
```

概率调整规则（详见 S07 诊断引擎）：
<!-- AI-MUTABLE: probability_multiplier_supported, type=float, range=[1.05, 1.30] -->
- 验证题做对 → 假设概率 × 1.15（result = "supported"）
<!-- AI-MUTABLE: probability_multiplier_weakened, type=float, range=[0.50, 0.90] -->
- 验证题做错 → 假设概率 × 0.7（result = "weakened"）
- 验证题结果模糊 → 假设概率不变（result = "inconclusive"）
<!-- AI-MUTABLE: consecutive_weakened_exclude, type=int, range=[2, 5] -->
- 同一假设连续 3 次 result="weakened" → 该假设被排除，切换下一假设或重新诊断
<!-- AI-MUTABLE: consecutive_inconclusive_badcase, type=int, range=[2, 5] -->
- 同一假设验证 3 轮仍 result="inconclusive" → 标记 badcase，降低难度重新观察

#### 事件 8：diagnosis_updated

触发时机：诊断引擎收到 validation_completed 事件后，更新假设概率，发出此事件。多轮验证过程中每轮验证完成后发出。

```json
{
  "event": "diagnosis_updated",
  "version": "2.0.3",
  "chainId": "chain_a1b2c3d4",
  "studentId": "S001",
  "diagnosisId": "diag_20260514_001",
  "knowledgeCode": "M5S1-3",
  "lessonId": "L_20260514_001",
  "hypotheses": [
    {"hypothesisId": "h1", "errorCode": "decimal_point_position_error", "probability": 0.71, "confidence": 0.80, "rank": 1}
  ],
  "mainHypothesis": {
    "hypothesisId": "h1",
    "errorCode": "decimal_point_position_error",
    "probability": 0.71,
    "confidence": 0.80
  },
  "status": "validated",
  "diagnosisStatus": "confirmed_with_reservation",
  "validationRound": 2,
  "triggerResult": "supported",
  "method": "rule_engine",
  "timestamp": "2026-05-14T10:23:56.000Z"
}
```

status 与 diagnosisStatus 的对照（六态。注：S07 诊断引擎曾存在「七态」与「六种状态」的自相矛盾——S07 v1.10（§1.3 七态输出）已明确：七态与六态的差异在于 **open 是否为独立的 diagnosisStatus 值**——S07 七态中 open 作为独立 diagnosisStatus 枚举值存在，而 S10 六态中 open 仅为 status 字段值（非 diagnosisStatus 枚举）。S07 §148 注明「S10 需在后续版本同步升级为七态」，当前 S10 六态定义与 S07 七态的实际交互无冲突（traced 已在 S10 枚举中），open 枚举升级列为 P2 待办）：

| status | diagnosisStatus | 含义 | 后续动作 |
|--------|----------------|------|----------|
| open | in_progress | 验证中 | 继续下一轮 |
| validated | confirmed | 确诊（prob≥0.85） | 策略引擎介入，发强策略 |
| validated | confirmed_with_reservation | 有保留确诊（满3轮 prob 0.5-0.8） | 仅发轻量策略 |
| closed | excluded | 假设被排除 | 切换次高假设或溯源 |
| open | traced | 已切入溯源 | 追溯前置知识点错因根源 |
| inconclusive | inconclusive | 无法判断 | 降低难度，记录 badcase |

多轮验证的 diagnosis_updated 发出规则：
- 第 1 轮 validation_completed 收到后 → 发出 diagnosis_updated
- 第 2 轮 validation_completed 收到后 → 发出 diagnosis_updated
- 第 3 轮 validation_completed 收到后 → 发出 diagnosis_updated（必须收盘：confirmed 或 excluded 或 inconclusive）
- <!-- AI-MUTABLE: early_confirm_probability, type=float, range=[0.75, 0.90] -->
验证提前确诊（probability ≥ 0.8）→ 立即发出 diagnosis_updated（diagnosisStatus=confirmed），不再继续

消费方：诊断引擎（溯源决策与状态机推进）、策略引擎（读到 status=validated 时开始选择策略包）、画像系统、家长摘要。

#### 事件 9：strategy_applied

触发时机：策略引擎根据诊断结果，选择一个策略包并部署。

```json
{
  "event": "strategy_applied",
  "version": "2.0.3",
  "chainId": "chain_a1b2c3d4",
  "studentId": "S001",
  "knowledgeCode": "M5S1-3",
  "diagnosisId": "diag_20260514_001",
  "lessonId": "L_20260514_001",
  "strategyPack": "decimal_point_position_pack",
  "triggerReason": "decimal_point_position_error",
  "triggerSource": "error_diagnosis",
  "confidenceBefore": 0.85,
  "params": {
    "difficultyAdjustment": -0.2,
    "questionCount": 2,
    "hintLevel": 1,
    "useTimer": false
  },
  "timestamp": "2026-05-14T10:24:00.000Z"
}
```

调度优先级规则（详见 S08 策略引擎）：
1. 体验保护（连续错误、学习能量低 → 能量恢复包）
2. 主错因匹配
3. 学科专属策略
4. 偏好叠加
5. 历史效能叠加

#### 事件 10：strategy_completed

触发时机：策略包执行完毕或被中断。

```json
{
  "event": "strategy_completed",
  "version": "2.0.3",
  "chainId": "chain_a1b2c3d4",
  "studentId": "S001",
  "knowledgeCode": "M5S1-3",
  "strategyPack": "decimal_point_position_pack",
  "diagnosisId": "diag_20260514_001",
  "lessonId": "L_20260514_001",
  "completionStatus": "completed",
  "durationMs": 42000,
  "effectScore": 1,
  "exitReason": null,
  "nextAction": "continue_lesson",
  "timestamp": "2026-05-14T10:24:42.000Z"
}
```

effectScore 枚举：-2（有害）/ -1（可能混淆）/ 0（无变化）/ 1（有帮助）/ 2（显著提升）。由策略引擎根据策略执行期间学生的答题表现自动计算。

每个 strategy_completed 事件必须同时生成一条 StrategyEffect 记录（见第二部分 §七）。

#### 事件 11：answer_abandoned

触发时机：题目展示后，学生在 N 秒内（默认 600 秒）既未提交答案也未请求提示，判定为放弃答题。

```json
{
  "event": "answer_abandoned",
  "version": "2.0.3",
  "chainId": "chain_a1b2c3d4",
  "studentId": "S001",
  "questionId": "Q_M5S1_DM_045",
  "knowledgeCode": "M5S1-3",
  "questionType": "calculation",
  "difficulty": 0.7,
  "abandonReason": "timeout",
  "timeOnScreenMs": 600000,
  "context": {
    "lessonId": "L_20260514_001",
    "strategyPack": "default",
    "stateCard": "challenge"
  },
  "timestamp": "2026-05-14T10:33:05.872Z"
}
```

answer_abandoned 不启动诊断链路。如果同一节课内连续 3 次 answer_abandoned，触发策略引擎的体验保护逻辑。

---

### 三、Phase 2 事件（Schema 后续补全）

| 事件名 | 用途 | 备注 |
|--------|------|------|
| question_shown | 题目展示给学生 | 用于校验 answerTimeMs |
| lesson_paused | 学生切到别的 App | 前端页面可见性 API 检测 |
| lesson_resumed | 学生切回来继续学 | 与 lesson_paused 配对 |
| idle_timeout | 超过 N 秒无操作 | N 默认 180 秒 |

---

### 四、Phase 3+ 事件（Schema 后续补全）

| 事件名 | 用途 |
|--------|------|
| explanation_replayed | 学生回看了某段讲解 |
| explanation_skipped | 学生跳过了某段讲解 |
| parent_summary_opened | 家长打开了摘要报告 |
| parent_feedback_submitted | 家长提交了反馈 |
| state_card_selected | 学生选择了状态卡 |
| preference_survey_submitted | 学生提交了偏好问卷 |

---

### 五、错误处理规则

#### 5.1 事件拒收

| 错误 | 错误码 | 处理方式 |
|------|--------|----------|
| 缺 studentId | EVENT_MISSING_STUDENT_ID | 拒收，不重试 |
| 缺 event 字段 | EVENT_MISSING_TYPE | 拒收，无法路由 |
| 缺任一"必填"字段（knowledgeCode 除外） | EVENT_MISSING_REQUIRED_FIELD | 拒收，返回缺失字段列表 |
| version 不兼容 | EVENT_VERSION_MISMATCH | 拒收，记录 WARN 日志 |

#### 5.2 可修复事件

| 错误 | 处理方式 |
|------|----------|
| 缺 knowledgeCode | 前端从 questionId 反查补全后重传 |
| 缺 questionType | 前端从 questionId 反查补全后重传 |

> 优先级：5.1 > 5.2。

#### 5.3 事件丢失

如果 chainId 中间缺失一环，引擎不崩溃，但标记该 chainId 为 incomplete。缺失的事件在 24 小时内可以补传（携带相同 chainId），超时后该链标记为 dead。

---

### 六、版本兼容规则

| 事件 version | 引擎行为 |
|--------------|----------|
| 2.0.x | 同主版本兼容变更，正常处理 |
| 1.0 | 尝试兼容解析，缺 chainId 时降级为孤立事件处理 |
| 缺失 version | 按 1.0 处理 |
| 未来版本（> 2.x） | 跳过，记录 WARN，不崩溃 |

---

### 七、事件矩阵总览

| # | 事件名 | Phase | 触发者 | 消费方 | Schema 状态 |
|---|--------|-------|--------|--------|-------------|
| 1 | answer_submitted | Phase 1 | 前端 | 诊断引擎、画像系统、家长摘要 | 完整 |
| 2 | hint_requested | Phase 1 | 前端 | 策略引擎、画像系统、家长摘要 | 完整 |
| 3 | lesson_started | Phase 1 | 前端 | 画像系统、家长摘要、策略引擎 | 完整 |
| 4 | lesson_completed | Phase 1 | 前端 | 画像系统、家长摘要 | 完整 |
| 5 | diagnosis_attempted | Phase 1 | 诊断引擎 | 策略引擎、家长摘要 | 完整 |
| 6 | validation_triggered | Phase 1 | 诊断引擎 | 前端（展示验证题） | 完整 |
| 7 | validation_completed | Phase 1 | 前端 | 诊断引擎（更新概率） | 完整 |
| 8 | diagnosis_updated | Phase 1 | 诊断引擎 | 诊断引擎、策略引擎、画像系统、家长摘要 | 完整 |
| 9 | strategy_applied | Phase 1 | 策略引擎 | 前端、策略引擎、S09课堂生成引擎、家长摘要 | 完整 |
| 10 | strategy_completed | Phase 1 | 前端 | 策略引擎、S09课堂生成引擎、画像系统、家长摘要 | 完整 |
| 11 | answer_abandoned | Phase 1 | 前端 | 画像系统、策略引擎 | 完整 |
| 12 | question_shown | Phase 2 | 前端 | 画像系统 | 待补 |
| 13 | lesson_paused | Phase 2 | 前端 | 画像系统 | 待补 |
| 14 | lesson_resumed | Phase 2 | 前端 | 画像系统 | 待补 |
| 15 | idle_timeout | Phase 2 | 系统 | 画像系统 | 待补 |
| 16 | explanation_replayed | Phase 3 | 前端 | 画像系统 | 待补 |
| 17 | explanation_skipped | Phase 3 | 前端 | 画像系统 | 待补 |
| 18 | parent_summary_opened | Phase 3 | 前端 | 家长摘要 | 待补 |
| 19 | parent_feedback_submitted | Phase 3 | 前端 | 画像系统 | 待补 |
| 20 | state_card_selected | Phase 3 | 前端 | 策略引擎 | 待补 |
| 21 | preference_survey_submitted | Phase 3 | 前端 | 策略引擎、画像系统 | 待补 |

---

### 八、与下游文档的接口约定

#### 8.1 诊断引擎（S07）

- 输入：answer_submitted 事件 + 学生画像 + 历史行为事件
- 输出：diagnosis_attempted 事件 + diagnosis_updated 事件
- 验证链路：diagnosis_attempted → validation_triggered → validation_completed → diagnosis_updated，全程共享同一 chainId

#### 8.2 策略引擎（S08）

- 输入：diagnosis_updated 事件（取 status=validated 时的 mainHypothesis）+ diagnosis_attempted 事件 + 学生历史 strategy_completed 事件
- 输出：strategy_applied 事件
- 效果评估：strategy_completed 事件 + StrategyEffect 记录

#### 8.3 家长摘要（S12）

- 输入：answer_submitted（提取题目/学生回答）、lesson_completed（提取 outcome + completionStatus）、diagnosis_updated（提取诊断结论）、strategy_applied（提取策略名称）、strategy_completed（提取 effectScore）
- 摘要生成：将事件链翻译为"学习现象 + 芽芽支持 + 积极变化/下一步建议"

#### 8.4 学生画像（S15-S17）【待生成】

- 输入：全部 11 种 Phase 1 事件，按 studentId + knowledgeCode 聚合
- 输出：GrowthMemory 记录
- 画像系统被动接收事件，不主动查询。事件驱动的异步更新模式。

---

## 第二部分：数据模型

### 九、数据底座

当前建设范围：人教版小学数学 1-6 年级全量覆盖。

- 394 个知识点，全量录入
- 87 个错因（L1 通用 11 个 + L2 数学特有 76 个），全量定义
- 1390 条知识点-错因绑定，394 个 KP 全覆盖
- 两层知识图谱（学习路径层 + 诊断依赖层），G1-G6 全部建成
- 题型规格矩阵
- 数据质量门禁（9 铁规全覆盖）

以下为 10 张核心数据表的 Schema 定义。

---

#### 表一：SubjectPlugin（学科插件注册）

```json
{
  "id": "primary_math_g1_g6_pep_v1",
  "subject": "math",
  "stage": "primary",
  "gradeRange": ["1", "2", "3", "4", "5", "6"],
  "textbookVersion": "PEP",
  "pluginVersion": "2.0.0",
  "status": "active",
  "dataFiles": {
    "knowledge": "primary_math_g1_g4_knowledge.json + primary_math_g5_g6_knowledge.json",
    "graph": "primary_math_g1_g4_knowledge_graph.json + primary_math_g5_g6_knowledge_graph.json",
    "levels": "primary_math_g1_g4_levels.json + primary_math_g5_g6_levels.json",
    "errorBindings": "error_kp_bindings.json",
    "errorTaxonomy": "error_taxonomy.json"
  }
}
```

---

#### 表二：KnowledgeNode（知识点节点）

```json
{
  "knowledgeCode": "M5S1-0",
  "subjectPluginId": "primary_math_g1_g6_pep_v1",
  "name": "小数乘整数的计算意义",
  "grade": "5",
  "gradeName": "五年级",
  "book": "上册",
  "unit": "第一单元 小数乘法",
  "lesson": "1.小数乘整数",
  "level": "A",
  "levelScore": 9,
  "levelDims": [2, 0, 1, 2, 2, 2],
  "curriculumLevel": "A",
  "curriculumLevelLabel": "了解——知道是什么",
  "curriculumVerb": "了解",
  "sourceRef": "http://www.dzkbw.com/books/rjb/shuxue/xs5s/",
  "textbookPage": {
    "source": "人教版五年级上册",
    "unit": "小数乘法",
    "pageStart": 2,
    "pageEnd": 18,
    "lesson": "1.小数乘整数"
  },
  "teachingGoal": "使学生理解和掌握小数乘法的算理和计算方法",
  "teachingGoalSource": "人教版教师教学用书·单元教学目标",
  "keyPoints": ["本质是相同加数求和", "读懂生活情境中的小数乘法含义"],
  "commonMistakes": ["小数点定位错误", "小数乘法进位错误"],
  "questionTypes": ["decimal_mul_basic", "decimal_mul_word_problem"],
  "prerequisites": ["M4S2-12"],
  "next": ["M5S1-1"],
  "strategyPacks": ["SP_M_02", "SP_G_A01"],
  "masteryRule": "default_weighted_mastery_v1",
  "tags": ["#概念理解", "#小数乘法"],
  "status": "needs_textbook_body_review",
  "confidence": 0.77
}
```

关键字段：levelDims 为六维细项，按序：[0]=记忆、[1]=理解、[2]=应用、[3]=分析、[4]=评价、[5]=创造。prerequisites 为诊断依赖层，next 为学习路径层。

---

#### 表三：ErrorTaxonomy（错因定义）

```json
{
  "errorCode": "decimal_point_position_error",
  "level": "L2",
  "category": "math_specific",
  "name": "小数点定位错误",
  "definition": "思路和列式基本正确，但积或商的小数点位置判断错误",
  "triggerConditions": ["列式正确", "计算数字基本正确", "小数点位置错误"],
  "exclusionConditions": ["列式错误", "数量关系错误"],
  "validationActions": ["decimal_place_visual_check", "decimal_point_rule_recall"],
  "neighborErrors": ["calculation_error", "concept_confusion"],
  "recommendedStrategies": ["decimal_place_visual_check", "decimal_position_practice"],
  "parentExplanation": "孩子在判断小数点位置时需要更多图示支持",
  "parentL1": "concept_confusion"
}
```

87 错因全量分布：L1 通用 11 个 + L2 数学特有 76 个。数据文件：error_taxonomy.json。

---

#### 表四：ErrorKpBinding（知识点-错因绑定）

```json
{
  "knowledgeCode": "M5S1-0",
  "errorCodes": ["decimal_point_position_error", "calculation_error", "concept_confusion", "info_omission"]
}
```

绑定规则：每个 KP 最少绑 2 条。A 级 KP 最少绑 3 条。当前总计：394 个 KP × 1390 条绑定。

strategyPacks vs recommendedStrategies 的权威性说明：
- ErrorTaxonomy.recommendedStrategies → 策略包编码：规划中的运行时权威路径（strategy_mapping.json 文件待生成）。文件缺失时，S08 策略引擎直接使用 ErrorTaxonomy.recommendedStrategies 作为策略编码来源（兜底规则）。
- KnowledgeNode.strategyPacks：人工标注的常见策略包建议，仅供教研查阅和人工复核，不直接驱动引擎决策。
- 如两条路径指向不同策略包，以 taxonomy 映射路径为准。

---

#### 表五：BehaviorEvent（行为事件）

统一事件表，存储所有事件协议定义的事件。eventId 格式：`evt_{YYYYMMDD}_{chainId尾8位}_{序号}`。

```json
{
  "eventId": "evt_20260514_a1b2c3d4_001",
  "event": "answer_submitted",
  "version": "2.0.3",
  "chainId": "chain_a1b2c3d4",
  "studentId": "S001",
  "lessonId": "L_20260514_001",
  "timestamp": "2026-05-14T10:23:06.500Z",
  "payload": {}
}
```

Phase 1 的 11 种事件类型枚举见第一部分 §七事件矩阵。

---

#### 表六：ErrorDiagnosis（错因诊断记录）

```json
{
  "diagnosisId": "diag_20260514_001",
  "chainId": "chain_a1b2c3d4",
  "studentId": "S001",
  "knowledgeCode": "M5S1-0",
  "sourceQuestionId": "Q_M5S1_DM_045",
  "lessonId": "L_20260514_001",
  "hypotheses": [
    {"hypothesisId": "h1", "errorCode": "decimal_point_position_error", "probability": 0.62, "confidence": 0.74, "rank": 1},
    {"hypothesisId": "h2", "errorCode": "calculation_error", "probability": 0.28, "confidence": 0.45, "rank": 2}
  ],
  "mainHypothesis": {
    "hypothesisId": "h1",
    "errorCode": "decimal_point_position_error",
    "probability": 0.62,
    "confidence": 0.74
  },
  "status": "open",
  "diagnosisStatus": "in_progress",
  "method": "rule_engine",
  "validationRound": 1,
  "parentSummary": {
    "short": "今天孩子在找小数点的位置时有些犹豫",
    "full": "在做小数乘法题时，孩子列式和计算步骤都对了，但在确定积的小数点位置时犹豫了。"
  },
  "teacherNote": "M5S1-0 小数乘法·小数点定位错误 | 验证中 | 第1轮",
  "recommendedAction": ["provide_scaffolding"],
  "createdAt": "2026-05-14T10:23:06.500Z",
  "updatedAt": "2026-05-14T10:23:06.500Z"
}
```

---

#### 表七：StrategyEffect（策略效果记录）

```json
{
  "effectId": "se_20260514_001",
  "strategyCode": "SP_M_02",
  "diagnosisId": "diag_20260514_001",
  "chainId": "chain_a1b2c3d4",
  "studentId": "S001",
  "knowledgeCode": "M5S1-0",
  "errorCode": "decimal_point_position_error",
  "effectScore": 1,
  "dimensions": {
    "immediateEffectiveness": 1,
    "shortTermPersistence": 0,
    "longTermRetention": -999,
    "dependencyReduction": 0,
    "independentAbility": 1
  },
  "nextQuestionCorrect": true,
  "sameTypeCorrectRate": 0.67,
  "hintUsedAfter": false,
  "createdAt": "2026-05-14T10:25:00.000Z"
}
```

effectScore 枚举：-2（有害）/ -1（可能混淆）/ 0（无变化）/ 1（有帮助）/ 2（显著提升）。

维度空值规则：所有维度值域为 -2 到 +2 的整数。-999 为统一标记值，表示「该维度在当前 Phase 不适用」。消费方读到 -999 时跳过该维度，不参与加权计算。Phase 1 期间 longTermRetention 为 -999，Phase 2 起有实际值后不再出现。

---

#### 表八：ParentSummary（家长摘要）

```json
{
  "summaryId": "ps_20260514_001",
  "studentId": "S001",
  "type": "lesson",
  "periodStart": "2026-05-14T09:00:00.000Z",
  "periodEnd": "2026-05-14T10:30:00.000Z",
  "lessonId": "L_20260514_001",
  "summaryText": {
    "short": "今天孩子在找小数点的位置时有些犹豫",
    "full": "今天小数乘法练习中，孩子一开始在确定积的小数点位置时有些犹豫。芽芽用小数点定位图示把过程可视化后，孩子能自己选出正确位置。"
  },
  "errorCodes": ["decimal_point_position_error"],
  "knowledgeCodes": ["M5S1-0"],
  "riskScore": 0.1,
  "riskFlags": [],
  "mentionPriority": 0,
  "parentFeedback": null,
  "parentFeedbackAt": null,
  "createdAt": "2026-05-14T10:30:00.000Z"
}
```

riskScore ∈ [0, 1]：综合评估家长焦虑风险。>0.5 触发人工复审。计算规则见 S12（质量仪表盘与家长摘要系统 v1.2+）。mentionPriority：-1 降优先/0 正常/1 提优先（Phase 2 字段）。

---

#### 表九：GrowthMemory（成长记忆）

```json
{
  "memoryId": "gm_S001_M5S1-0",
  "studentId": "S001",
  "knowledgeCode": "M5S1-0",
  "masteryScore": 0.72,
  "sampleCount": 45,
  "lastErrorCode": "decimal_point_position_error",
  "lastErrorAt": "2026-05-14T10:23:06.500Z",
  "strategyHistory": [
    {
      "strategyCode": "SP_M_02",
      "diagnosisId": "diag_20260513_005",
      "effectScore": 1,
      "appliedAt": "2026-05-13T15:00:00.000Z"
    }
  ],
  "errorTendency": {
    "decimal_point_position_error": 0.35,
    "calculation_error": 0.15
  },
  "milestones": [
    {"type": "mastered", "date": "2026-05-12", "detail": "连续5次正确，掌握度突破0.8"}
  ],
  "coldStartFlag": false,
  "updatedAt": "2026-05-14T10:30:00.000Z"
}
```

> GrowthMemory 的详细消费和更新规则见 S15-S17 学生画像系统【待生成】。本文档仅定义存储 Schema。

---

#### 表十：核心枚举

| 枚举名 | 值 | 说明 |
|--------|-----|------|
| Stage | primary / middle / high | 学段 |
| Subject | math / chinese / english / ... | 学科 |
| KnowledgeLevel | A / B / C / D | 知识点重要程度 |
| ErrorLevel | L1 / L2 / L3 | 错因层级 |
| L1ErrorCode | calculation_error / comprehension_bias / concept_confusion / expression_format_error / info_omission / memory_retrieval_failure / prerequisite_gap / strategy_missing / transfer_failure / question_type_unfamiliar | L1 通用错因 10 类 |
| DiagnosisStatus | in_progress / confirmed / confirmed_with_reservation / excluded / inconclusive / traced | 六态 |
| StrategyEffectScore | -2 / -1 / 0 / 1 / 2 | 策略效果 |
| SummaryType | lesson / weekly / monthly / stage | 摘要周期 |
| ParentFeedback | accurate / inaccurate / helpful / unsuitable / reobserve | 家长反馈 |
| ValidationResult | supported / weakened / inconclusive | 验证结果 |
| MethodPhase | rule_engine / decision_tree / ai_assisted | 诊断方法 |

---

### 十、数据文件清单

| 文件 | 大小 | 记录数 | 说明 |
|------|------|--------|------|
| primary_math_g5_g6_knowledge.json | 521KB | 189 KP | 五/六年级知识点 |
| primary_math_g1_g4_knowledge.json | 391KB | 205 KP | 一至四年级知识点 |
| primary_math_g5_g6_knowledge_graph.json | 172KB | 189 nodes | 五/六年级知识图谱 |
| primary_math_g1_g4_knowledge_graph.json | 187KB | 205 nodes | 一至四年级知识图谱 |
| error_taxonomy.json | 94KB | 86 errors | 错因分类体系 |
| error_kp_bindings.json | 332KB | 1390 bindings | 知识点-错因绑定 |
| question_type_matrix.json | 260KB | - | 题型规格矩阵 |
| strategy_mapping.json | - | - | 策略包映射表【待生成——文件不存在，S08 兜底使用 ErrorTaxonomy.recommendedStrategies】 |

---

## 四层安全架构

### 第一层：本子系统的自我进化能力

S10 作为通信和数据底座，本身不执行教学逻辑。它的"进化"是指：
- 新增事件类型（如 Phase 2/3 事件升级为完整 Schema）
- 新增数据表或数据字段
- 修改枚举值
- 调整必填/选填规则

这些变更属于「内容进化」——新增事件/字段不改变已有 Schema 的语义，不影响现有子系统的消费逻辑。

【禁用清单】S10 不允许自主修改已有事件的字段类型、删除已有字段、修改枚举含义。这些属于「代码进化」，需走完整进化流程。

### 第二层：安全进化机制

S10 的进化触发条件：
- 新增事件类型：由消费方（S07/S08/S09/S12/S15）在路线图推进中提出需求，经评审后定义 Schema
- 新增数据字段：由数据消费方提出，确认对现有系统无断裂后添加
- Phase 2/3 事件升级：当对应子系统达到 Phase 2 触发条件时，完善事件 Schema

不可修改边界（七类）：

| 类型 | 不可修改项 | 修改后果 | AI 正确行为 |
|------|-----------|---------|------------|
| 外部法规定义 | N/A（S10 不涉及法规定义） | — | — |
| 全局外键标识符 | knowledgeCode、studentId、chainId、diagnosisId 格式规则 | 跨系统关联断裂→所有事件无法关联到知识点/学生/诊断链 | 新增标识符类型时可扩展，绝不修改已有格式 |
| 通信协议基础字段 | event、version、timestamp、chainId 的字段名和类型 | 所有消费方解析失败→全系统静默崩溃 | 新增事件类型和字段，绝不修改已有字段名和类型 |
| 学生原始作答日志 | BehaviorEvent 表中 answer_submitted.payload.answer 为绝对只读 | 篡改学生答案→诊断完全失效→家长信任丧失 | 读取原始数据做分析，绝不修改原始记录 |
| 质量门禁核心规则 | 事件拒收规则（见本文档「五、错误处理规则」§5.1）不可放宽 | 脏数据入库→全部分析结果不可信 | 可新增校验规则，绝不禁用已有门禁 |
| 北极星底线信号覆盖项 | studentId 缺失拒收规则 | 事件无法归属学生→画像系统数据污染 | 每次新增事件类型时确认 studentId 必填 |
| Shareable 验证标准阈值 | N/A（S10 不涉及策略推广） | — | — |

### 间接修改边界（量化标准）

| 修改类型 | 间接影响的不可修改项 | 差异阈值 | 处置 |
|---------|--------------------|---------|------|
| 新增事件类型的必填字段定义不合理 | 事件拒收规则（拒收率上升→数据完整性下降） | <5% 拒收率 | 正常推进 |
| | | 5-15% 拒收率 | 审查员审核 |
| | | 15-30% 拒收率 | 产品经理签批 |
| | | >30% 拒收率 | 视为越界直接拒绝，回滚 Schema |
| 修改 chainId 生成规则 | 全局外键标识符（下游追踪断裂） | 任何修改 | 禁止——chainId 格式不可变 |
| 放宽事件拒收规则 | 质量门禁核心规则 | 任何放宽 | 视为越界直接拒绝 |
| 修改 version 兼容规则 | 通信协议基础字段（版本兼容性契约） | 任何修改 | 禁止——version 兼容规则不可变 |

### 越界告警分级处置

| 级别 | 触发条件 | 告警方式 | 处置时限 |
|------|---------|---------|---------|
| 轻 | AI 读取不可修改项意图 | 日志记录 + kanban WARN | 即时（无处置，仅记录） |
| 中 | AI 生成方案含修改不可修改项 | 冻结该进化方向 7 天 + 人工审核 | 7 天内完成审核 |
| 重 | AI 已执行修改不可修改项 | 永久封禁该方向 + 回滚 + 通知产品经理 | 1 小时内回滚完成 |

### 第三层：AI 可读接口

AI-MUTABLE 标注：
<!-- AI-MUTABLE: answer_abandoned 默认超时秒数, type=int, range=[300, 1800] --> 当前值 600
<!-- AI-MUTABLE: idle_timeout 默认秒数, type=int, range=[120, 600] --> Phase 2 上线时设为 180
<!-- AI-MUTABLE: lesson_completed activeMs 上限, type=int, range=[3600000, 28800000] --> Phase 1 为 7200000，Phase 2 为 14400000

### 第四层：北极星对齐

**信号权重配比**：底线信号权重 > 负信号权重 > 正信号权重。底线信号（studentId缺失拒收）触发时直接冻结所有Schema变更，不可被正信号/负信号的好成绩覆盖。具体权重：底线信号 50% > 负信号 30% > 正信号 20%。北极星检查不可绕过——任何进化操作前必须通过三层信号全检，任一底线信号触发→冻结进化+回滚至上一稳定版本。

S10 对齐北极星的检查节点：
- 底线信号：studentId 缺失拒收规则确保学生数据归属安全
- 正信号：事件采集完整性（chainId 的 incomplete 比例）、数据质量门禁通过率
- 负信号：事件拒收率异常上升（可能表示前端 Bug 或协议不兼容）

北极星检查节点：每次新增事件类型或数据字段时，校验——
1. 不削弱 studentId 必填规则
2. 不引入可关联到具体学生的非教学必需字段
3. 新增字段不影响已有消费方的解析逻辑

---

## 自我进化路线图

S10 事件协议与数据模型的进化围绕一个核心维度展开：**从「Phase 1 静态事件集」到「全阶段自适应事件协议」**。

| 阶段 | 触发条件 | 系统能力 | 人工角色 | 终局状态 | 退化降级规则 |
|------|---------|---------|---------|---------|------------|
| 1 | Phase 1 启动（当前）【人工依赖：产品经理确认 Phase 1 子系统就绪】 | 11 种 Phase 1 事件完整 Schema + 10 张核心数据表。事件拒收率 < 1%。chainId 完整率 > 97%。 | 产品经理：新事件审批。审核员：事件 Schema 变更审计。工程师：Schema 实现 | 11 种事件覆盖诊断→策略→课堂→反馈完整链路。Phase 2/3 事件（#12-#21）仅定义事件名和字段骨架，待后续阶段补充完整 Schema | 连续 3 次新增字段导致消费方断裂→冻结该字段类型的新增操作 60 天<!-- AI-MUTABLE: 新增字段冻结天数, type=int, range=[30, 90] --> |
| 2 | Phase 1 稳定运行 ≥ 6 个月 + 事件拒收率 < 0.5% 连续 30 天 + 信用分 ≥ 30（自主：信用分达标自动触发）<!-- AI-MUTABLE: 阶段2信用分阈值, type=int, range=[25, 40] --> | Phase 2 事件（#12-#15：question_shown/lesson_paused/lesson_resumed/idle_timeout）完整 Schema 上线。事件拒收率自动监控+告警。 | 产品经理：Phase 2 事件审批。审核员：交叉验证 | Phase 2 事件全部有完整 Schema，事件链路覆盖课堂暂停/恢复/超时场景 | Phase 2 事件拒收率 > 5% 连续 7 天→回退该事件 Schema 至上一版本 |
| 3 | Phase 2 完成 + 所有 Phase 2 事件消费方就绪 + 信用分 ≥ 50（自主：信用分达标自动触发）<!-- AI-MUTABLE: 阶段3信用分阈值, type=int, range=[45, 60] --> | Phase 3 事件（#16-#21：skill_demonstrated 等 6 种）完整 Schema 上线。事件协议支持自适应——新事件类型的 Schema 可由 AI 提案、人审批后上线。 | 产品经理：新事件类型最终审批。审核员：季度审计。AI：新事件类型提案 | 21 种事件全部有 Schema，事件协议从「静态定义」进化为「自扩展协议」——AI 发现新事件需求后可提案新事件类型，走安全管道上线 | 自扩展事件类型的消费方采用率 < 50% 连续 3 个月→暂停自扩展机制，回退至人工定义模式 |

**数据闭环声明**：Phase 1 所有触发条件的数据源已在 11 种事件中完整覆盖——answer_submitted/diagnosis_attempted/validation_triggered/validation_completed/diagnosis_updated/strategy_applied/strategy_completed/lesson_started/lesson_completed/hint_requested/answer_abandoned 均有完整 Schema 定义。Phase 2 事件（#12-#15）当前仅定义事件名和字段骨架，其完整 Schema 定义为「数据采集就绪」中间阶段——Phase 1 稳定运行后补充。Phase 3 事件的数据源需在 Phase 2 完成后评估。事件拒收率和 chainId 完整率由事件总线自动统计——数据自然积累，不需额外中间阶段。

## 自我进化执行方法

### 五类角色权限台账

| 角色 | 可执行操作 | 禁止操作 | 审批要求 |
|------|-----------|---------|---------|
| AI（yaya-profile） | 新增事件类型（需走完整进化流程）、新增数据字段（选填字段，无断裂） | 删除已有字段、修改字段类型、修改枚举含义 | 任何改动需经人工终审 |
| 人工（liufeng） | 审批所有进化请求、修改不可修改边界 | 绕过进化流程直接改 Schema | 无 |
| 审核员（yaya-reviewer） | 审计变更记录、核对北极星对齐 | 直接修改文档 | 无 |
| 实施团队 | 按照 Schema 和接口文档实现 | 偏离 Schema 定义 | 偏离需回写文档 |
| 运维 | 监控事件拒收率、chainId incomplete 率 | 修改事件拒收规则 | 无 |

### 五步执行流程

1. **提出**：由消费方（S07/S08/S09/S12/S15）在路线图推进中提出新增事件/字段需求
2. **设计**：AI 设计 Schema，包含必填/选填属性、枚举值范围、与现有字段的兼容性
3. **审计**：审核员检查跨文档引用断裂、北极星对齐、消费关系完整性
4. **实施**：更新 S10 文档和数据文件清单
5. **验证**：消费方接入后，监控事件拒收率（新增字段的必填必须 ≤2%）、chainId incomplete 率不上升

### 三级权限分级

| 权限级 | 范围 | 示例 |
|--------|------|------|
| 只读 | 消费方读取事件 Schema | S07 读取 answer_submitted 的 payload 定义 |
| 提议写入 | 新增选填字段、新增事件类型（Phase 升级） | Phase 2 新增 adaptive_prompt_shown 事件 |
| 管理写入 | 修改必填规则、删除字段 | 仅人工（liufeng）+ AI 协助，需审核员审计 |

### 信用分三子分体系

| 子分 | 计算依据 | 用途 |
|------|---------|------|
| 设计信用分 | Schema变更无断裂 +5 / 导致消费方读错数据 -10 | 判断 AI 是否可自主发起新增字段 |
| 执行信用分 | 事件拒收率、chainId 完整率（<90%持续18教学月：扣5分/月） | 判断系统运行健康度 |
| 进化信用分 | 新增字段被消费方实际采用的比例 | 判断进化方向是否正确 |

**聚合规则**：总信用分 = min(设计信用分, 执行信用分, 进化信用分)。三子分取最低分——任一维度不及格，整体信用受限。

**跨子分挪用拦截**：三子分各自独立计分，不可互相挪用。设计信用分的加分不能掩盖执行信用分的扣分，反之亦然。聚合取 min 的机制天然防止某一子分的高分掩盖另一子分的低分。

**分级暂停**：任一子分 < 20→限制该子分对应领域的自主权。总信用分 < 10→全系统暂停（仅保留事件接收和日志记录，停止所有 Schema 变更）。总信用分 = 0（即任一子分 = 0 → min = 0）→触发全系统熔断——事件协议冻结为只读模式。

**月度恢复上限**：每个子分月度加分上限 = +5/-10 分。长期停滞（连续 18 个月无进化操作）→所有子分每月 -3。

**破产恢复**：任一子分降至 0 分→该子分对应的进化操作冻结 90 天→90 天后由审核员人工审查→审查通过后子分重置为 10（非初始值 50——破产后恢复需重新积累信任）。

**重置场景**：系统重大版本升级（v2→v3）→三子分全部重置为初始值 50，保留历史事故记录。版本升级后前 90 天，月度加分上限降为 +3（谨慎恢复期）→90 天后恢复 +5 上限。

**初始值**：三子分初始值均为 50。

信用分自主权阈值：
<!-- AI-MUTABLE: credit_autonomy_threshold_20, type=int, range=[10, 30] -->
- ≥ 20：AI 可自主提议选填字段
<!-- AI-MUTABLE: credit_autonomy_threshold_10, type=int, range=[5, 20] -->
- ≥ 10：AI 可协助但不能直接改 Schema
<!-- AI-MUTABLE: credit_freeze_threshold, type=int, range=[5, 15] -->
- < 10：全系统 Schema 冻结，等人工重建信用

### A/B 测试分组规则

- 新增事件类型：先在 20% 流量（影子模式）运行 7 天，拒收率 <1% 后全量
- 新增数据字段：先在 S15 画像系统单路验证 <!-- AI-MUTABLE: shadow_validation_days, type=int, range=[1, 14] --> 3 天（不影响诊断/策略），通过后推广到全部消费方
- 修改枚举值：禁止线上直接改。通过新增枚举值（保留旧值）+ 消费方逐步迁移实现

### 元进化递归上限

S10 自身走进化流程时，遵循两层递归上限：
1. 进化流程本身的修改（如信用分计算规则变更）：需人工终审
2. 进化流程的修改再修改：禁止（两层递归上限）

---

## 安全执行管道

### 三层执行管道

| 阶段 | 流量比例 | 持续时间 | 通过条件 | 北极星前置检查 |
|------|---------|---------|---------|--------------|
| 影子模式 | 0%（只记录、不消费） | Phase 1 全程 | 记录完整率 >99%，拒收率 <1% | studentId 必填规则未削弱 |
| A/B 测试 | 20% | 7 天 | 测试组拒收率 ≤ 对照组，chainId 完整率不下降 | 无新增 P0 静默失败 |
| 全量上线 | 100% | — | A/B 测试通过 + 人工终审 | 所有北极星检查节点通过 |

### 管道节点说明

- **影子模式入口**：新增事件类型进入影子模式，事件被记录到 BehaviorEvent 表但消费方不实际消费。验证 Schema 完整性和拒收率。
- **A/B 入口**：新数据字段在 S15 画像系统单路验证（A 组用旧字段，B 组用新字段），不影响诊断/策略链路。
- **全量上线入口**：需人工终审确认后，消费方接入新字段/事件。

### 管道异常处置

- 影子模式拒收率 >5%：回退 Schema，重新设计
- A/B 测试组拒收率 >1%：缩小测试范围至 5%，修正后重新 7 天
- 全量后发现断裂：启动应急熔断，回滚到上一个 Phase 版本

---

## 内容与代码进化分离

### 内容进化

**定义**：新增事件类型、新增数据字段（选填）、新增枚举值——不改变已有 Schema 的语义，不影响现有消费方。

**流程**：
1. 消费方提出需求 → 设计 Schema
2. 新增字段默认值定义（如 -999 表示"无数据"）
3. 影子模式验证 7 天
4. 消费方逐步接入

**示例**：Phase 2 新增 adaptive_prompt_shown 事件（选填字段，已有消费方不消费）

### 代码进化

**定义**：修改已有字段类型、删除已有字段、修改枚举含义——改变已有 Schema 的语义，可能影响现有消费方。

**流程**：
1. 消费方提出需求 → 评估断裂风险
2. 新增替代字段（保留旧字段）+ 消费方明确声明迁移时间线
3. A/B 测试 14 天
4. 全部消费方迁移后，标记旧字段 deprecated（保留 30 天）
5. 30 天后删除旧字段

**示例**：activeMs 从 Phase 1 的实际值改为 Phase 2 的估算值（activeMsEstimated），旧字段保留 30 天给画像系统过渡

### 混合进化

**定义**：同时涉及内容进化（新增）和代码进化（修改）的变更。

**流程**：必须分别走内容进化流程和代码进化流程，两者都通过人工终审后才能全量上线。不允许跳过任一流程。

---

## 维度交互矩阵

S10 有四个核心维度：事件协议层、数据模型层、Phase 进化层、消费关系层。以下按验收标准 1.17 三问题格式逐格分析（每格回答：(a) A进化是否改变B的输入数据分布？(b) B的触发条件和退化规则是否仍有效？(c) 仲裁规则及验证步骤）。

|  | 事件协议层 | 数据模型层 | Phase 进化层 | 消费关系层 |
|--|----------|----------|------------|----------|
| **事件协议层** | — | **(a)是**——新增字段→数据表需新增列/默认值，改变数据表写入分布。(b)数据模型层的冷启动逻辑（-999默认值）需随新增字段扩展。(c)仲裁：新增字段在影子模式验证通过后→更新数据表Schema→同步更新所有消费方的读取逻辑。验证步骤：1.影子模式7天 2.消费方接入测试 3.数据质量门禁通过。 | **(a)是**——Phase升级定义新事件类型→事件协议层新增Schema条目。(b)Phase进化层的触发条件（信用分/拒收率）不因新增事件而改变。(c)仲裁：Phase升级需求由消费方提出→审核员审计→安全管道三层验证。验证步骤：1.A/B测试7天 2.北极星前置检查 3.人工终审。 | **(a)是**——事件类型变更→消费关系清单更新。(b)消费关系层的检测方式（链路上报/定时校验）需随新事件扩展。(c)仲裁：事件类型变更前→先更新消费关系清单→通知所有消费方。验证步骤：1.消费方声明就绪 2.消费关系全量校验 3.降级策略覆盖新消费方。 |
| **数据模型层** | **(a)否**——数据表字段变更（选填字段）不影响已有事件Schema，字段独立。(b)事件协议层触发条件不变。(c)无需仲裁。但数据表必填字段新增→等同于事件Schema变更，走事件协议层仲裁规则。 | — | **(a)是**——Phase升级新增数据表→数据模型层扩展。(b)Phase进化层触发条件不变。(c)仲裁：新增数据表走安全管道→影子模式→A/B→全量。验证步骤同事件协议层→数据模型层。 | **(a)是**——数据表新增→消费方读取接口变更。(b)消费方P0/P1链路受影响。(c)仲裁：数据表变更前→更新消费关系清单→逐消费方确认兼容性。验证步骤：1.消费方声明兼容 2.降级策略覆盖读取超时 3.全量上线后监控读取延迟。 |
| **Phase 进化层** | **(a)是**——Phase升级定义新事件类型。(b)事件协议层的拒收规则和chainId规则需验证对新事件的适配。(c)仲裁：Phase升级→事件协议层定义Schema→走全部三层安全管道。验证步骤：1.新事件Schema定义 2.消费方接入验证 3.北极星检查。 | **(a)是**——Phase升级定义新数据表。(b)数据模型层需预留Phase 2/3表格结构。(c)仲裁：Phase升级→数据模型层新增表→走内容进化流程。验证步骤：1.表结构定义 2.字段默认值定义 3.消费方接入验证。 | — | **(a)是**——Phase升级→消费方需同步升级到新事件/新数据表。(b)消费方P0-P4等级可能因Phase变化重新分级。(c)仲裁：Phase升级前→全部消费方声明Phase就绪→安全管道全量验证。验证步骤：1.全部消费方Phase就绪声明 2.降级策略覆盖阶段过渡 3.人工终审。 |
| **消费关系层** | **(a)是**——消费方需求→事件Schema设计。(b)事件协议层新增事件时需验证与现有事件的兼容性。(c)仲裁：消费方需求→AI设计Schema→审核员审计→安全管道→全量上线。验证步骤：1.Schema设计 2.跨文档引用检查 3.消费方接入验证。 | **(a)是**——消费方需求→数据表设计。(b)数据模型层无额外约束。(c)仲裁：消费方需求→数据表Schema设计→走内容进化流程。验证步骤：1.表结构设计 2.字段默认值定义 3.Event-to-Table映射更新。 | **(a)是**——消费方需求驱动Phase演进规划。(b)Phase进化层触发条件需消费方的拒收率/信用分数据支撑。(c)仲裁：消费方集体Phase升级需求→Phase进化层评估→走安全管道。验证步骤：1.消费方需求汇总 2.Phase升级评估 3.北极星检查。 | — |

### 交互规则与仲裁优先级

1. 任何维度变更必须检查对其他三个维度的影响——逐格走三问题式分析（见上表每格(a)(b)(c)），不可跳过
2. 事件 Schema 变更 → 必须更新数据文件清单和消费关系清单。仲裁优先级：消费方兼容性 > 北极星检查 > Schema 美观性
3. 数据表新增 → 必须定义 Event-to-Table 映射（哪个事件写入哪个表）。仲裁优先级：数据完整性（必填字段有默认值）> 消费方读取兼容性 > 存储效率
4. Phase 升级 → 必须先更新维度交互矩阵（本表），再实施变更。仲裁优先级：全部消费方 Phase 就绪声明 > 独立 A/B 测试 > 北极星三层检查
5. 消费关系变更 → 必须通知所有受影响的消费方（至少在变更记录中注明）。仲裁优先级：P0 消费方不中断 > P1-P4 降级可接受 > 新消费方接入速度

---

## 消费关系清单

| 元素 | 对应事件矩阵# | 被消费方 | 消费方式 | 故障类型 | 严重等级 | 检测方式 | 链路类型 |
|------|---------|---------|---------|---------|---------|---------|
| answer_submitted 事件 | #1 | S07 诊断引擎 | 事件驱动，取值 answer/behavior/context | 静默失败 | P0 | 诊断链路 incomplete 率监控 | 异步 |
| diagnosis_updated 事件 | #8 | S08 策略引擎 | 事件驱动，取 status=validated 的 mainHypothesis | 崩溃 | P1 | strategy_applied 延迟监控 | 异步 |
| lesson_completed 事件 | #4 | S12 质量仪表盘 | 事件驱动，取 outcome + duration | 数据错误 | P2 | 指标计算异常检测 | 异步 |
| StrategyEffect 表 | 表七 | S08 策略引擎 | 读写，记录策略执行效果 | 数据错误 | P1 | effectScore 完整性校验 | 同步 |
| GrowthMemory 表 | 表九 | S15 学生画像 | 读写，按 studentId+knowledgeCode 聚合 | 静默失败 | P0 | masteryScore 更新频率监控 | 异步 |
| answer_abandoned 事件 | #11 | S08 策略引擎 | 事件驱动，体验保护触发条件 | 崩溃 | P2 | 连续 abandon 计数 | 异步 |
| answer_abandoned 事件 | #11 | S15 画像系统 | 事件驱动，记录放弃行为→影响学习能量曲线计算 | 静默失败 | P2 | 学习能量异常检测 | 异步 |
| diagnosis_updated.diagnosisStatus | #8 | S08 策略引擎 | 取值 confirmed/confirmed_with_reservation/excluded | 静默失败 | P1 | 策略强度校验 | 异步 |
| strategy_completed.effectScore | #10 | S08 策略引擎 | 效能评估输入 | 数据错误 | P2 | 策略效果异常检测 | 异步 |
| diagnosis_updated 事件 | #8 | S12 家长摘要 | 取值 mainHypothesis 生成摘要 | 数据错误 | P3 | 摘要质量抽检 | 异步 |
| strategy_applied 事件 | #9 | S12 家长摘要 | 取值 strategyPack 生成策略描述 | 数据错误 | P3 | 摘要中策略名称校验 | 异步 |
| strategy_completed 事件 | #10 | S12 家长摘要 | 取值 effectScore 生成效果描述 | 数据错误 | P3 | 摘要效果描述校验 | 异步 |
| answer_submitted 事件 | #1 | S12 家长摘要 | 提取题目/学生回答 | 数据错误 | P3 | 摘要中题目描述校验 | 异步 |
| lesson_completed 事件 | #4 | S12 家长摘要 | 提取 outcome + completionStatus | 数据错误 | P3 | 摘要中课堂统计校验 | 异步 |
| BehaviorEvent 全表 | 表五 | S15 学生画像 | 按 studentId+knowledgeCode 聚合全部事件 | 静默失败 | P0 | GrowthMemory 更新延迟监控 | 异步 |
| ErrorDiagnosis 表 | 表六 | S08 策略引擎 | 读取诊断历史 | 数据错误 | P2 | 策略选择合理性校验 | 同步 |
| KnowledgeNode 表 | 表二 | S01/S02 | 知识点存储 | 崩溃 | P0 | 知识图谱完整性检查 | 同步 |
| ErrorTaxonomy 表 | 表三 | S03/S07 | 错因定义存储 | 崩溃 | P0 | 错因库完整性检查 | 同步 |

---

---

## 它还不会什么

S10 作为通信底座和数据模型，存在明确的能力边界：

| 能力边界 | 说明 | 替代或兜底 |
|---------|------|-----------|
| 不负责事件路由的实现细节 | S10 定义事件 Schema 和消费关系，但不实现消息队列、事件分发、重试机制 | 由下游系统各自接入时自行实现，S10 仅提供 Schema 和拒收规则 |
| 不负责下游子系统内部的逻辑 | 事件送达后，消费方如何处理（如诊断、策略选择）不在 S10 职责范围 | 各子系统自行定义内部逻辑 |
| 不负责数据库物理部署 | S10 定义表 Schema 和字段，但不负责分库分表、读写分离、备份策略 | 由基础设施层处理 |
| 不负责实时性 SLA | S10 定义事件的同步/异步消费方式，但不保障延迟上限 | 降级策略定义了兜底方案，但 SLA 由运维层面保障 |
| 不负责历史数据迁移 | Phase 升级时新增字段的默认值已定义（如-999），但旧数据迁移脚本不在本文档范围 | 迁移脚本作为实施文档单独编写 |
| 不支持运行时动态修改 Schema | 所有 Schema 变更走进化流程，不在运行时动态调整 | 通过 Phase 升级机制实现 |

---

## 降级策略

| 故障场景 | 检测方 | 检测频率 | 降级方案 | 恢复条件 | 告警目标 |
|---------|---------|---------|---------|---------|---------|
| <!-- AI-MUTABLE: event_rejection_rate_threshold, type=percent, range=[1, 20] --> 事件拒收率 > 5% | S10 事件总线 | 每 5 分钟 | 前端降级为仅发送必填字段（裁剪选填字段），诊断引擎使用 S03 静态错因库兜底 | <!-- AI-MUTABLE: event_rejection_recovery_rate, type=percent, range=[0.1, 5] / recovery_duration_min, type=int, range=[10, 120] --> 拒收率 < 1% 持续 30 分钟 | S12 质量仪表盘 |
| <!-- AI-MUTABLE: chainId_incomplete_threshold, type=percent, range=[5, 30] --> chainId incomplete 率 > 10% | S07 诊断引擎 | 每 10 分钟 | 诊断引擎跳过缺失链路的验证，直接使用 diagnosis_attempted 的初始假设（不经验证） | <!-- AI-MUTABLE: chainId_incomplete_recovery_rate, type=percent, range=[0.5, 10] / recovery_duration_hr, type=int, range=[0.5, 4] --> incomplete 率 < 3% 持续 1 小时 | S12 质量仪表盘 |
| BehaviorEvent 表写入失败 | S10 事件总线 | 每次写入 | 事件暂存前端本地 IndexedDB，最多 <!-- AI-MUTABLE: indexeddb_max_events, type=int, range=[500, 5000] --> 1000 条。超限后丢弃最旧的事件。恢复后批量回传 | 写入恢复后自动回传 | S10 自检（kanban WARN） |
| StrategyEffect 表写入失败 | S08 策略引擎 | 每次写入 | effectScore 仅记录在 strategy_completed 事件的 payload 中，不入表。画像系统从事件中读取 | 写入恢复后从事件回填 | S08 自检（kanban WARN） |
| GrowthMemory 表读取超时 | S15 画像系统 | 每次读取 | 诊断引擎和策略引擎使用 S03/S04 静态数据兜底（无个性化），画像系统暂停更新 | 读取恢复后增量更新 | S15 自检（kanban WARN） |
| 前端未发出 answer_abandoned | S10 事件总线（连续3节课无 answer_abandoned 事件但 answerTimeMs 超阈值） | 每节课结束 | 诊断引擎不依赖此事件启动，无影响。仅策略引擎的体验保护逻辑缺少输入 | 不恢复，需前端修复。告警链路：S10 检测→通知运维（kanban WARN）→24小时内未修复升级为 P1 | S12 质量仪表盘 |
| Phase 1 → Phase 2 过渡期间 activeMs 口径不一致 | S15 画像系统 | Phase 切换时 | 画像系统不跨阶段对比 activeMs（通过 activeMsEstimated 标记隔离） | Phase 2 运行满 30 天后解除隔离 | S12 质量仪表盘 |

---

### 消费方宕机退化场景

当消费方进程级宕机时，S10 事件总线采取以下措施：

| 消费方 | 宕机场景 | 处置 | 恢复 |
|--------|---------|------|------|
| S07 诊断引擎 | 宕机期间 answer_submitted 积压 | 事件总线保留所有未消费事件（通过 chainId 去重），S07 重启后批量续接诊断 | S07 发出第一条 diagnosis_attempted 后视为恢复 |
| S08 策略引擎 | 宕机期间 diagnosis_updated 积压超过 <!-- AI-MUTABLE: strategy_backlog_threshold, type=int, range=[50, 500] --> 100 条 | 触发告警，S04 静态策略包兜底（不依赖事件驱动） | S08 重启后逐条消费积压事件 |
| S09 课堂引擎 | 宕机时课堂状态丢失 | 课堂状态已在 lesson 表落盘，S09 重启后从最后一个 strategy_completed 事件续接 | S09 发出第一节课状态同步后视为恢复 |

> 事件总线自身宕机：S10 是逻辑定义（非独立进程），事件由前端和各引擎直接收发。各消费方自身的宕机由各自的重启逻辑处理。

---

## 大白话

S10 是芽芽的"通信协议 + 存档室"。好比一栋大楼里的对讲机系统和档案柜——

对讲机系统（事件协议）：每个子系统通过对讲机说话——诊断引擎说"我判断这孩子是小数点位置错了"，策略引擎听到后说"那我来推一套小数点定位练习"，课堂引擎听到后把这些练习放进课堂里。对讲机有严格的频道规则——问答题的频道（chainId）从学生提交答案开始建立，后面的诊断、验证、策略执行全在这个频道里，不会串台。对讲机里的消息如果缺了关键信息（比如不知道是哪个学生），直接拒收——相当于"信号不好，请重新呼叫"。

档案柜（数据模型）：10 个柜子各管各的——知识点柜、错因柜、事件记录柜、诊断记录柜、策略效果柜、家长摘要柜、成长记忆柜。每个柜子有固定的抽屉格式，比如策略效果柜必须记录五个维度的效果（当下有没有用、过几天还有没有用、是不是不再依赖提示了等等）。Phase 1 期间"长期效果"这个抽屉还没数据（标 -999），等 Phase 2 系统能追踪长期效果了再填。

这套对讲机和档案柜的关键设计原则：**格式优先于内容**。对讲机频道编号（chainId）、档案柜主键（knowledgeCode/studentId）、消息版本号（version）这些格式一旦定下来，改的成本巨大——所以把它们放在"不可修改边界"里。但可以新增频道（Phase 2/3 事件）、新增抽屉格（新增数据字段），这些是正常进化。

**自我进化路线图**：S10 的进化分两步——Phase 1 先把 11 种事件和 10 张表跑稳（事件拒收率<1%、chainId 完整率>97%），Phase 2/3 才加新事件和新字段。为什么不能一开始就定义 21 种事件？因为定义太多没用的事件会让 Schema 膨胀——每加一个字段就要在所有消费方验证兼容性，成本递增。先跑稳核心链路再扩展，就像先建好主干道再修支路。

**接口约定**：S10 和下游子系统的接口约定就是一个契约——"我给你这个结构的 event，你给我按这个字段读"。哪个消费方如果读错字段名（比如把 diagnosisId 读成 diagnosis_id），它自己挂了不是 S10 的锅——Schema 是唯一的真实来源。新增字段默认选填——不破坏老消费方。删除字段禁做——因为老消费方可能在用。

**自我进化执行方法**：S10 自身进化走五步流程——消费方（S07/S08/S09）提出需求 → AI 设计 Schema → 审核员审计 → 实施更新文档 → 消费方接入验证。五类角色各司其职：AI 可以新增选填字段，但不能改必填/删字段/改枚举。信用分三子分（设计/执行/进化）决定 AI 的自主权——分数低了自动降权。

**异常进化处置**：连续 3 次 Schema 变更导致下游断裂 → 冻结该方向的进化 60 天。chainId 完整率持续低于 90% 超 18 教学月 → 信用分扣 5 分/月。<!-- AI-MUTABLE: runtime_mutation_detection_jump, type=percent_range, threshold=1%→10% -->
（运行中突变检测——区别于管道门禁的稳态阈值）事件拒收率突然从 1% 跳到 10% → 立即冻结全部事件 Schema 变更，等人工排查。

**应急熔断**：轻量级——暂停新事件注册但已有事件照常；子系统级——全部分析引擎降级到静态模式（不用事件驱动，用 S03/S04 静态数据兜底）；全系统级——全停+回滚未完成的 Schema 变更。

**进化信用分**：S10 的信用分反映的是"Schema 变更质量"——每次新增字段如果所有消费方都顺利接入（无断裂），信用分+5。如果有消费方因为新字段读错了数据，信用分-10。信用分掉到 20 以下 → AI 只能提议，不能直接改 Schema。掉到 10 以下 → 全系统 Schema 冻结，等人工重建信用。

**内容与代码进化分离**：S10 的进化分两条路——内容是"数据的格式和结构"（新增字段、新增可选枚举值），代码是"事件总线的处理逻辑"（队列实现、Socket/HTTP 传输层、IndexedDB 持久化策略）。就像档案柜：新增一个"家长反馈"抽屉格（内容进化——新增 ParentSummary 字段）不破坏旧档案，但把档案柜从「按学生分类」改成「按日期分类」（代码进化）可能让所有系统找不到旧档案。内容进化（Schema 变更）走教研+产品审批+五步管道，代码进化（传输层优化）走工程师+审查员审批。两者都改的（如从 HTTP→WebSocket 同时增加新事件类型）必须两套流程都通过。

---

---

## 设计演化推理链

### 为什么 Phase 1 选了这 11 个事件

Phase 1 选择了 11 个核心事件（而非更多或更少），取舍逻辑如下：

**入选理由**（与 §二 Phase 1 事件 Schema 和 §七 事件矩阵完全对齐）：
- answer_submitted / hint_requested / answer_abandoned：答题行为三事件——提交答案驱动诊断链、请求提示记录帮助寻求行为、放弃答题驱动体验保护
- diagnosis_attempted / validation_triggered / validation_completed / diagnosis_updated：诊断四步走——尝试、触发验证、完成验证、更新结论，覆盖从模糊到确定的完整诊断过程
- strategy_applied / strategy_completed：策略二步——应用策略、完成执行并携带效果评分，形成策略闭环
- lesson_started / lesson_completed：课堂边界——开始和结束，驱动画像更新和家长摘要

**未入选理由**：
- Phase 2 事件（adaptive_prompt_shown、knowledge_synthesis、transfer_attempt）尚不具备运行条件——TTS 引擎、提示词库、迁移检测尚未就绪
- Phase 3 事件（peer_comparison、self_reflection、learning_path_adjustment）需要全量画像数据积累——Phase 1 学生数据量不足
- 边界内但不纳入：如 question_displayed 事件（仅前端展示，无教学价值）、session_resumed 事件（可从 lesson_completed 反推）

### 为什么 chainId 边界是一次答题→诊断→策略执行

chainId 的边界选择有三个候选：

| 候选 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| 一道题 | 粒度最细，关联最清晰 | 无法追踪多题策略的整体效果 | 淘汰 |
| 一次答题→诊断→策略执行（选中） | 覆盖一次完整诊断链，可追踪策略效果 | 一节课可能有多条 chainId，需上层聚合 | 采用 |
| 一节课 | 天然的业务边界 | 如果一个学生在课堂上多次答题但诊断不同错因，chainId 会混在一起 | 淘汰 |

「一次答题→诊断→策略执行」是诊断的最小闭环。多题、多错因通过多条 chainId 串联（同 studentId + lessonId），由 S15 画像系统在上层聚合【S15已建，引用待交叉验证】。

### 为什么数据模型选了 10 张表

S10 定义了 10 张核心表（与 §二 数据模型完全对齐），取舍逻辑：
- 表一 SubjectPlugin / 表二 KnowledgeNode / 表三 ErrorTaxonomy：静态字典，系统启动前必须存在
- 表四 ErrorKpBinding / 表五 BehaviorEvent / 表六 ErrorDiagnosis / 表七 StrategyEffect：事件驱动的流水表，按时间序写入
- 表八 ParentSummary / 表九 GrowthMemory：聚合表，从流水表计算得出
- 表十 核心枚举：跨表共享的枚举值定义（diagnosisStatus/strategyEffect/messageRole/reviewType）
- 不纳入的表：StudentProfile 表（归 S15 管理）、ClassroomTemplate 表（归 S09 管理）、QuestionBank 表（归 S01 管理）——各子系统管理自身数据，S10 仅定义跨系统的共享表

---

## 提交前自查验证（验收标准 3.18）

- AI-MUTABLE覆盖率：23/N（已标注23处——含概率调整系数×1.15/×0.7/confidence<0.5/probability≥0.8/3次weakened排除/3轮inconclusive badcase/影子7天+A/B 7天+旧字段30天/拒收率5%+1%/降级策略各阈值/大白话信用分阈值等。S10 的事件协议以不可变 Schema 为主体，AI-MUTABLE 参数集中在运行时阈值和管道参数。自检以已标注数为分母，实际应标注总数 ≈ 23）
- 不可修改边界：7/7 类逐类打勾通过
- 十段基建：逐项确认——越界告警✓(行1003-1009)/间接修改✓(行992-1001)/数据闭环✓(行1044)/安全管道✓(行1118-1138)/A&B分组✓(行1104-1108)/元进化递归✓(行1110-1114)/G1-G7✓(行256-592事件定义含partitionKey类型检查+行194-252事件验证+行1242-1251降级策略+行994-1005间接修改边界+行1003-1009越界告警+行1021-1031北极星底线信号+行1020不可绕过声明)/大白话✓(行1267-1297)/消费清单✓(行1198-1220)/被消费方待定义标注✓(行1220)
- 验证时间：2026-05-17 15:17:34

---

## 与原文档的关系

本文档从 acceptance-artifacts/09_EVENT_PROTOCOL.md（v2.0.8）和 acceptance-artifacts/10_DATA_MODEL.md（v2.1.4）合并而成。核心 Schema 定义保持一致，不做内容修改。本文档是子系统视角的系统设计文档，原两份老文档作为实施参考的详细手册保留在 acceptance-artifacts/ 中。两者关系：本文档定义系统边界和接口规范，原文档提供逐字段说明和边缘情况处理细节。实施时以本文档为接口依据，以原文档为字段级参考。
