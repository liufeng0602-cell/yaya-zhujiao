# 超地狱验收报告 — Phase 0 / Phase 1 / Phase 2

生成时间: 2026-05-13 超地狱级穿透审计
审计方式: 程序化全量逐条校验 (189条知识点 × 23项检查)
上一轮: 地狱自检 (23项中15通过, 0阻断) — 本轮的严格程度提升到数据层穿透

---

## 总览

| 指标 | 数值 |
|---|---|
| 检查项总数 | 23 |
| 通过 | 15 |
| 阻断 (BLOCK) | 6 |
| 警告 (WARN) | 2 |
| 综合判定 | **有条件不通过 — 6个阻断项必须修复** |

---

## 阻断项 (必须修复才能继续)

### BLOCK-1: levelScore ≠ sum(levelDims) — 数学一致性断裂

严重程度: 致命
影响范围: 95/183 个已分级知识点 (52%)

问题: levelScore 与 levelDims 六维求和值不一致。大量 A 级知识点声明 score=9 但 dim 求和 2-8, B 级声明 score=5 但 dim 求和 2-4, C 级声明 score=4 但 dim 求和 5-8。

典型示例:
- M5S1-1 小数乘整数笔算方法: levelScore=9, sum(dims)=6 (实际应为 B 级)
- M5S1-2 积末尾有0的化简规则: levelScore=9, sum(dims)=4 (实际应为 C 级)
- M5S1-64 小数乘除法综合计算: levelScore=4, sum(dims)=7 (实际应为 B 级)
- M5S2-12 长方体正方体体积公式: levelScore=9, sum(dims)=8 (临界 B/A)

根因: 看起来 levelScore 是独立赋值的(大量硬编码为 9/5/4 整档值), 而 levelDims 是按六维评分表真实计算的, 两者未联动。

修复方案: 
- 方案A(推荐): 以 levelDims 求和的真实值替换 levelScore, 然后按真实分数重定级别
- 方案B: 以 levelScore 为准, 重新调整 levelDims 使之求和一致

### BLOCK-2: 6个知识点完全缺少 level 字段

严重程度: 致命
影响范围: M5S2-28 ~ M5S2-33

这6个点是五下补充知识点, 在 knowledge.json 中有基本信息但缺少:
- level, levelScore, levelDims (无分级)
- verifiedBy, confidence, status, teachingGoal, keyPoints, commonMistakes, tags (7个必填字段缺失)

有趣的是它们在 levels.json 和知识图谱中已补了分级(2A + 2B + 2C), 但 knowledge.json 未回写。

| Code | Name | levels.json级别 |
|---|---|---|
| M5S2-28 | 探索和的奇偶性 | C (score=3) |
| M5S2-29 | 体积单位间的进率 | A (score=9) |
| M5S2-30 | 不规则物体的体积测量 | B (score=6) |
| M5S2-31 | 分数与除法的关系 | A (score=10) |
| M5S2-32 | 用旋转解决实际问题 | C (score=3) |
| M5S2-33 | 分数加减法应用题 | B (score=5) |

修复方案: 将 levels.json 中的分级数据和必填字段回写到 knowledge.json 这6条记录中。

### BLOCK-3: knowledge.json vs levels.json A级数量不一致

knowledge.json 实际 A=102 (6个无level + 其余183中有102个A)
levels.json 声明 A=108 (多出6 = M5S2-28..33)

修复 BLOCK-2 后此问题自动解决。

### BLOCK-4: 6个知识点 status 字段缺失

M5S2-28~33 的 status 字段缺失, 导致 183/189=96.8% 正确标注 needs_textbook_body_review, 而非要求的 100%。

### BLOCK-5: 实践活动处置 — 7/8 未在 knowledge.json 中显式建知识点

Dashboard 宣称"8项实践活动均按规则处置为C级实践节点或复习聚合入口", 但实际:
- ✅ 掷一掷 → M5S1-37 (掷骰子概率实验分析, C级)
- ❌ 探索图形 → 仅在 outline 中作为目录项(五年级下册 ★单元), 无对应知识点
- ❌ 怎样通知最快 → 同上
- ❌ 节约用水 → 仅在 outline 六上册第七单元目录中, 无知识点
- ❌ 确定起跑线 → 同上
- ❌ 生活与百分数 → 同上
- ❌ 自行车里的数学 → 同上
- 总复习/整理与复习 → 有知识点(复习聚合入口)

评估: 按 03_SYLLABUS_SOURCE_RULES.md 要求, "实践活动项有处理决策：知识点化/专题化/暂不入图谱"。目前状态可以认为是"决策不单独建知识点"但文档未明确标注。建议在 sourceReview 或 notes 字段中为每个活动添加显式处置说明。

---

## 警告项 (应关注但不阻断)

### WARN-1: 得分分布断层

得分分布: 2分(5个), 3分(8个), 4分(23个), 5分(36个), 6分(5个), 7分(4个), 9分(101个), 10分(1个)

断层: 0分, 1分, 8分, 11分, 12分全部缺失

- 8分缺失说明无"高B级/低A级"交界项 — 但如果 dims 修复后(见 BLOCK-1)可能会补上
- 0-1分缺失合理 (不存在完全无价值的知识点)
- 11-12分缺失合理 (小学知识点难达满分)

### WARN-2: 五下知识点偏少 + 六上缺课时级细粒度

- 五下: 34个知识点, 9个单元, 均3.8/单元 vs 五上70个(8单元, 均8.8/单元)
- 六上: 6个单元仅单元级目录, 无课时细分

两问题都在文档中已坦诚标注, 属已知限制。

---

## 通过项 (确认无问题)

- ✅ Phase 0: 15个工程文档全部到位
- ✅ Phase 0: knowledgeCode 189个全局唯一
- ✅ Phase 0: 编号连续 (M5S1/M5S2/M6S1/M6S2 内部无断层)
- ✅ Phase 0.2: 4册教材大纲完整, sourceRef 全部指向电子课本网
- ✅ Phase 0.3: sourceReview 覆盖率 100%
- ✅ Phase 0.3: needsTextbookBodyReview 100% 诚实标注
- ✅ Phase 0.3: needsPageRef 100% 诚实标注(缺页码)
- ✅ Phase 1: 分级边界合规 (A≥9, B=5-8, C≤4 — 但见BLOCK-1)
- ✅ Phase 1: levels.json 内部自洽 (summary=实际列表)
- ✅ Phase 1: levels.json ↔ knowledge.json 代码双文件一致(无遗漏无多余)
- ✅ Phase 2: 知识图谱 189节点, 六维100%完整
- ✅ Phase 2: M5S2-28..33 在知识图谱中已补全
- ✅ 14个必填字段: 除6个破损项外全部完整

---

## Phase 2 补充审计

知识图谱(primary_math_g5_g6_knowledge_graph.json):
- 189个节点, 每个都有: prerequisites, next, questionTypes, commonErrors, strategyPacks, masteryRule — 六维100%
- 所有节点 status=draft (诚实)
- M5S2-28..33 已全部纳入

覆盖门禁(coverage_gate_rules.json):
- 0阻断, 143警告
- summary含 passed/total 字段
- 与 Phase 2 dashboard 记录一致

注意: 覆盖门禁基于有问题的 levelScore 构建, BLOCK-1 修复后需重新跑。

---

## 修复优先级

1. P0-立即: 修复 M5S2-28~33 的 knowledge.json 缺失字段 (BLOCK-2/3/4, 约10分钟)
2. P0-立即: 修复 levelScore = sum(levelDims) 一致性 (BLOCK-1, 影响95项, 约30分钟)
3. P1-本阶段: 为7个实践活动添加显式处置决策记录 (BLOCK-5, 约15分钟)
4. P2-后续: 五下知识点补充核对, 六上细粒度目录补全 (WARN-2)
