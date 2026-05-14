# 芽芽助教自我进化 AI 教学适配引擎 · 文档索引 v2.0

本文档集用于指导「芽芽助教」K12 多学科自我进化 AI 教学适配引擎的产品、工程、AI 教研与数据闭环开发。

更新日期：2026-05-15

## 核心定位

芽芽助教不是普通题库、不是简单 AI 讲题工具、不是儿童心理测评系统，而是：

> 面向 K12 全学段、多学科场景，以真实教材知识图谱为骨架、以学习行为为真值、以错因诊断为核心、以策略调度为动作系统、以成长记忆为长期资产的自我进化 AI 教学适配引擎。

## 当前范围

**MVP：人教版小学数学 5-6 年级。数据底座 1-6 年级全量建成，1-4 年级为第二阶段扩展。**

| 维度 | 状态 |
|------|------|
| 知识点 | 394 个（G1-G4: 205, G5-G6: 189），全量录入 ✅ |
| 错因体系 | 86 个（L1 通用 10 + L2 数学特有 76），全量定义 ✅ |
| 错因绑定 | 1390 条，394 个 KP 全覆盖 ✅ |
| 知识图谱 | 两层架构（学习路径 + 诊断依赖），G1-G6 全部建成 ✅ |
| 题型矩阵 | question_type_matrix.json（260KB）✅ |
| 门禁 | data_quality_gate.py v2.0，9 铁规全覆盖 ✅ |

## 推荐阅读顺序

### 第一次来？从这里开始
1. `00_INDEX.md`（本文件）
2. `01_PRODUCT_VISION.md` — 产品定义、核心壁垒
3. `02_DEVELOPMENT_ROADMAP.md` — 分阶段开发路线

### 理解数据底座
1. `03_SYLLABUS_SOURCE_RULES.md` — 教材/教参/课标来源规则
2. `04_KNOWLEDGE_LEVELING.md` — A/B/C/D 分级规则
3. `05_COVERAGE_GATE.md` — 覆盖门禁规则
4. `06_KNOWLEDGE_GRAPH.md` — 知识图谱两层架构
5. `07_ERROR_TAXONOMY.md` — 错因分类与边界

### 理解引擎链路
1. `08_STRATEGY_PACKS.md` — 策略包定义（39 包 + 映射表）
2. `09_EVENT_PROTOCOL.md` — 事件协议 v2.0.4（11 种事件 + 链式追踪）
3. `10_DATA_MODEL.md` — 数据模型（10 张表完整 Schema）
4. `11_DIAGNOSIS_ENGINE.md` — 诊断引擎 v2.3（四步诊断 + 六态输出）
5. `12_STRATEGY_ENGINE.md` — 策略引擎 v2.0（六态调度 + 安全护栏）
6. `13_PARENT_SUMMARY_RULES.md` — 家长摘要 v2.0（模板 + 风险评分）
7. `14_QUALITY_DASHBOARD.md` — 质量仪表盘 v2.0（24 指标 + badcase 管理）

## 文档版本与状态

| 文件 | 版本 | 状态 | 说明 |
|------|------|------|------|
| `01_PRODUCT_VISION.md` | v2.0.2 | 就绪 ✅ | MVP + 合规 + MCP + 六标志 |
| `02_DEVELOPMENT_ROADMAP.md` | v2.0.0 | 就绪 ✅ | 按现状重写 Stage 1-3 |
| `03_SYLLABUS_SOURCE_RULES.md` | v2.0.0 | 就绪 ✅ | MVP 5-6，1-4 第二阶段 |
| `04_KNOWLEDGE_LEVELING.md` | v2.0.0 | 就绪 ✅ | 全文对齐新课标 4 级，6 维体系已废止 |
| `05_COVERAGE_GATE.md` | v2.0.0 | 就绪 ✅ | 9 铁规 + 17 项整合，D 级门禁新增 |
| `06_KNOWLEDGE_GRAPH.md` | v2.0.0 | 就绪 ✅ | 图谱状态更新，示例 JSON 修正 |
| `07_ERROR_TAXONOMY.md` | v2.0.0 | 就绪 ✅ | L1 中英对照，L2 标注 errorCode |
| `08_STRATEGY_PACKS.md` | v2.1.2 | 就绪 ✅ | 40 策略包 + 编码体系 + 映射表 |
| `09_EVENT_PROTOCOL.md` | v2.0.7 | 就绪 ✅ | 11 事件 + 链式追踪 |
| `10_DATA_MODEL.md` | v2.1.2 | 就绪 ✅ | 10 张表完整 Schema |
| `11_DIAGNOSIS_ENGINE.md` | v2.4.1 | 就绪 ✅ | 四步诊断 + 六态 + 多轮验证 |
| `12_STRATEGY_ENGINE.md` | v2.2.2 | 就绪 ✅ | 六态调度 + 安全护栏 + 中策略定义 |
| `13_PARENT_SUMMARY_RULES.md` | v2.1 | 审查中 | 交叉审查进行中 |
| `14_QUALITY_DASHBOARD.md` | v2.0 | 待审查 | 24 指标 + 9 铁规集成 |

## 数据文件清单

| 文件 | 大小 | 内容 |
|------|------|------|
| `primary_math_g5_g6_knowledge.json` | 521KB | 五/六年级 189 知识点 |
| `primary_math_g1_g4_knowledge.json` | 391KB | 一至四年级 205 知识点 |
| `primary_math_g5_g6_knowledge_graph.json` | 172KB | 五/六年级知识图谱 |
| `primary_math_g1_g4_knowledge_graph.json` | 187KB | 一至四年级知识图谱 |
| `primary_math_g5_g6_levels.json` | 5KB | 五/六年级分级 |
| `primary_math_g1_g4_levels.json` | 68KB | 一至四年级分级 |
| `error_taxonomy.json` | 94KB | 86 错因分类体系 |
| `error_kp_bindings.json` | 332KB | 1390 条知识点-错因绑定 |
| `error_kp_bindings_g5g6_backup.json` | 146KB | G5-G6 绑定备份 |
| `error_kp_bindings_g1g4.json` | 186KB | G1-G4 绑定（778 条） |
| `question_type_matrix.json` | 260KB | 题型规格矩阵 |
| `data_quality_gate.py` | 15KB | 9 铁规门禁脚本 v2.0 |

## 如何跑门禁

```bash
cd /Users/liufeng/Downloads/yaya-browser-v3/acceptance-artifacts
python3 data_quality_gate.py
```

9/9 PASS 表示数据底座健康。任何 FAIL 必须修复后才能改数据文件。

## 当前整体进度

**数据层：95%**（394 KP / 86 错因 / 1390 绑定 / 两层图谱全量建成）
**规则层：95%**（14 份规划文档中：13 份就绪 + 1 份审查中）
**引擎层：50%**（诊断引擎规则完备，策略引擎规则完备，家长摘要规则完备，但均未实现代码）
**实现层：0%**（无后端服务、无前端集成、无真实数据流）
