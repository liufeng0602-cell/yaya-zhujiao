# 09 行为事件协议 v2.0.8

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | - | 初始版本：15 个事件命名 + 4 个事件样例 |
| 2.0 | 2026-05-14 | 全部事件定义完整 Schema；引入 chainId 串联诊断链路；必填字段强制校验；新增 version 字段；新增 diagnosis_attempted 事件；lesson_started.knowledgeCode 改为 knowledgeCodes 数组 |
| 2.0.1 | 2026-05-14 | 地狱自检修复：chainId 鸡生蛋问题（预生成规则）；mainHypothesis 补 confidence 字段；答对/放弃链路规则（1.6）；新增 answer_abandoned 事件（现 20 个事件）；lessonId 补充到 diagnosis_attempted/strategy_applied/strategy_completed；strategy_completed 补 diagnosisId；概率调整规则澄清（weakened vs inconclusive）；概率样例数学校正；1.5 去掉"尽量"改为必填规则表；5.1/5.2 优先级明确；probability/confidence 区别解释；triggerReason 按 triggerSource 格式约束；difficulty/level 分工说明（1.7）；effectScore 计分方明确；activeMs Phase 过渡规则；lesson_completed 补 byKnowledgeCode 拆分；事件矩阵消费方补全；章节 8 输入对齐 11 号文档 |
| 2.0.8 | 2026-05-15 03:31 | 地狱级交叉审查：(1)§8.3 家长摘要输入事件列表修正——原列四事件（lesson_started/lesson_completed/diagnosis_attempted/strategy_completed）与 13 号 v2.6.1 §9 接口表不一致（缺 answer_submitted 事件 1、缺 strategy_applied 事件 9、diagnosis_attempted 应为 diagnosis_updated），改为对齐 13 号实际消费的 5 事件（answer_submitted/lesson_completed/diagnosis_updated/strategy_applied/strategy_completed） |
| 2.0.2 | 2026-05-14 | 新增 diagnosis_updated 事件（事件 8）：多轮验证过程中每轮验证完成后诊断引擎发出，携带更新后的假设集、status、diagnosisStatus。解耦策略引擎介入时机（读 diagnosis_updated 而非等 diagnosis_attempted）。事件总数从 20 升至 21。事件 8→11 重编号（strategy_applied→9, strategy_completed→10, answer_abandoned→11），Phase 2/3 事件 11-20→12-21。8.1 节验证链路更新 |
| 2.0.3 | 2026-05-14 18:37 | 地狱自检修复 - 数据底座对齐：(1)所有 knowledgeCode 样例从语义编码格式（M5S1-DECIMAL-MUL-003）修正为数字编码格式（M5S1-3），对齐真实 knowledge.json 数据；(2)validation_triggered 的 hypothesisType 枚举对齐 error_taxonomy.json：migration_failure→transfer_failure、key_info_missed→info_omission，补全 comprehension_bias / expression_format_error，从 8 个增至完整 10 个 L1 错因；(3)文件迁移至 acceptance-artifacts 目录 |
| 2.0.4 | 2026-05-14 19:05 | 地狱自检修复：(1)1.2 节链路图补 diagnosis_updated（validation_completed→strategy_applied 之间）；(2)lesson_completed 的 activeMs 增加异常值校验（<0 或 >7200000 标记无效）；(3)事件矩阵 strategy_applied 消费方补全（策略引擎+家长摘要）；(4)hint_requested 增加 previousHintLevel 字段区分求助模式；(5)answer_submitted 增加 context.activeStrategyPack 解决策略执行期间答题归属；(6)所有事件 version 字段从 "2.0" 升级到 "2.0.3"，同主版本内兼容变更不拒收 |
| 2.0.5 | 2026-05-14 19:12 | 地狱自检修复：(1)activeStrategyPack 增加前端时序规则——以 strategy_applied/completed 时间窗口为主判断，activeStrategyPack 仅作为校验辅助；(2)previousHintLevel 增加降级求助模式（低于上次=提示理解困难）；(3)activeMs 异常值校验增加 Phase 2 历史数据重新校验规则；(4)diagnosis_updated 消费方补全诊断引擎自身（溯源决策与状态机推进） |
| 2.0.6 | 2026-05-14 19:28 | 地狱自检修复：(1)1.3 节新增 version 升级规则——事件样例 version 值为最后一次 Schema 结构变更的版本号，纯文本说明修改不触发升级；(2)activeMs Phase 2 上限 4 小时增加来源说明（idle_timeout 精确扣除后覆盖长时间沉浸式学习场景）；(3)diagnosis_attempted 的 status 字段说明增加语义差异标注——open/inconclusive 出现在 diagnosis_attempted 中，validated/closed 只在 diagnosis_updated 中出现 |
| 2.0.7 | 2026-05-14 19:52 | 10 号文档交叉审计修复（P2）：diagnosis_updated 的 diagnosisStatus 枚举从 4 态扩展为六态 full——补 confirmed_with_reservation（有保留确诊，对齐 11 号诊断引擎 v2.3 的满 3 轮 0.5-0.8 输出；策略引擎见此态只发轻量策略，不发强策略）和 traced（溯源切入态，对齐 11 号溯源流程输出） |

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

这是芽芽助教产品文档集的第 09 号文件，定义 11 个行为事件的完整 Schema、链式追踪规则（chainId）、版本兼容规则和消费方矩阵。它回答「系统各模块怎么对话」——前端、诊断引擎、策略引擎、画像系统、家长摘要全通过这套事件协议通信。本文档是所有引擎模块的接口规范，是整个系统的通信底座。

## 一、通用规则

### 1.1 必填字段

每个事件 Schema 中标注"必填"的字段，缺一不可。缺任一必填字段，事件拒收，返回错误码：

```
EVENT_MISSING_REQUIRED_FIELD
```

上游（前端/网关）补全后重传。

特殊情况：
- **studentId 缺失永不接受**。没有 studentId，事件无法归属到任何学生画像。
- **knowledgeCode 缺失时**，允许前端从 questionId 反查 knowledgeCode 后补全重传。仅 knowledgeCode 有此例外。

### 1.2 chainId —— 诊断链路串联

所有属于同一条诊断链路的事件，共享同一个 `chainId`。

chainId 的生成规则：
- chainId 的边界是"一次答题→诊断→策略执行"，不是"一节课"。同一节课内不同题目对应不同 chainId。
- **正常流程**：chainId 在 `answer_submitted` 事件中首次生成。格式：`chain_{studentId}_{timestamp_ms}` 或 UUID v4，由前端生成。
- **提前请求提示**：学生可能在提交答案之前先请求提示（hint_requested 先于 answer_submitted）。此时前端为这道题预生成 chainId（格式同上），hint_requested 携带该预生成的 chainId。后续 answer_submitted 复用同一 chainId。若 hint_requested 发出后学生放弃答题（无 answer_submitted），该 chainId 标记为 orphan，24 小时后清理。
- **答对不诊断**：如果 answer_submitted.isCorrect = true，且系统判定无需诊断（见 1.6 节规则），则 chainId 仍然生成，但不会产生 diagnosis_attempted 及后续事件。该 chainId 作为"正常作答链"归档，不标记为 incomplete。
- **学生放弃答题**：题目展示后，若学生在 N 秒内（默认 600 秒）既未提交答案也未请求提示，前端自动发送 `answer_abandoned` 事件（Phase 1 新增）。放弃的题目不进入诊断链路。
- 后续所有事件（diagnosis_attempted、validation_triggered、validation_completed、diagnosis_updated、strategy_applied、strategy_completed 以及同一道题上的 hint_requested）必须携带同一个 chainId。

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

### 1.3 version —— 协议版本

每条事件携带 `"version": "2.0.3"`。

引擎读取事件时校验 version 字段：
- **同主版本兼容**：2.0.x 之间的版本差异为兼容变更（次字段增减、枚举扩展），引擎正常处理，不拒收。
- **跨主版本不兼容**：如 1.x 事件发到 2.x 引擎，跳过该事件，记录 WARN 日志，不崩溃。
- 版本字段缺失：按 1.0 协议尝试解析，失败则跳过。

**事件样例中 version 的升级规则**：事件样例中的 version 值为最后一次 Schema 结构变更的版本号。所谓 Schema 结构变更指：字段增删、字段类型修改、枚举值增删改。以下变更不触发 version 升级：字段描述文字修改、过渡规则补充、消费方列表更新、校验规则调整等纯文本说明修改。按此规则，当前 v2.0.3 之后的所有修改均为纯文本说明修改，事件样例 version 保持 "2.0.3"。

### 1.4 timestamp —— 时间戳

每条事件携带 ISO 8601 格式时间戳，精确到毫秒：

```
"timestamp": "2026-05-14T10:23:05.872Z"
```

所有 timestamp 以 UTC 为准。前端负责在事件发送前打时间戳。

### 1.5 事件通用上下文字段

以下字段为所有事件的通用上下文。标注"必填"的字段缺一则事件拒收（见 1.1 节）。标注"选填"的字段各事件按需携带。

| 字段 | 类型 | 必填规则 | 说明 |
|------|------|----------|------|
| studentId | string | **所有事件必填** | 学生唯一标识 |
| subject | string | 选填 | 学科（math/chinese/english 等） |
| grade | string | 选填 | 年级（5/6） |
| stage | string | 选填 | 学段（primary/middle/high） |
| textbookVersion | string | 选填 | 教材版本（PEP） |
| knowledgeCode | string | 选填（可从 questionId 反查） | 知识点编码 |
| questionType | string | 选填 | 题型 |
| difficulty | number | 选填 | 难度（0-1） |
| strategyPack | string | 选填 | 当前使用的策略包 |
| stateCard | string | 选填 | 状态卡（easy/challenge/solo/companion） |
| lessonId | string | **课堂类事件必填** | 所属课堂。answer_submitted/hint_requested/lesson_started/lesson_completed 必填；diagnosis_attempted/strategy_applied/strategy_completed 选填但强烈建议携带 |
| chainId | string | **诊断链路事件必填** | 诊断链路 ID |
| version | string | **所有事件必填** | 协议版本 |
| timestamp | string | **所有事件必填** | ISO 8601 时间戳 |

> 注意：各事件 Schema 中的必填声明为最终权威。上表为通用指引，如与 Schema 冲突，以 Schema 为准。

### 1.6 诊断链路启动规则

诊断链路（chainId 生成 → diagnosis_attempted → ...）的启动条件：

- **答错启动**：answer_submitted.isCorrect = false 时，诊断引擎必须运行，生成 diagnosis_attempted。
- **答对跳过**：answer_submitted.isCorrect = true 时，默认不启动诊断。但以下例外必须启动：
  - answerTimeMs 异常长（超过该知识点历史均值的 3 倍标准差）
  - hintUsed = true（答对但用了提示，需确认是否真正掌握）
  - modifyCount ≥ 3（反复修改后才答对，存在"蒙对"可能）
- **放弃跳过**：answer_abandoned 事件不启动诊断链路。

### 1.7 difficulty 与 knowledgeLevel 的关系

answer_submitted 携带两个难度信号：

- `difficulty`（0-1）：题目本身的难度系数，由题库定义，表示这道题在所属知识点内的相对难度。
- knowledgeCode 对应的 `level`（A/B/C）：知识点的认知层级（A=了解、B=理解、C=掌握），由知识图谱定义，表示这个知识点本身的深度要求。

诊断引擎使用 difficulty 做"这道题对学生来说多难"的判断（结合答题时长）。策略引擎使用 level 做"这个知识点本身要求多高"的判断（决定策略强度）。两者不互相替代，各自独立使用。

---

### 1.8 knowledgeCode 编码格式

本文档所有 knowledgeCode 样例采用真实数据的数字编码格式：`{年级}{册}{单元}-{序号}`。例如 `M5S1-3` 表示五年级上册第一单元第 3 号知识点（小数乘小数算理）。

实际数据中 knowledgeCode 见 `knowledge.json` 文件的 `knowledgeCode` 字段。文档中的样例码（如 `M5S1-3`、`M5S1-4`）仅供示意，真实编码以数据文件为准。

---

## 二、Phase 1 事件（完整 Schema）

以下 11 个事件为诊断引擎和策略引擎启动的必要输入。Schema 完整定义，可直接用于实现。

### 事件 1：answer_submitted

触发时机：学生在课堂上提交一道题的答案。

这是整个系统最重要的输入事件。诊断引擎以此启动，策略引擎以此判断效果。

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

字段说明：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| event | 是 | string | 固定值 "answer_submitted" |
| version | 是 | string | 固定值 "2.0.3" |
| chainId | 是 | string | 前端生成，本次诊断链起点。格式 chain_{studentId}_{ts} 或 UUID v4 |
| studentId | 是 | string | 学生唯一标识 |
| questionId | 是 | string | 题目唯一标识 |
| knowledgeCode | 是 | string | 知识点编码。缺失时从 questionId 反查补全 |
| questionType | 是 | string | 题型（calculation/word_problem/choice/fill_blank 等） |
| difficulty | 否 | number | 难度系数 0-1 |
| answer.studentResponse | 是 | string | 学生提交的最终答案 |
| answer.isCorrect | 是 | boolean | 答案是否正确 |
| answer.errorOption | 否 | string | 选择题选错时，记录错误选项 |
| answer.scratchpadUsed | 否 | boolean | 是否使用了草稿功能 |
| answer.steps | 否 | array | 解题步骤（如果能采集到）。每步含 stepNumber/input/output/isCorrect/errorDetail |
| behavior.answerTimeMs | 是 | number | 从题目展示到提交答案的毫秒数 |
| behavior.modifyCount | 否 | number | 修改了几次答案 |
| behavior.hintUsed | 是 | boolean | 是否在作答前使用过提示 |
| behavior.hintLevel | 否 | number | 如果用过提示，提示层级（1-3） |
| context.lessonId | 是 | string | 所属课堂 ID |
| context.strategyPack | 否 | string | 当前正在使用的策略包 |
| context.stateCard | 否 | string | 学生上课前选的状态卡 |
| context.activeStrategyPack | 否 | string | 学生作答时正在执行的活跃策略包编码。如果此时没有活跃策略（如诊断前），值为 null。前端应在收到 strategy_applied 事件后立即更新 activeStrategyPack 状态，在 strategy_completed 后清除。**时序规则**：如果 strategy_applied 事件还在网络传输中而学生已开始作答，允许 activeStrategyPack 为 null 或上一轮策略包编码。策略引擎在计算 effectScore 时，以 strategy_applied.timestamp 和 strategy_completed.timestamp 为时间窗口主判断依据，activeStrategyPack 仅作为校验辅助——两者冲突时以时间窗口为准 |
| timestamp | 是 | string | ISO 8601 UTC 时间戳 |

**answerTimeMs 的计时来源说明**：该值由前端在题目渲染瞬间启动本地计时器，学生提交答案时读取。不依赖 question_shown 事件（Phase 2 上线）。Phase 2 上线 question_shown 后，该事件携带相同 questionId 和 timestamp_start，用于事后校验 answerTimeMs 准确性，不用于实时计时。

---

### 事件 2：hint_requested

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

字段说明：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| event | 是 | string | 固定值 "hint_requested" |
| version | 是 | string | 固定值 "2.0.3" |
| chainId | 是 | string | 复用当前题目的诊断链 ID |
| studentId | 是 | string | 学生唯一标识 |
| questionId | 是 | string | 题目唯一标识 |
| knowledgeCode | 是 | string | 知识点编码 |
| hint.level | 是 | number | 提示层级（1=方向指引，2=关键步骤，3=完整解法） |
| hint.type | 是 | string | 提示类型（general_guidance/key_step/full_solution/concept_hint/error_hint） |
| hint.requestedAfterMs | 是 | number | 看到题目后多久请求提示（毫秒） |
| hint.previousHintLevel | 否 | number | 同一 chainId 下上一次 hint_requested 的 level。首次请求提示时为 null。消费方可直接判断求助模式：与上次相同 = 卡在同一层（提示无效），高于上次 = 逐级升级（难度过高），低于上次 = 降级求助（高等级提示未能理解，退回更基础的引导，消费方将此模式视为"提示理解困难"，不同于"卡在同一层"的提示无效信号） |
| context.lessonId | 是 | string | 所属课堂 ID |
| context.attemptNumber | 否 | number | 这是第几次尝试（同一题目反复请求提示） |
| timestamp | 是 | string | ISO 8601 UTC 时间戳 |

---

### 事件 3：lesson_started

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
  "knowledgeCodes": [
    "M5S1-4",
    "M5S1-3"
  ],
  "strategyPack": "default",
  "stateCard": "challenge",
  "timestamp": "2026-05-14T10:00:00.000Z"
}
```

字段说明：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| event | 是 | string | 固定值 "lesson_started" |
| version | 是 | string | 固定值 "2.0.3" |
| studentId | 是 | string | 学生唯一标识 |
| lessonId | 是 | string | 课堂唯一标识 |
| subject | 是 | string | 学科 |
| grade | 是 | string | 年级 |
| stage | 是 | string | 学段 |
| textbookVersion | 是 | string | 教材版本 |
| knowledgeCodes | 是 | array | 本节课覆盖的知识点编码列表。**第一个元素为本课目标知识点**，后续为前置回顾/相关知识点。最少 1 个 |
| strategyPack | 否 | string | 初始策略包 |
| stateCard | 否 | string | 学生上课前选的状态卡 |
| timestamp | 是 | string | ISO 8601 UTC 时间戳 |

---

### 事件 4：lesson_completed

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
      {
        "knowledgeCode": "M5S1-4",
        "questionsAnswered": 5,
        "questionsCorrect": 4
      },
      {
        "knowledgeCode": "M5S1-3",
        "questionsAnswered": 3,
        "questionsCorrect": 2
      }
    ]
  },
  "timestamp": "2026-05-14T10:25:00.000Z"
}
```

字段说明：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| event | 是 | string | 固定值 "lesson_completed" |
| version | 是 | string | 固定值 "2.0.3" |
| studentId | 是 | string | 学生唯一标识 |
| lessonId | 是 | string | 课堂唯一标识 |
| completionStatus | 是 | string | completed / interrupted（学生主动退出）/ timeout（超时自动结束） |
| duration.totalMs | 是 | number | 从 lesson_started 到 lesson_completed 的总毫秒数 |
| duration.activeMs | 是 | number | 有效学习时长（扣除了 idle_timeout 和 lesson_paused 时段） |
| duration.pauses | 否 | number | 暂停次数（切到别的 App 后又回来） |
| duration.idleTimeouts | 否 | number | 空闲超时次数（超过 N 秒无操作） |
| outcome.questionsAnswered | 是 | number | 回答的题目总数 |
| outcome.questionsCorrect | 是 | number | 答对的题目数 |
| outcome.exitPoint | 否 | string | 如果未完成，记录退出的步骤/题目 |
| outcome.byKnowledgeCode | 否 | array | 按知识点拆分的答题统计。每项含 knowledgeCode/questionsAnswered/questionsCorrect。建议携带，以便画像系统按知识点评估正确率 |
| timestamp | 是 | string | ISO 8601 UTC 时间戳 |

**activeMs 的计算规则**：totalMs 减去所有 idle_timeout 时段和 lesson_paused 时段。Phase 1 尚未上线 idle_timeout 和 lesson_paused 事件时，activeMs = totalMs。

**activeMs 异常值校验**：后端入库前校验 activeMs。若 activeMs < 0 或 activeMs > 7200000（2 小时），标记 `activeMsValid: false`，原值仍入库但该条记录不参与画像系统的专注度计算。Phase 2 上线 idle_timeout 后，上限调整为 4 小时。Phase 2 上限调整为 4 小时的原因：引入 idle_timeout 后，totalMs 中的无效时段被精确扣除，activeMs 更接近真实学习时长。长时间沉浸式学习（如周末集中复习）的 activeMs 可达 3-4 小时，4 小时上限可覆盖 99% 以上的真实学习场景。

**Phase 1 → Phase 2 activeMs 历史数据重新校验规则**：Phase 2 上线时（上限从 2 小时变为 4 小时），对 Phase 1 期间标记为 `activeMsValid: false` 且 activeMs 在 7200001-14400000（含）之间的历史记录，自动重新标记为 `activeMsValid: true`，纳入画像系统计算。标记为 `activeMsEstimated` 的 Phase 1 记录不受此规则影响（重新校验只改 valid 标记，不改 estimated 标记）。

**Phase 1 → Phase 2 过渡规则**：Phase 2 上线计时事件后，需要对 Phase 1 期间产生的历史 lesson_completed 事件打标记 `"activeMsEstimated": true`。画像系统在比较跨阶段数据时，不将 Phase 1（estimated）和 Phase 2（measured）的 activeMs 直接对比，避免因统计口径变化导致"该学生 Phase 1 更专注"的误判。Phase 1 数据仅用于同阶段内比较。

---

### 事件 5：diagnosis_attempted

触发时机：诊断引擎完成一次错因诊断，生成假设集。

这是 v2.0 新增事件。原来是 answer_submitted 直接跳到 validation_triggered，中间"完成了诊断"这一步没有记录。加入此事件后链路变成六环咬合。

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

字段说明：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| event | 是 | string | 固定值 "diagnosis_attempted" |
| version | 是 | string | 固定值 "2.0.3" |
| chainId | 是 | string | 复用本次诊断链 ID |
| studentId | 是 | string | 学生唯一标识 |
| diagnosisId | 是 | string | 本次诊断的唯一标识 |
| sourceQuestionId | 是 | string | 触发诊断的题目 ID（对应 answer_submitted 的 questionId） |
| knowledgeCode | 是 | string | 知识点编码 |
| lessonId | 否 | string | 所属课堂 ID（建议携带，便于画像系统按课堂聚合诊断结果） |
| hypotheses | 是 | array | 错因假设集，按概率降序排列 |
| hypotheses[].hypothesisId | 是 | string | 假设 ID |
| hypotheses[].errorCode | 是 | string | 错因编码（对应 error_taxonomy.json） |
| hypotheses[].probability | 是 | number | 概率 0-1 |
| hypotheses[].confidence | 是 | number | 置信度 0-1 |
| hypotheses[].rank | 是 | number | 排名（1 起始） |
| mainHypothesis | 是 | object | 主假设（概率最高的假设） |
| mainHypothesis.hypothesisId | 是 | string | 主假设 ID |
| mainHypothesis.errorCode | 是 | string | 主假设错因编码 |
| mainHypothesis.probability | 是 | number | 主假设概率（0-1） |
| mainHypothesis.confidence | 是 | number | 主假设置信度（0-1） |
| status | 是 | string | open（待验证）/ validated（已验证）/ inconclusive（无法判断）/ closed（已关闭）。**注意**：diagnosis_attempted 的 status 通常为 open（待验证），仅当 mainHypothesis.confidence < 0.5 时直接设为 inconclusive。validated 和 closed 只在 diagnosis_updated 中出现，不出现在 diagnosis_attempted 中。两个事件的 status 枚举值相同但语义不同：diagnosis_attempted.status 表初次诊断的初始状态，diagnosis_updated.status 表验证后的更新状态 |
| method | 否 | string | 诊断方法（rule_engine / decision_tree / ai_assisted） |
| timestamp | 是 | string | ISO 8601 UTC 时间戳 |

**probability 与 confidence 的区别**：
- **probability**（概率）：这个假设为真的可能性。验证题答对时上升，答错时下降。是诊断引擎对外输出的"判断结果"。
- **confidence**（置信度）：诊断引擎对自己这次判断的把握程度。即使概率高，如果证据不足（如只有一道题、行为数据稀少），置信度可能仍低。
- 使用规则：confidence < 0.5 时，不能触发验证题（改为降低难度或分步提示）。probability 无论高低都可以触发验证（只要 confidence ≥ 0.5）。

**低置信度规则**：当 mainHypothesis.confidence < 0.5 时，status 应设为 "inconclusive"，不触发验证题，改为降低难度或分步提示。低置信度错因不能触发强策略。

---

### 事件 6：validation_triggered

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

字段说明：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| event | 是 | string | 固定值 "validation_triggered" |
| version | 是 | string | 固定值 "2.0.3" |
| chainId | 是 | string | 复用本次诊断链 ID |
| studentId | 是 | string | 学生唯一标识 |
| diagnosisId | 是 | string | 触发验证的诊断 ID（对应 diagnosis_attempted.diagnosisId） |
| hypothesisId | 是 | string | 正在验证的假设 ID |
| sourceQuestionId | 是 | string | 原始错题 ID |
| validationQuestionId | 是 | string | 验证题 ID |
| knowledgeCode | 是 | string | 知识点编码 |
|| hypothesisType | 是 | string | 假设类型（concept_confusion / calculation_error / prerequisite_gap / transfer_failure / question_type_unfamiliar / memory_retrieval_failure / info_omission / strategy_missing / comprehension_bias / expression_format_error）。共 10 类，对应 error_taxonomy.json 的 L1 通用错因 |
| validationType | 是 | string | 验证动作类型（concept_visual_check / decimal_place_visual_check / prerequisite_question / variant_question / step_by_step_check / memory_cue_check / key_info_highlight / strategy_scaffold） |
| validationRound | 是 | number | 验证轮次（同一假设最多 3 轮验证，3 轮仍 inconclusive 则标记并记录 badcase） |
| previousValidationId | 否 | string | 上一轮验证的 ID（第 2 轮及以后） |
| timestamp | 是 | string | ISO 8601 UTC 时间戳 |

---

### 事件 7：validation_completed

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

字段说明：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| event | 是 | string | 固定值 "validation_completed" |
| version | 是 | string | 固定值 "2.0.3" |
| chainId | 是 | string | 复用本次诊断链 ID |
| studentId | 是 | string | 学生唯一标识 |
| diagnosisId | 是 | string | 诊断 ID |
| hypothesisId | 是 | string | 正在验证的假设 ID |
| validationQuestionId | 是 | string | 验证题 ID |
| knowledgeCode | 是 | string | 知识点编码 |
| validationRound | 是 | number | 验证轮次 |
| isCorrect | 是 | boolean | 验证题是否答对 |
| studentResponse | 否 | string | 学生答案 |
| correctAnswer | 否 | string | 正确答案 |
| result | 是 | string | supported（验证题答对，假设概率上升）/ weakened（验证题答错，假设概率下降）/ inconclusive（无法判断） |
| probabilityBefore | 是 | number | 验证前的假设概率 |
| probabilityAfter | 是 | number | 验证后的假设概率 |
| timestamp | 是 | string | ISO 8601 UTC 时间戳 |

**概率调整规则**（详见 11_DIAGNOSIS_ENGINE.md）：
- 验证题做对 → 假设概率 × 1.15（result = "supported"）
- 验证题做错 → 假设概率 × 0.7（result = "weakened"）
- 验证题结果模糊 → 假设概率不变（result = "inconclusive"）
- 同一假设连续 3 次 result="weakened"（连错 3 道验证题）→ 确诊为判伪（confirmed），该假设被排除，诊断引擎切换至下一假设或重新诊断
- 同一假设验证 3 轮仍 result="inconclusive"（无法判断）→ 标记 badcase，降低难度，重新观察。inconclusive 与 weakened 是不同的结论——前者是"系统没法判断"，后者是"判断了但学生做错了"
- 示例：假设概率 0.60，验证题做对 → 0.60 × 1.15 = 0.69（supported）。验证题做错 → 0.60 × 0.7 = 0.42（weakened）。

---

### 事件 8：diagnosis_updated

这是 v2.0.2 新增事件。多轮验证过程中，每轮验证完成后诊断引擎发出此事件，携带更新后的假设集和状态。解决了原来 diagnosis_attempted 只发一次、验证过程中状态变化无处记录的缺口。

触发时机：诊断引擎收到 validation_completed 事件后，更新假设概率，发出此事件。

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
    {
      "hypothesisId": "h1",
      "errorCode": "decimal_point_position_error",
      "probability": 0.71,
      "confidence": 0.80,
      "rank": 1
    }
  ],
  "mainHypothesis": {
    "hypothesisId": "h1",
    "errorCode": "decimal_point_position_error",
    "probability": 0.71,
    "confidence": 0.80
  },
  "status": "validated",
  "diagnosisStatus": "validated",
  "validationRound": 2,
  "triggerResult": "supported",
  "method": "rule_engine",
  "timestamp": "2026-05-14T10:23:56.000Z"
}
```

字段说明：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| event | 是 | string | 固定值 "diagnosis_updated" |
| version | 是 | string | 固定值 "2.0.3" |
| chainId | 是 | string | 复用本次诊断链 ID |
| studentId | 是 | string | 学生唯一标识 |
| diagnosisId | 是 | string | 诊断 ID（与初始 diagnosis_attempted 一致） |
| knowledgeCode | 是 | string | 知识点编码 |
| lessonId | 否 | string | 所属课堂 ID |
| hypotheses | 是 | array | 更新后的假设集，按概率降序排列 |
| hypotheses[].hypothesisId | 是 | string | 假设 ID |
| hypotheses[].errorCode | 是 | string | 错因编码 |
| hypotheses[].probability | 是 | number | 更新后的概率 0-1 |
| hypotheses[].confidence | 是 | number | 更新后的置信度 0-1 |
| hypotheses[].rank | 是 | number | 排名 |
| mainHypothesis | 是 | object | 更新后的主假设 |
| mainHypothesis.hypothesisId | 是 | string | 主假设 ID |
| mainHypothesis.errorCode | 是 | string | 主假设错因编码 |
| mainHypothesis.probability | 是 | number | 主假设概率 |
| mainHypothesis.confidence | 是 | number | 主假设置信度 |
| status | 是 | string | open（继续验证）/ validated（确诊）/ closed（已排除）/ inconclusive（无法判断） |
| diagnosisStatus | 是 | string | confirmed（假设被验证确认，prob≥0.85）/ confirmed_with_reservation（有保留确诊，满 3 轮 prob 在 0.5-0.8，策略引擎见此态只发轻量策略）/ excluded（假设被排除）/ in_progress（验证未完成，继续）/ inconclusive（证据不足无法判断）/ traced（已切入溯源，诊断引擎正在追溯前置知识点的错因根源） |
| validationRound | 是 | number | 当前验证轮次（1-3） |
| triggerResult | 是 | string | 本轮触发更新的验证结果：supported / weakened / inconclusive（来自 validation_completed.result） |
| method | 否 | string | 诊断方法（rule_engine / decision_tree / ai_assisted） |
| timestamp | 是 | string | ISO 8601 UTC 时间戳 |

**status 与 diagnosisStatus 的对照（六态）**：

| status | diagnosisStatus | 含义 | 后续动作 |
|--------|----------------|------|----------|
| open | in_progress | 验证中 | 继续下一轮 validation_triggered |
| validated | confirmed | 确诊（prob≥0.85） | 停止验证，策略引擎介入，允许发强策略 |
| validated | confirmed_with_reservation | 有保留确诊（满 3 轮 prob 在 0.5-0.8） | 策略引擎仅发轻量策略（基础巩固包），不发强策略（变式特训包、精准计算包等） |
| closed | excluded | 假设被排除 | 切换次高假设或走溯源 |
| open | traced | 已切入溯源 | 诊断引擎追溯前置知识点错因根源，暂停当知识点的验证 |
| inconclusive | inconclusive | 无法判断 | 降低难度，记录 badcase |

**多轮验证的 diagnosis_updated 发出规则**：
- 第 1 轮 validation_completed 收到后 → 发出 diagnosis_updated（diagnosisStatus=in_progress 或 confirmed 或 excluded）
- 第 2 轮 validation_completed 收到后 → 发出 diagnosis_updated
- 第 3 轮 validation_completed 收到后 → 发出 diagnosis_updated（必须收盘：confirmed 或 excluded 或 inconclusive）
- 验证提前确诊（probability ≥ 0.8）→ 立即发出 diagnosis_updated（diagnosisStatus=confirmed），不再继续

**消费方**：诊断引擎（溯源决策与状态机推进——当 diagnosisStatus=excluded 时判断切换次高假设还是走溯源）、策略引擎（读到 status=validated 时开始选择策略包，读到 status=closed 时等待下一个 diagnosis_updated）、画像系统（记录诊断过程）、家长摘要（记录诊断结论）

---

### 事件 9：strategy_applied

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

字段说明：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| event | 是 | string | 固定值 "strategy_applied" |
| version | 是 | string | 固定值 "2.0.3" |
| chainId | 是 | string | 复用本次诊断链 ID |
| studentId | 是 | string | 学生唯一标识 |
| knowledgeCode | 是 | string | 知识点编码 |
| diagnosisId | 是 | string | 触发策略的诊断 ID |
| lessonId | 否 | string | 所属课堂 ID（建议携带） |
| strategyPack | 是 | string | 策略包编码（对应 strategy_packs.json） |
| triggerReason | 是 | string | 触发原因，格式取决于 triggerSource：<br>- error_diagnosis → 错因编码（如 "decimal_point_position_error"）<br>- behavior_pattern → 行为模式标签（如 "fast_careless" / "hesitant_guesser" / "hint_dependent"）<br>- state_card → 状态卡名（如 "challenge" / "easy" / "solo" / "companion"）<br>- parent_goal → 家长目标（如 "foundation" / "sync" / "boost" / "advanced"）<br>- strategy_history → 历史策略编码（效能叠加触发） |
| triggerSource | 是 | string | 触发来源：error_diagnosis / behavior_pattern / state_card / parent_goal / strategy_history |
| confidenceBefore | 是 | number | 策略执行前的错因置信度 |
| params | 否 | object | 策略参数 |
| params.difficultyAdjustment | 否 | number | 难度调整（-1 到 +1） |
| params.questionCount | 否 | number | 推送题目数量 |
| params.hintLevel | 否 | number | 提示层级 |
| params.useTimer | 否 | boolean | 是否启用计时器 |
| timestamp | 是 | string | ISO 8601 UTC 时间戳 |

**调度优先级规则**（详见 08_STRATEGY_PACKS.md 和 12_STRATEGY_ENGINE.md）：
1. 体验保护（连续错误、学习能量低 → 能量恢复包 / 舒缓讲解包）
2. 主错因匹配（根据 diagnosis_attempted 的 mainHypothesis.errorCode 选择核心策略）
3. 学科专属策略（叠加数学专属策略包）
4. 偏好叠加（挑战、积分、表扬等）
5. 历史效能叠加（历史有效策略升权，低效策略降权）

---

### 事件 10：strategy_completed

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

字段说明：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| event | 是 | string | 固定值 "strategy_completed" |
| version | 是 | string | 固定值 "2.0.3" |
| chainId | 是 | string | 复用本次诊断链 ID |
| studentId | 是 | string | 学生唯一标识 |
| knowledgeCode | 是 | string | 知识点编码 |
| strategyPack | 是 | string | 策略包编码 |
| diagnosisId | 是 | string | 触发此策略的诊断 ID（对应 strategy_applied.diagnosisId） |
| lessonId | 否 | string | 所属课堂 ID（建议携带） |
| completionStatus | 是 | string | completed（正常完成）/ skipped（学生跳过）/ interrupted（被中断）/ timeout（超时） |
| durationMs | 是 | number | 策略执行时长（毫秒） |
| effectScore | 是 | number | 即时效果评分：-2（显著倒退）/ -1（轻微倒退）/ 0（无变化）/ 1（有改善）/ 2（显著改善）。由策略引擎根据策略执行期间学生的答题表现自动计算，前端不参与打分 |
| exitReason | 否 | string | 如果未完成，记录退出原因 |
| nextAction | 否 | string | 建议下一步动作（continue_lesson / back_to_lesson / recommend_break / switch_strategy / retry_diagnosis） |
| timestamp | 是 | string | ISO 8601 UTC 时间戳 |

**effectScore 的计算规则**：策略引擎收集策略执行期间该知识点下的所有 answer_submitted 事件，比较策略执行前后的正确率和答题时长变化。正确率提升 + 答题时长缩短 → 正值；正确率下降 → 负值；无显著变化 → 0。具体公式由 12_STRATEGY_ENGINE.md 定义。

**strategy_completed 和 StrategyEffect 的关系**：每个 strategy_completed 事件必须同时生成一条 StrategyEffect 记录（见 10_DATA_MODEL.md）。StrategyEffect 包含更详细的效果评估（当下有效/后续同类题提升/7天后仍有效/降低提示依赖/提高独立完成能力）。

---

### 事件 11：answer_abandoned

触发时机：题目展示后，学生在 N 秒内（默认 600 秒）既未提交答案也未请求提示，前端判定为放弃答题。

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

字段说明：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| event | 是 | string | 固定值 "answer_abandoned" |
| version | 是 | string | 固定值 "2.0.3" |
| chainId | 是 | string | 预生成的 chainId（如提前请求过提示则复用，否则新建） |
| studentId | 是 | string | 学生唯一标识 |
| questionId | 是 | string | 题目唯一标识 |
| knowledgeCode | 是 | string | 知识点编码 |
| questionType | 是 | string | 题型 |
| difficulty | 否 | number | 难度系数 0-1 |
| abandonReason | 是 | string | 放弃原因：timeout（超时未操作）/ exit_lesson（学生退出课堂）/ page_hidden（页面切到后台超过阈值） |
| timeOnScreenMs | 是 | number | 题目展示到放弃的毫秒数 |
| context.lessonId | 是 | string | 所属课堂 ID |
| context.strategyPack | 否 | string | 当前正在使用的策略包 |
| context.stateCard | 否 | string | 学生上课前选的状态卡 |
| timestamp | 是 | string | ISO 8601 UTC 时间戳 |

**放弃答题的处理**：answer_abandoned 不启动诊断链路（chainId 标记为 orphan）。画像系统记录该事件用于评估学生的参与度和放弃模式。如果同一节课内连续 3 次 answer_abandoned，触发策略引擎的体验保护逻辑（能量恢复包 / 舒缓讲解包）。

---

## 三、Phase 2 事件（Schema 后续补全）

以下事件在诊断引擎和策略引擎稳定运行后按需补全。此处仅列名字和用途，具体 Schema 在 Phase 2 设计时定义。

| 事件名 | 用途 | 备注 |
|--------|------|------|
| question_shown | 题目展示给学生 | 用于与 answer_submitted 的 answerTimeMs 做事后校验。携带 questionId 和 timestamp_start |
| lesson_paused | 学生切到别的 App 或页面 | 前端页面可见性 API 检测。切出时触发 |
| lesson_resumed | 学生切回来继续学 | 切回时触发。与 lesson_paused 配对 |
| idle_timeout | 超过 N 秒无操作 | N 默认 180 秒（3 分钟），后续根据数据校准。lesson_completed 的 activeMs 需扣除所有 idle_timeout 时段 |

---

## 四、Phase 3+ 事件（Schema 后续补全）

| 事件名 | 用途 |
|--------|------|
| explanation_replayed | 学生回看了某段讲解 |
| explanation_skipped | 学生跳过了某段讲解 |
| parent_summary_opened | 家长打开了摘要报告 |
| parent_feedback_submitted | 家长提交了反馈（准确/不准确/有帮助/不适合/请重新观察） |
| state_card_selected | 学生选择了状态卡 |
| preference_survey_submitted | 学生提交了偏好问卷 |

---

## 五、错误处理规则

### 5.1 事件拒收

以下情况事件直接拒收，不存入数据库。**本章规则优先于 5.2——先判定是否拒收，再判定是否可修复。**

| 错误 | 错误码 | 处理方式 |
|------|--------|----------|
| 缺 studentId | EVENT_MISSING_STUDENT_ID | 拒收，不重试。前端必须补全 |
| 缺 event 字段 | EVENT_MISSING_TYPE | 拒收，无法路由 |
| 缺任一"必填"字段（knowledgeCode 除外，见 5.2） | EVENT_MISSING_REQUIRED_FIELD | 拒收，返回缺失字段列表，前端补全后重传 |
| version 不兼容 | EVENT_VERSION_MISMATCH | 拒收，记录 WARN 日志 |

### 5.2 可修复事件

以下字段缺失时，优先走修复流程而非拒收。修复成功的事件正常入库。

| 错误 | 处理方式 |
|------|----------|
| 缺 knowledgeCode | 前端从 questionId 反查 knowledgeCode，补全后重传。注意：1.1 节声明 knowledgeCode 缺失例外，不走 5.1 的拒收流程 |
| 缺 questionType | 前端从 questionId 反查 questionType，补全后重传 |

> priority：5.1 > 5.2。先检查 studentId 和 event 是否缺失（立即拒收）。再检查其他必填字段。knowledgeCode 和 questionType 走 5.2 修复，其他必填字段走 5.1 拒收。

### 5.3 事件丢失

如果 chainId 中间缺失一环（比如有 answer_submitted 但没有 diagnosis_attempted），引擎不崩溃，但标记该 chainId 为 incomplete。缺失的事件在 24 小时内可以补传（携带相同 chainId），超时后该链标记为 dead。

---

## 六、版本兼容规则

| 事件 version | 引擎行为 |
|--------------|----------|
| 2.0.x | 同主版本兼容变更，正常处理（2.0、2.0.3、2.0.4 等均正常） |
| 1.0 | 尝试兼容解析。answer_submitted/hint_requested/lesson_started/lesson_completed/diagnosis_attempted 在 1.0 中不存在，跳过。原有 4 个事件（validation_triggered/completed、strategy_applied/completed）按 1.0 Schema 尝试解析，缺 chainId 时无法串联链路，降级为孤立事件处理 |
| 缺失 version | 按 1.0 处理 |
| 未来版本（> 2.x） | 跳过，记录 WARN，不崩溃 |

---

## 七、事件矩阵总览

| # | 事件名 | Phase | 触发者 | 消费方 | Schema 状态 |
|---|--------|-------|--------|--------|-------------|
| 1 | answer_submitted | Phase 1 | 前端 | 诊断引擎、画像系统、家长摘要 | 完整 |
| 2 | hint_requested | Phase 1 | 前端 | 策略引擎、画像系统、家长摘要 | 完整 |
| 3 | lesson_started | Phase 1 | 前端 | 画像系统、家长摘要、策略引擎（初始策略选择） | 完整 |
| 4 | lesson_completed | Phase 1 | 前端 | 画像系统、家长摘要 | 完整 |
| 5 | diagnosis_attempted | Phase 1 | 诊断引擎 | 策略引擎、家长摘要 | 完整 |
| 6 | validation_triggered | Phase 1 | 诊断引擎 | 前端（展示验证题） | 完整 |
| 7 | validation_completed | Phase 1 | 前端 | 诊断引擎（更新概率） | 完整 |
| 8 | diagnosis_updated | Phase 1 | 诊断引擎 | 诊断引擎（溯源决策与状态机推进）、策略引擎、画像系统、家长摘要 | 完整 |
| 9 | strategy_applied | Phase 1 | 策略引擎 | 前端（执行策略）、策略引擎（效能评估时间锚点）、家长摘要（策略描述） | 完整 |
| 10 | strategy_completed | Phase 1 | 前端 | 策略引擎（效能评估）、画像系统、家长摘要 | 完整 |
| 11 | answer_abandoned | Phase 1 | 前端 | 画像系统（参与度评估）、策略引擎（体验保护） | 完整 |
| 12 | question_shown | Phase 2 | 前端 | 画像系统（校验 answerTimeMs） | 待补 |
| 13 | lesson_paused | Phase 2 | 前端 | 画像系统（修正 activeMs） | 待补 |
| 14 | lesson_resumed | Phase 2 | 前端 | 画像系统 | 待补 |
| 15 | idle_timeout | Phase 2 | 系统 | 画像系统（修正 activeMs） | 待补 |
| 16 | explanation_replayed | Phase 3 | 前端 | 画像系统 | 待补 |
| 17 | explanation_skipped | Phase 3 | 前端 | 画像系统 | 待补 |
| 18 | parent_summary_opened | Phase 3 | 前端 | 家长摘要（读反馈） | 待补 |
| 19 | parent_feedback_submitted | Phase 3 | 前端 | 画像系统（置信度调整） | 待补 |
| 20 | state_card_selected | Phase 3 | 前端 | 策略引擎 | 待补 |
| 21 | preference_survey_submitted | Phase 3 | 前端 | 策略引擎、画像系统 | 待补 |

---

## 八、与下游文档的接口约定

### 8.1 诊断引擎（11_DIAGNOSIS_ENGINE.md）

- 输入：answer_submitted 事件（含 answer/behavior/context）+ 学生画像（prior student profile）+ 历史行为事件
- 输出：diagnosis_attempted 事件（含假设集）+ diagnosis_updated 事件（验证过程中每轮更新假设集和状态）
- 验证链路：diagnosis_attempted → validation_triggered → validation_completed → diagnosis_updated，全程共享同一 chainId。每轮 validation_completed 之后诊断引擎发出 diagnosis_updated，策略引擎据此决定是否介入

### 8.2 策略引擎（12_STRATEGY_ENGINE.md）

- 输入：diagnosis_updated 事件（取 status=validated 时的 mainHypothesis）+ diagnosis_attempted 事件（取初始假设集）+ 学生历史 strategy_completed 事件（用于效能评估）
- 输出：strategy_applied 事件（含策略包选择和参数）
- 效果评估：strategy_completed 事件 + StrategyEffect 记录

### 8.3 家长摘要（13_PARENT_SUMMARY_RULES.md）

- 输入：answer_submitted（事件 1，提取题目/学生回答）、lesson_completed（事件 4，提取 outcome.questionsAnswered/outcome.questionsCorrect + completionStatus）、diagnosis_updated（事件 8）、strategy_applied（事件 9，提取策略名称/类型）、strategy_completed（事件 10，提取 effectScore）
- 摘要生成：将事件链翻译为"学习现象 + 芽芽支持 + 积极变化/下一步建议"
- 家长反馈：parent_feedback_submitted 事件不能直接修改画像，仅作为重新观察/置信度调整/badcase复盘信号
