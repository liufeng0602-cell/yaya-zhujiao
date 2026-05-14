# 超地狱验收 第二轮 — 穿透审计报告

生成时间: 2026-05-14
审计方式: 程序化 15 项穿透检查 (189 知识点 × 多文件交叉)
上一轮: 6 BLOCK + 2 WARN → 本轮: 17 BLOCK + 3 WARN

---

## 总览

| 指标 | 数值 |
|---|---|
| 检查项 | 15 (比上一轮多 3 个交叉文件维度) |
| 阻断 (BLOCK) | 17 |
| 警告 (WARN) | 3 |
| 信息 (INFO) | 23 |
| 综合判定 | **不通过 — 17 个阻断项必须修复** |

---

## 本轮新增发现 (上一轮未覆盖的审计死角)

上一轮审计依赖字段名匹配，未穿透以下维度：
1. levelDims 的实际数据结构是 **list** (非 dict)，求和逻辑不同
2. 错因码三向交叉：taxonomy → bindings 方向未检查
3. levels.json 的级别标签 vs knowledge.json 实际 level 字段一致性
4. M5S2-28..33 缺失字段范围比上一轮报告的更广 (10 个字段而非 7 个)

---

## 阻断项详情

### BLOCK-1: levelScore 与 levelDims 数学一致性彻底断裂

严重程度: **致命**
影响范围: 135/183 (73.8%) — 比上一轮的 95/183 (52%) 更严重

根因: levelDims 是 **list** `[textbookWeight, cognitiveDepth, prerequisiteChain, examFrequency, errorProneness, transferability]`，不是 dict。
直接 sum(list) 得到真实分。大量 A 级知识点声明 score=9 但 dims 求和仅 2-8。

**典型示例:**
- M5S1-1 小数乘整数笔算方法: ls=9, dims=[0,0,1,2,1,2], sum=6 → 实际 B 级
- M5S1-2 积末尾有0的化简: ls=9, dims=[0,0,1,1,1,1], sum=4 → 实际 C 级
- M5S1-3 小数乘法中的小数点定位: ls=9, dims=[2,0,1,1,1,2], sum=7 → 实际 B 级

**133 个知识点会因此改变级别** (A↔B/C 等翻转)

**修复方案:** 以 sum(levelDims) 为准替换 levelScore，按新分数重定 level。

---

### BLOCK-2: M5S2-28~33 缺失 10 个必填字段

这 6 个知识点在 knowledge.json 中缺失:
- verifiedBy, confidence, status
- teachingGoal, keyPoints, commonMistakes, tags
- level, levelScore, levelDims

比上一轮报告的 7 个字段更多。

它们在 KG 和 levels.json 中已补全，但 knowledge.json 未回写。

---

### BLOCK-3: levels.json 级别标签 vs knowledge.json level 字段不一致

11 个知识点在 levels.json 和 knowledge.json 中被标为不同级别:

| Code | levels.json | knowledge.json |
|---|---|---|
| M5S2-31 | A | (缺失) |
| M5S1-51 | A | ? |
| M5S1-53 | A | ? |
| M5S1-56 | A | ? |
| M6S2-0 | A | ? |
| M5S2-29 | A | (缺失) |
| M5S2-30 | B | (缺失) |
| M6S2-9 | B | ? |
| M5S2-33 | B | (缺失) |
| M5S2-28 | C | (缺失) |
| M5S2-32 | C | (缺失) |

其中 6 个是 M5S2-28..33 (修复 BLOCK-2 即解决)，另外 5 个需要单独核查。

---

### BLOCK-4: 10 个 L1 通用错因未绑定到任何知识点

错因码三向交叉发现:

| 方向 | 结果 |
|---|---|
| KG → Taxonomy | ✓ 全部匹配 |
| Taxonomy → Bindings | ✗ 10 个 L1 错因无绑定 |
| Bindings → Taxonomy | ✓ 全部匹配 |

未绑定的 10 个 L1 错因:
`calculation_error, comprehension_bias, concept_confusion, expression_format_error, info_omission, memory_retrieval_failure, prerequisite_gap, question_type_unfamiliar, strategy_missing, transfer_failure`

这些是通用认知层面的错因，不属于某个具体数学知识点，但需要明确处置：作为全局后备错因 / 降级兜底 / 或也绑定到高频知识点。

---

### BLOCK-5: levelScore 分布严重畸形

得分分布: 9分(101), 5分(36), 4分(23), 3分(8), 2分(5), 6分(5), 7分(4), 10分(1), None(6)

- 101/183 (55%) 集中在 9 分 — 大量节点被硬编码为 A 级边界值
- 0/1/8/11/12 分完全缺失
- 6 个 None (M5S2-28..33)

修复 BLOCK-1 后此分布会自动修正。

---

### BLOCK-6: levelDims 六维值域严重偏斜

| 维度 | 范围 | 均值 |
|---|---|---|
| textbookWeight | [0,2] | 0.4 |
| cognitiveDepth | [0,2] | 0.1 |
| prerequisiteChain | [0,2] | 0.9 |
| examFrequency | [1,2] | 1.1 |
| errorProneness | [1,2] | 1.2 |
| transferability | [0,2] | 1.0 |

- textbookWeight 均值仅 0.4 — 大量知识点教材权重为 0
- cognitiveDepth 均值仅 0.1 — 几乎全部被标为低认知深度
- 六维区分度不足: 前两维近乎废弃，后四维集中在 [1,2]

**这可能也是 levelScore 偏高的根因之一** — 低权重 + 低深度拉低了 dims 求和，但 levelScore 被独立赋值。

---

## 警告项

### WARN-1: KG 31 个节点 prerequisites 为空

31 个起始知识点 (如 M5S1-0, M5S1-15, M5S1-20...) 的 prerequisites 为空。
单元起始点可能有合理原因，但需逐条标注决策 (真正无前置 vs 前置未录入)。

### WARN-2: KG 31 个节点 next 为空

与 WARN-1 对应——31 个终末知识点 next 为空。
同样需要标注决策。

### WARN-3: 10 个 L1 错因未被任何 KG 节点引用

这些是通用错因，可能有意不作为具体知识点的 commonErrors，但需确认设计意图。

---

## 通过项 (确认无问题)

- KG 六维字段名: 189 个节点全部使用正确字段名 (prerequisites/next/questionTypes/commonErrors/strategyPacks/masteryRule)
- KG ↔ Knowledge: 189 节点完美对应，无一遗漏/多余
- levels.json ↔ Knowledge: 189 代码一一对应
- Error taxonomy: 86 个错因 (10 L1 + 76 L2) 全部 11 字段完整
- Error bindings: 189 个知识点全部有绑定，A 级 min=3 满足要求
- 错因名: 无重复

---

## 修复优先级

| 优先级 | 阻断项 | 预估 |
|---|---|---|
| P0 | BLOCK-1: levelScore = sum(dims) 一致性 | 30min (程序化批量修复) |
| P0 | BLOCK-2: M5S2-28..33 回填 10 个字段 | 15min |
| P0 | BLOCK-4: L1 错因绑定决策 + 处置 | 15min |
| P1 | BLOCK-3: 5 个非 M5S2-28..33 的级别不一致 | 10min (人工核查) |
| P1 | BLOCK-6: levelDims 六维值域重新评估 | 60min (需领域知识) |
| P2 | WARN-1/2: 31 个空 prerequisites/next 标注决策 | 20min |
| P2 | WARN-3: L1 错因在 KG 中的引用决策 | 10min |

---

## 与上一轮对比

| 指标 | 上一轮 | 本轮 | 差异原因 |
|---|---|---|---|
| BLOCK 总数 | 6 | 17 | 新增 3 个交叉维度审计 |
| levelScore 异常 | 95/183 | 135/183 | levelDims 是 list 非 dict, sum 更精确 |
| levelDims 值域 | 未查 | 发现严重偏斜 | 新增统计维度 |
| 错因-绑定交叉 | 未查 Tax→Bind | 10 个 L1 未绑定 | 新增三向交叉 |
| Level 标签一致性 | 未查 | 11 个不一致 | 新增 levels↔knowledge 交叉 |
