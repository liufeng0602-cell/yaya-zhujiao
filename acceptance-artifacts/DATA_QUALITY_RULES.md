# 芽芽助教 数据质量门禁规则

版本: v1.0
生效日期: 2026-05-14
适用范围: 知识点分级体系 (knowledge.json / levels.json / knowledge_graph.json / error_taxonomy.json / error_kp_bindings.json)

---

## 规则总览

| 编号 | 规则 | 类型 | 违反后果 |
|------|------|------|----------|
| R1 | 算分必须程序计算，禁止手填 | 阻断 | 不得提交 |
| R2 | 三文件交叉对账，缺一不可 | 阻断 | 不得提交 |
| R3 | 新维度/新字段上线前必须跑真实数据验证 | 阻断 | 不得上线 |
| R4 | 定义的错因必须被引用 | 阻断 | 不得提交 |
| R5 | 知识点必填字段完整性 | 阻断 | 不得提交 |
| R6 | 级别标签多文件一致性 | 阻断 | 不得提交 |

---

## R1: 算分必须程序计算，禁止手填

**问题根因**: 73.8% 的知识点 levelScore 是手填的假数字，与 6 个维度的实际求和结果不一致。101 个知识点被集中标为 9 分（最高档边界值）。

**规则**: levelScore 必须由程序根据 curriculumLevel 或 levelDims 自动计算，不得手工录入。计算逻辑写死在脚本中，任何人不得绕过。

**计算逻辑** (当前版本):
- 若有 curriculumLevel: D=4 → 算分=curriculumLevel 映射分
- levelScore 字段在 knowledge.json 中保留，但它的值必须与程序计算结果一致

**检查方式**: 脚本重新计算所有知识点的 levelScore，与文件中实际值逐一比对，任何不一致即阻断。

---

## R2: 三文件交叉对账，缺一不可

**问题根因**: 知识图谱补了数据，主数据文件没同步（6 个知识点缺失 10 个字段）。levels.json 和 knowledge.json 各写各的。

**规则**: 每次修改 knowledge.json 后，必须同步更新:
1. knowledge_graph.json — 知识图谱
2. levels.json — 分级表

三个文件中的知识点代码集合必须完全一致，一个不能多，一个不能少。

**检查方式**: 提取三个文件的全部知识点代码，做集合运算:
- knowledge.json 有但 KG 没有 → 阻断
- KG 有但 knowledge.json 没有 → 阻断
- levels.json 有但 knowledge.json 没有 → 阻断
- knowledge.json 有但 levels.json 没有 → 阻断

---

## R3: 新维度/新字段上线前必须跑真实数据验证

**问题根因**: 6 维度评分系统中，textbookWeight 均值仅 0.4、cognitiveDepth 均值仅 0.1，两个维度在实际数据中几乎无区分度，等于废了。但设计阶段无人验证。

**规则**: 任何新增的评分维度、分类字段、结构变更，在上线前必须:
1. 用全部 189 个知识点的真实数据跑一遍
2. 输出该维度/字段的值域分布（最大值、最小值、均值、标准差、各取值的数量）
3. 确认区分度达标（至少 3 个不同取值，且 80% 数据不集中在单一取值）

**检查方式**: 脚本自动扫描 knowledge.json 中的自定义字段（非核心必填字段），列出每个字段的值域分布。若发现某个字段 90% 以上知识点取值完全一致，标记为"低区分度字段"并预警。

---

## R4: 定义的错因必须被引用

**问题根因**: error_taxonomy.json 中定义了 10 个 L1 通用错因（如"计算粗心""概念混淆"），但 error_kp_bindings.json 中一个知识点都没绑定。等于药房上了药但没告诉病人该吃哪种。

**规则**: 
- error_taxonomy.json 中定义的每一个错因码，必须在 error_kp_bindings.json 中至少有一条绑定记录
- 或者在知识点的 commonErrors 字段中被引用
- 两者至少满足其一

**检查方式**: 
1. 提取 taxonomy 的全部错因码
2. 提取 bindings 的全部错因码
3. 提取 knowledge.json 中所有 commonErrors 引用的错因码
4. taxonomy 有但 (bindings + commonErrors) 都没有的 → 阻断

---

## R5: 知识点必填字段完整性

**问题根因**: 6 个知识点（M5S2-28~33）缺失 level/levelScore/levelDims/verifiedBy/confidence/status/teachingGoal/keyPoints/commonMistakes/tags 共 10 个字段，属于半成品。

**规则**: 每个知识点必须包含以下字段且有值（非 null、非空字符串、非空数组）:

必修字段清单:
- knowledgeCode — 知识点代码
- knowledgeName — 知识点名称
- unit — 所属单元
- semester — 学期
- grade — 年级
- knowledgeType — 知识点类型
- curriculumLevel — 新课标认知层级 (A/B/C/D)
- curriculumLevelLabel — 层级中文标签 (了解/理解/掌握/运用)
- levelScore — 综合分级得分（程序计算，见 R1）
- teachingGoal — 教学目标
- keyPoints — 教学重点
- commonMistakes — 常见错因
- tags — 标签
- verifiedBy — 核验人
- confidence — 置信度
- status — 状态

**检查方式**: 逐知识点检查上述字段是否存在且非空。缺失任一项即阻断，并列出缺失详情。

---

## R6: 级别标签多文件一致性

**问题根因**: 11 个知识点在 levels.json 和 knowledge.json 中被标为不同级别。

**规则**: 对同一个知识点代码:
- knowledge.json 中的 curriculumLevel 字段
- levels.json 中该代码对应的 level 字段
两者的值必须完全一致。

**检查方式**: 按知识点代码逐条交叉比对，任何不一致即阻断。

---

## 附录: 门禁脚本使用说明

### 运行方式
```bash
cd /Users/liufeng/Downloads/yaya-browser-v3/acceptance-artifacts/
python3 data_quality_gate.py
```

### 输出说明
- 全部通过: 显示绿色 "PASS — 6/6 规则通过"
- 有阻断: 显示红色 "BLOCK — X 条规则未通过"，逐条列出违规详情

### 何时运行
- 每次修改 knowledge.json / levels.json / knowledge_graph.json / error_taxonomy.json / error_kp_bindings.json 之后
- 建议接入 CI/CD，提交前自动运行
