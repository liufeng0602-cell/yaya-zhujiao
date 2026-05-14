# 05 CoverageGate 覆盖门禁 v2.1.2

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

这是芽芽助教产品文档集的第 05 号文件，定义知识点、题型、错因、策略包、家长摘要的上线门禁规则。它回答「能不能发布」——任何数据或引擎变更必须通过全部门禁后才能上线。

门禁规则由 9 条自动化铁规（R1-R9）实现为 `data_quality_gate.py` 脚本。旧版 05 号的 17 项手检清单已整合进 9 铁规框架中——9 铁规是自动化执行层，17 项是每 KP 必须满足的字段完整性要求。

## 1. 门禁总则

CoverageGate 是正式发布门禁系统，判断知识点、题型、错因、策略、验证动作、家长摘要是否具备上线条件。

CoverageGate 规则由人类确认，AI 可辅助生成脚本实现和修复建议，但不能自行降低发布标准或绕过门禁。

### 1.1 自动化门禁脚本

```bash
cd acceptance-artifacts && python3 data_quality_gate.py
```

返回 9/9 PASS 表示数据底座健康，任何 blocker 必须修复后才能提交。

---

## 2. 9 条自动化铁规（R1-R9）

### R1 — levelScore 程序化计算

`levelScore` 必须由 `curriculumLevel` 映射得出：A=3, B=6, C=9, D=12。手填值直接阻断。

**检查方式**：遍历全部 KP，`levelScore == mapped_value(curriculumLevel)`

### R2 — 三文件交叉对账

`knowledge.json`、`knowledge_graph.json`、`levels.json` 三文件的 knowledgeCode 集合必须完全一致。

**检查方式**：提取三文件全部 code → 求交集 → 差集必须为空

### R3 — 字段区分度

新增字段在真实数据中的值分布必须有意义。>80% 取值相同触发 WARN（不阻断）。

**检查方式**：遍历指定字段的取值分布

### R4 — 错因必须引用

`error_taxonomy.json` 中每一个错因 code 必须在 `error_kp_bindings.json` 中出现至少 1 次。

**检查方式**：提取 taxonomy 全部 code → 与 bindings 交集 → 差集必须为空

### R5 — 必填字段完整

每个 KP 必须包含 17 个必填字段：knowledgeCode, name, unit, book, grade, lesson, sourceRef, curriculumLevel, curriculumLevelLabel, levelScore, teachingGoal, keyPoints, commonMistakes, tags, verifiedBy, confidence, status。

**检查方式**：遍历全部 KP → 逐字段判空

### R6 — 级别标签一致

knowledge.json 中 KP 的 `curriculumLevel` 必须与 levels.json 的分桶一致。

**检查方式**：提取 knowledge.json 每 KP 的 curriculumLevel → 在 levels.json 对应桶中查找

### R7 — A 级错误绑定深度

每个 A 级（了解）KP 在 `error_kp_bindings.json` 中必须至少有 3 条绑定。

**检查方式**：提取 A 级 KP code 集合 → 统计每 KP 绑定数

### R8 — 双向边一致

如果 A.prerequisites 包含 B，则 B.next 必须包含 A（反之亦然）。图谱边必须双向。

**检查方式**：遍历全部节点 → 校验每条入边有对应出边

### R9 — 题库矩阵覆盖

`question_type_matrix.json` 中每个 KP 的 questionTypes 非空。全部 KP 必须覆盖。

**检查方式**：提取矩阵全部 code → 与 knowledge.json 交集

---

## 3. 知识点字段完整性清单（17 项）

每 KP 提交前必须检查以下字段。这些检查分布在 R2/R5/R6 等规则中。

| # | 检查项 | 对应字段 | 归属铁规 |
|---|--------|---------|---------|
| 1 | knowledgeCode | `knowledgeCode` | R2, R5 |
| 2 | 年级 | `grade` | R5 |
| 3 | 册别 | `book` | R5 |
| 4 | 单元 | `unit` | R5 |
| 5 | 小节/课时 | `lesson` | R5 |
| 6 | 教材来源 | `sourceRef` | R5 |
| 7 | 前置知识 | `knowledge_graph.json → prerequisites` | R8 |
| 8 | 后续知识 | `knowledge_graph.json → next` | R8 |
| 9 | 分级 | `curriculumLevel` | R1, R6 |
| 10 | 题型 | `question_type_matrix.json` | R9 |
| 11 | 错因 | `commonMistakes` / `error_kp_bindings.json` | R4, R7 |
| 12 | 验证动作 | `error_taxonomy.json → validationActions` | R4, R5 |
| 13 | 推荐策略 | `strategyPacks` | R4 |
| 14 | 掌握度规则 | `masteryRule` | R5 |
| 15 | 基础题 | 题库系统 | R9 |
| 16 | 验证题 | 题库系统 | R4 |
| 17 | 家长摘要模板 | `error_taxonomy.json → parentExplanation` | R4 |

---

## 4. 分级门禁要求

### 4.1 A 级（了解）门禁

```
必须有教材来源
必须有知识图谱位置（在 knowledge_graph.json 中存在对应节点，前置或后续至少一端有边）
必须至少绑定 2 个题型
必须至少绑定 3 个常见错因（R7）
必须至少绑定 2 个策略包
必须至少有 1 个验证动作
必须至少有 5 道基础题
必须至少有 5 道变式题（同一知识点、不同问法或数据，难度在知识点本身难度区间内；A 级为 difficulty 1-3，见 04 号文档 §2 建设深度表）
必须至少有 3 道错因验证题（error_validation_questions.json 中的定向验证题，用于诊断引擎 §7.3 的多轮验证流程）
必须有家长摘要模板
必须有掌握度规则
```

缺任意一项，不允许发布（blocker）。

### 4.2 B 级（理解）门禁

```
必须有教材来源
必须有前置/后续关系
满足 R9 铁规要求（questionTypes 非空）
必须至少绑定 1 个常见错因
必须至少绑定 1 个策略包
必须至少有 3 道基础题
必须有基础掌握度规则
```

### 4.3 C 级（掌握）门禁

```
必须有教材来源
必须有基础说明
必须有知识图谱位置
必须有基础练习入口
```

### 4.4 D 级（运用）门禁

```
满足 C 级全部要求
必须至少绑定 1 个情境/开放题型
必须有迁移应用验证题
```

---

## 5. 跨模块门禁

### 5.1 QuestionType 门禁（题型）

每个题型必须检查：定义、适用知识点、难度梯度（对齐 04 号文档 §2 建设深度表的各级别难度区间——A 级 1-3、B 级 2-5、C 级 3-7、D 级 5-10）、常见错因、验证题模板、推荐策略包。

### 5.2 ErrorTaxonomy 门禁（错因）

每类错因必须检查：定义、触发条件、排除条件（exclusionConditions）、验证动作、对应策略包、家长端中性解释（parentExplanation）。

### 5.3 StrategyPack 门禁（策略包）

每个策略包必须检查（对齐 08_STRATEGY_PACKS.md 字段定义）：编码（SP_X_XX）、策略名、适用场景、核心动作、强/中/弱分类、同天频率限制、结束条件（见 08 号 §7.3）。适用学段、话术模板由学段话术模板包（SP_T_ 系列）独立管理，不在通用/学科策略包字段中。

### 5.4 ParentSummary 门禁（家长摘要）

每个家长摘要模板必须检查（对齐 13_PARENT_SUMMARY_RULES.md §10 验收标准）：

- 是否使用中性表达
- 是否避免禁止词（检测检出率 100%）
- 是否包含具体现象
- 是否包含系统支持动作
- 是否包含积极变化或下一步建议
- 是否不展示原始错因概率
- 是否不做心理判断
- 中断场景（completionStatus ≠ completed）是否仍生成摘要
- L2 错因 parentExplanation 为空时是否回退 parentL1

完整验收标准见 13_PARENT_SUMMARY_RULES.md §10。

---

## 6. 输出格式

门禁脚本输出示例（对齐 9 铁规）：

```json
{
  "scope": "primary_math_g1_g6",
  "totalKnowledge": 394,
  "passed": 394,
  "failed": 0,
  "coverageRate": 1.0,
  "results": {
    "R1_levelScore": "PASS",
    "R2_cross_file": "PASS",
    "R3_field_entropy": "PASS",
    "R4_error_reference": "PASS",
    "R5_required_fields": "PASS",
    "R6_level_consistency": "PASS",
    "R7_A_binding_depth": "PASS",
    "R8_bidirectional_edges": "PASS",
    "R9_matrix_coverage": "PASS"
  },
  "failures": [
    {
      "knowledgeCode": "M5S1-0",
      "curriculumLevel": "A",
      "missing": ["validationActions", "parentExplanation"],
      "severity": "blocker"
    }
  ],
  "generatedAt": "datetime"
}
```

---

## 7. 发布规则

| 级别 | 含义 | 措施 |
|------|------|------|
| blocker | 阻断发布 | 必须修复，zero-tolerance |
| warning | 允许内部测试，不建议正式发布 | 列入修复队列 |
| pass | 通过 | 可发布 |

---

**变更记录**

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v2.1.2 | 2026-05-15 02:43 | 交叉审查修复（2 项）：(1)R5 必填字段增加 sourceRef（16→17），对齐 §3 第 6 项教材来源和 03 号文档 JSON 示例；(2)§5.2 错因门禁「排出条件」→「排除条件（exclusionConditions）」，对齐 07 号文档和 error_taxonomy.json 实际字段名 |
| v2.1.1 | 2026-05-15 02:39 | 交叉审查修复（6 项）：(1)R5 必填字段增加 lesson（15→16），对齐 §3 第 5 项和 03 号文档 JSON 示例；(2)§3 第 12 项 validationAction→validationActions（复数），归属铁规 R4→R4,R5；(3)§4.1 A 级门禁「变式题」难度阈值 difficulty≥5→在知识点本身难度区间内（A 级 difficulty 1-3），消除与 04 号 §2 A 级难度 1-3 的矛盾；(4)§4.1 A 级门禁「必须有前置知识」「必须有后续知识」合并为「必须有知识图谱位置（前置或后续至少一端有边）」，避免强制起始/终点节点编造边；(5)§5.1 题型门禁难度梯度补 04 号 §2 各级别难度区间引用；(6)§4.1 变式题/错因验证题定义从独立注释行整合入门禁清单条目 |
| v2.1.0 | 2026-05-15 02:33 | 交叉审查修复（7 项）：(1)§4.1 A 级门禁「变式题」「错因验证题」补定义——变式题=基础题 difficulty≥5 子集，错因验证题=error_validation_questions.json 定向验证题；(2)§4.2 B 级门禁「至少绑定 1 个题型」→「满足 R9 铁规要求」消除与 R9 的冗余；(3)§5.3 策略包门禁检查项对齐 08 号实际字段——编码/策略名/适用场景/核心动作/强中弱分类/同天频率限制/结束条件，移除不存在的「适用学段」「禁用条件」等；(4)§5.4 家长摘要门禁补 2 项——中断场景摘要生成、L2 错因 parentExplanation 回退 parentL1，并引 13 号 §10 完整验收标准；(5)§6 输出示例字段名校正——validationAction→validationActions、parentSummaryTemplate→parentExplanation；(6)§7 发布规则移除未定义缩写「AMP 级」；(7)§1.1「BLOCK」→「blocker」统一大小写和拼写 |
| v2.0.0 | 2026-05-15 00:37 | 全文重写：9 铁规（R1-R9）替代旧 17 项手检清单，两套体系整合——9 铁规为自动化执行层、17 项为字段完整性清单。新增 D 级门禁、R1 程序化校验、跨模块门禁、输出格式对齐实际门禁脚本。示例 JSON 字段修正（level→curriculumLevel、scope→primary_math_g1_g6）。 |
