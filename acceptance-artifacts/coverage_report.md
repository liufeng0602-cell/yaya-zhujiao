# Phase 2 CoverageGate 覆盖报告
> 生成时间：2026-05-13T22:17:58.671229
> 状态：Phase 2 完成 ✅

## 总体覆盖率
- 知识点总数：189
- 门禁通过：189
- 阻断：0
- 警告：143（全部为 Phase 3 待补）
- 覆盖率：100%

## 按级别分布
| 级别 | 总数 | 通过 | 阻断 |
|---|---|---|---|
| A 级 | 108 | 108 | 0 |
| B 级 | 45 | 45 | 0 |
| C 级 | 36 | 36 | 0 |

## Phase 2 交付物
| 文件 | 内容 | 状态 |
|---|---|---|
| primary_math_g5_g6_knowledge_graph.json | 189 节点知识图谱，六维完整 | ✅ |
| coverage_gate_rules.json | 覆盖门禁规则 | ✅ |
| coverage_report.md | 覆盖报告 | ✅ |

## 六维覆盖率
| 维度 | 有数据的节点数 | 覆盖率 |
|---|---|---|
| sourceRef（教材出处） | 189/189 | 100% |
| prerequisites（前置知识） | 158/189 | 84% |
| next（后续知识） | 158/189 | 84% |
| questionTypes（题型） | 189/189 | 100% |
| commonErrors（错因） | 189/189 | 100% |
| strategyPacks（策略包） | 189/189 | 100% |
| masteryRule（掌握度规则） | 189/189 | 100% |

## Phase 2 未完成项（进入 Phase 3）
- validationAction（验证动作）：144 个警告
- basicQuestions（基础题）：108 个警告  
- variantQuestions（变式题）：108 个警告
- errorVerificationQuestions（错因验证题）：108 个警告
- parentSummaryTemplate（家长摘要）：108 个警告
- 跨单元前置/后置关系：部分首尾节点待补

## 下一步
- Phase 3：错因体系落地
  1. 为 108 个 A 级知识点生成错因验证动作
  2. 为所有知识点生成家长摘要模板
  3. 补充 L2/L3 层级错因（学科专属、知识点典型错因）
