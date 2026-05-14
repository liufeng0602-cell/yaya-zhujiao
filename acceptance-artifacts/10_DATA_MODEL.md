# 10 数据模型 v2.0

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | - | 初始版本：SubjectPlugin / KnowledgeNode / QuestionType / ErrorTaxonomy / StrategyPack 骨架 |
| 2.0 | 2026-05-14 | 对齐数据底座：knowledgeCode 格式统一 M5S1-0；补全 BehaviorEvent / ErrorDiagnosis / StrategyEffect / ParentSummary / GrowthMemory 完整 Schema；所有枚举对齐 09 号事件协议和 error_taxonomy.json |

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

这是芽芽助教产品文档集的第 10 号文件，定义 10 张核心数据表的完整 Schema：学科插件注册、知识点节点、题型、错因、策略包、行为事件、错因诊断记录、策略效果记录、家长摘要、成长记忆。它回答「数据怎么存」——所有引擎模块的读写都基于这些数据模型。本文档的 Schema 字段与 knowledge.json、error_taxonomy.json 等实际数据文件完全对齐。

## 一、SubjectPlugin（学科插件注册）

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

## 二、KnowledgeNode（知识点节点）

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
  "commonMistakes": ["小数点定位错误", "小数乘法进位错误", "因数变化规律应用错误"],
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

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| knowledgeCode | string | 主键。格式：M{年级}S{学期}-{序号}，如 M5S1-0 |
| levelScore | number | 六维评分总和，A≥9/B≥6/C≥3 |
| levelDims | array[6] | 六维细项：[记忆, 理解, 应用, 分析, 评价, 创造] |
| prerequisites | array | 前置知识点 code（诊断依赖层） |
| next | array | 后续知识点 code（学习路径层） |
| strategyPacks | array | 直接关联的策略包编码 |
| masteryRule | string | 掌握度计算规则名 |

## 三、ErrorTaxonomy（错因定义）

```json
{
  "errorCode": "decimal_point_position_error",
  "level": "L2",
  "category": "math_specific",
  "name": "小数点定位错误",
  "definition": "思路和列式基本正确，但积或商的小数点位置判断错误",
  "triggerConditions": [
    "列式正确",
    "计算数字基本正确",
    "小数点位置错误"
  ],
  "exclusionConditions": [
    "列式错误",
    "数量关系错误"
  ],
  "validationActions": [
    "decimal_place_visual_check",
    "decimal_point_rule_recall"
  ],
  "neighborErrors": [
    "calculation_error",
    "concept_confusion"
  ],
  "recommendedStrategies": [
    "decimal_place_visual_check",
    "decimal_position_practice"
  ],
  "parentSafeExplanation": "孩子在判断小数点位置时需要更多图示支持",
  "l1Mapping": "concept_confusion"
}
```

**86 错因全量分布**：
- L1 通用：10 个（calculation_error / comprehension_bias / concept_confusion / expression_format_error / info_omission / memory_retrieval_failure / prerequisite_gap / strategy_missing / transfer_failure / question_type_unfamiliar）
- L2 数学特有：76 个
- 数据文件：error_taxonomy.json（94KB）

## 四、ErrorKpBinding（知识点-错因绑定）

```json
{
  "knowledgeCode": "M5S1-0",
  "errorCodes": [
    "decimal_point_position_error",
    "calculation_error",
    "concept_confusion",
    "info_omission"
  ]
}
```

**绑定规则**：
- 每个 KP 最少绑 2 条（1 条 L1 通用 + 1 条领域相关）
- A 级 KP 最少绑 3 条
- 当前总计：394 个 KP × 1390 条绑定
- 数据文件：error_kp_bindings.json（332KB）

## 五、BehaviorEvent（行为事件）

统一事件表，存储所有 09 号协议定义的事件。核心字段：

```json
{
  "eventId": "evt_20260514_a1b2c3d4_001",
  "event": "answer_submitted",
  "version": "2.0",
  "chainId": "chain_a1b2c3d4",
  "studentId": "S001",
  "lessonId": "L_20260514_001",
  "timestamp": "2026-05-14T10:23:06.500Z",
  "payload": {}
}
```

**事件类型枚举（Phase 1，11 种）**：

| # | event 值 | payload 关键字段 |
|---|----------|-----------------|
| 1 | answer_submitted | answer{studentResponse, isCorrect, steps}, behavior{answerTimeMs, modifyCount, hintUsed}, context{knowledgeCode, questionId} |
| 2 | hint_requested | hintLevel, questionId, knowledgeCode |
| 3 | answer_abandoned | questionId, elapsedMs, knowledgeCode |
| 4 | lesson_started | unitName, lessonPlan |
| 5 | lesson_completed | questionCount, correctCount, durationMs |
| 6 | diagnosis_attempted | hypotheses[], mainHypothesis, status, method, diagnosisId |
| 7 | validation_triggered | diagnosisId, hypothesisId, validationQuestionId, validationAction |
| 8 | validation_completed | validationQuestionId, result{supported\|weakened\|inconclusive}, studentResponse |
| 9 | diagnosis_updated | hypotheses[], mainHypothesis, status, diagnosisStatus, diagnosisId |
| 10 | strategy_applied | diagnosisId, strategyCode, confidenceBefore |
| 11 | strategy_completed | strategyCode, effectScore, studentResponses[], diagnosisId |

完整 Schema 见 09_EVENT_PROTOCOL.md。

## 六、ErrorDiagnosis（错因诊断记录）

```json
{
  "diagnosisId": "diag_20260514_001",
  "chainId": "chain_a1b2c3d4",
  "studentId": "S001",
  "knowledgeCode": "M5S1-0",
  "sourceQuestionId": "Q_M5S1_DM_045",
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
  "diagnosisStatus": "in_progress",
  "method": "rule_engine",
  "validationRound": 1,
  "parentSummary": {
    "short": "今天孩子在找小数点的位置时有些犹豫",
    "full": "在做小数乘法题时，孩子列式和计算步骤都对了，但在确定积的小数点位置时犹豫了。芽芽用小数点定位图示帮助理解。"
  },
  "teacherNote": "M5S1-0 小数乘法·小数点定位错误 | 验证中 | 第1轮",
  "recommendedAction": ["provide_scaffolding"],
  "createdAt": "2026-05-14T10:23:06.500Z",
  "updatedAt": "2026-05-14T10:23:06.500Z"
}
```

**status vs diagnosisStatus**：

| status | 含义 | diagnosisStatus | 含义 |
|--------|------|----------------|------|
| open | 假设待验证 | in_progress | 验证进行中 |
| validated | 验证完成（确诊或排除后） | confirmed | 确诊（prob≥0.85） |
| closed | 假设被排除 | confirmed_with_reservation | 有保留确诊（0.5≤prob<0.85） |
| inconclusive | 无法判断 | excluded | 验证排除 |
| | | inconclusive | 无法判断 |
| | | traced | 已切入溯源 |

## 七、StrategyEffect（策略效果记录）

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
    "longTermRetention": null,
    "dependencyReduction": 0,
    "independentAbility": 1
  },
  "nextQuestionCorrect": true,
  "sameTypeCorrectRate": 0.67,
  "hintUsedAfter": false,
  "createdAt": "2026-05-14T10:25:00.000Z"
}
```

**effectScore 枚举**：-2（有害）/ -1（可能混淆）/ 0（无变化）/ 1（有帮助）/ 2（显著提升）

## 八、ParentSummary（家长摘要）

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
    "full": "今天小数乘法练习中，孩子一开始在确定积的小数点位置时有些犹豫。芽芽用小数点定位图示把过程可视化后，孩子能自己选出正确位置。后续可以继续用'先数小数位数'的小步骤练几次。"
  },
  "errorCodes": ["decimal_point_position_error"],
  "knowledgeCodes": ["M5S1-0"],
  "riskScore": 0.1,
  "riskFlags": [],
  "parentFeedback": null,
  "parentFeedbackAt": null,
  "createdAt": "2026-05-14T10:30:00.000Z"
}
```

**riskScore ∈ [0, 1]**：综合评估该摘要是否存在家长焦虑风险。>0.5 触发人工复审。

## 九、GrowthMemory（成长记忆）

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
      "effectScore": 1,
      "appliedAt": "2026-05-13T15:00:00.000Z"
    }
  ],
  "errorTendency": {
    "decimal_point_position_error": 0.35,
    "calculation_error": 0.15
  },
  "milestones": [
    {
      "type": "mastered",
      "date": "2026-05-12",
      "detail": "连续5次正确，掌握度突破0.8"
    }
  ],
  "coldStartFlag": false,
  "updatedAt": "2026-05-14T10:30:00.000Z"
}
```

## 十、核心枚举

| 枚举名 | 值 | 说明 |
|--------|-----|------|
| Stage | primary / middle / high | 学段 |
| Subject | math / chinese / english / ... | 学科 |
| KnowledgeLevel | A / B / C / D | 知识点重要程度 |
| ErrorLevel | L1 / L2 / L3 | 错因层级 |
| DiagnosisStatus | in_progress / confirmed / confirmed_with_reservation / excluded / inconclusive / traced | 六态 |
| StrategyEffectScore | -2 / -1 / 0 / 1 / 2 | 策略效果 |
| SummaryType | lesson / weekly / monthly / stage | 摘要周期 |
| ParentFeedback | accurate / inaccurate / helpful / unsuitable / reobserve | 家长反馈 |
| ValidationResult | supported / weakened / inconclusive | 验证结果 |
| MethodPhase | rule_engine / decision_tree / ai_assisted | 诊断方法 |

## 十一、数据文件清单

| 文件 | 大小 | 记录数 | 说明 |
|------|------|--------|------|
| primary_math_g5_g6_knowledge.json | 521KB | 189 KP | 五/六年级知识点 |
| primary_math_g1_g4_knowledge.json | 391KB | 205 KP | 一至四年级知识点 |
| primary_math_g5_g6_knowledge_graph.json | 172KB | 189 nodes | 五/六年级知识图谱 |
| primary_math_g1_g4_knowledge_graph.json | 187KB | 205 nodes | 一至四年级知识图谱 |
| error_taxonomy.json | 94KB | 86 errors | 错因分类体系 |
| error_kp_bindings.json | 332KB | 1390 bindings | 知识点-错因绑定 |
| question_type_matrix.json | 260KB | - | 题型规格矩阵 |
