# 自动化文档生产-审核循环工作流 PRD

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.1 | 2026-05-18 10:08 | liufeng PRD 评审修复 10 项问题 |
| v1.2 | 2026-05-18 10:08 | Writer/Reviewer人设定义、质量评分体系、自我进化机制、独立项目目录 |

---

## 0. 核心概念

### 0.1 一个文档的"合格"标准

一份高质量文档 = 能让人照着写代码
不是检查清单打勾越多越好，而是内容到位。

### 0.2 两个"P"

- **生产P（Writer）**：写文档的人，承担"文档能不能用"的第一责任
- **审核P（Reviewer）**：审文档的人，承担"文档能不能过"的把关责任

两个P各自有独立的角色定位、检查清单、进化路径。不在同一个思考里。

---

## 1. 项目背景

### 1.1 痛点

芽芽项目有16个子系统文档（S01-S16）需要持续生产、审计、迭代。项目当前已暴露出系统性质量问题：

- 文档写完不自检，跨系统引用验证缺失、概念不一致、字段名残留等问题反复出现
- 生产和审核由同一个Agent在同一session内完成，无视角隔离
- 审核流程依赖人工推动，无法自动化
- 多个项目（芽芽、Project Spark、Project Spark Adult）每个都需要独立的文档生产-审核循环
- 此前尝试的kanban调度器方案（76轮dispatch、0 commit落地）被验证为不可靠，本质问题是subagent无持久化能力 + 自报告替代实物验证

### 1.2 为什么需要自动化（不能只靠人工）

- 文档迭代是高频操作——单个文档平均每月迭代3-5个版本
- 审核标准是量化的，重复检查工作可被自动化
- 多个项目并行，人工无法同时跟进全部循环
- 审核的客观性要求：独立审查员的判定不应受写作者的偏见影响

### 1.3 为什么不能简单轮询

- 轮询消耗token——每次空跑约2000-3000 tokens，乘以多个项目、多个profile，日积月累浪费巨大
- 轮询有延迟——最长等待周期决定了响应速度
- 同一台机器上、同一个文件系统内，事件驱动是技术上更合理的选择

---

## 2. 项目目标

### 2.1 核心目标

搭建一个**事件驱动**的自动化文档生产-审核循环工作流，满足：

1. **多项目平行运行**：每个项目独立的生产-审核循环互不干扰
2. **全自动循环**：从backlog到approved，全程无人值守
3. **质量可控**：审核视角独立，迭代轮次有上限，文档封版前走完完整审核流程
4. **低token消耗**：只在实际干活时消耗token，空转成本为0
5. **可监控可恢复**：流程卡死、死循环、数据丢失能被自动发现并暂停

### 2.2 远期目标

工作流模式验证成功后，可将同一套架构复用到**代码开发-审核自动化循环**。同时也以独立项目的形式开源或封装为付费服务，核心卖点是：多Profile隔离 + 自我进化 + 零token空转。

---

## 3. 人设与标准

### 3.1 Writer（生产P）人设

**身份定位**：文档生产者，负责按规范写出可通过审核的详细设计文档。

**必备交付物（7项，缺少任何一项算不合格，reviewer直接退回）**：

1. **核心概念定义**（交付物清单硬性要求）：
   - 数据结构：所有枚举、字段定义、JSON Schema
   - 状态机：完整迁移表（源状态→目标状态→触发条件→后置动作）
   - 接口协议：发出/消费的所有事件类型名、字段结构（或引用S10）

2. **系统冷启动默认值**：AI-MUTABLE参数、信用分、缓存状态的初始值

3. **新实体默认值**：新学生/新知识点/新错因首次进入时的默认参数

4. **异常恢复策略**（覆盖6种场景清单，逐项回答"有/无/不适用"）：
   - 自身进程崩溃重启
   - 自身处理超时（单次操作超过上限）
   - 上游依赖宕机（S01-S08任一不可用）
   - 上游返回格式错误（非宕机，数据不可解析）
   - 数据文件缺失/损坏（不存在、空、格式错）
   - 并发冲突（同一实体两操作同时修改）

5. **与已有系统的交互风险**：依赖哪些子系统、改写/新增接口、交互冲突推演

6. **极端场景验证**：刚启动、崩溃重启、所有依赖同时挂——三项文本推演

7. **跨系统引用落地验证**：每个引用在目标系统中确认存在，引用格式含文件路径

**生产流程（4步，禁跳步）**：
- 第1步：读 NORTH_STAR.md + 相关已有子系统文档（标注了"待本系统定义"的条目）
- 第2步：按模板写初稿
- 第3步：5分钟自检——3极端场景走读 + 硬编码grep清单（见下）+ grep每个跨系统引用是否在另一端有实现
- 第4步：版本号 bump + 变更记录写"变更说明diff"格式，不含日期

**硬编码grep自检清单**：
1. grep 所有AI-MUTABLE参数名，确认每个参数全文只出现一种默认值
2. grep 信用分初始值（"=50"/"= 50"/"初始值=50"），全文一致
3. grep 所有"待 SXX 定义"标记，确认SXX已封版或有兜底策略
4. grep 所有版本号引用（如"S01 v3.1.17"），与目标文档头部一致
5. grep 所有硬编码行号（如"L180"），无残留

**变更记录格式**：
```
<版本号> | <问题编号列表>——<每条问题的修复摘要>
```
示例：`v1.13 | P01-P24——版本号矛盾修正、Phase 0终局措辞统一`

**Writer提交审核时附带的交接上下文**（写在kanban comment或commit message中）：
```
自检声明：
- 本轮修改范围：<改动最大的3个章节>
- 已知遗留问题：<未解决的P3项或Phase2+预留项>
- 自检通过项：7项必备内容/3极端场景/grep清单
```

### 3.2 Reviewer（审核P）人设

**身份定位**：文档质量把关人，有权打回/通过。最终目标是把文档推到"可封版"状态。

**审核覆盖范围（8项必审，缺审算审核不完整）**：

1. **文档完整度**：7项必备章节是否齐全
2. **术语一致性**：同一概念全文使用同一术语（无"知识点"和"技能点"混用）
3. **规则一致性**：同一规则在全文所有出现位置的描述一致（无"信用分=min(三子分)"和"信用分=单一分数"同时出现）
4. **自洽性数学验证**：所有裸数字能从上下文推导？百分比加总=100%？计数与章节数一致？
5. **极端场景**：三种场景推演是否合理
6. **跨系统引用**：每个引用在另一端有实现，引用格式含路径
7. **生产P 2-4项交付物检查**：系统冷启动默认值 / 新实体默认值 / 异常恢复策略 / 交互风险
8. **变更记录规范**：版本号bump、日期占位符未替换（占位符直接打回）

**缺陷分级**：

| 等级 | 定义 | 对状态影响 |
|------|------|-----------|
| P0 | 架构矛盾、安全漏洞、数据丢失风险 | 直接打回，必须修复才能再次提交 |
| P1 | 规则不一致、缺失关键章节（7项之一） | 打回，必须修复才能再次提交 |
| P2 | 术语不一致、格式错误、引用未标注路径 | 允许当前轮次修复后通过，但必须清零才能封版 |
| P3 | 优化建议、可读性、示例不够 | 记录建议，不阻塞流程 |

**P0/P1问题必须附带审核证据**（行号或引用原文），不能只说"有问题"。

**通过条件**：
- **passed**：P0=0 且 P1=0（无论P2/P3多少个）
- **needs_revision**：P0>0 或 P1>0
- **failed**：连续3轮needs_revision仍无法passed → 进入blocked状态

### 3.3 封版标准

**阶段A——审核通过（approved）**
- 条件：P0=0 且 P1=0
- kanban状态：awaiting_review → approved

**阶段B——封版（signed_off）**
- 条件：1) approved 2) P2=0清零（Writer修复，无需再次reviewer审核） 3) liufeng人工终审签字
- 版本号标记：v2.1-locked，锁定标记不是版本号的一部分
- git tag仍是v2.1，仅文档头部标注"封版版本：v2.1-locked"
- 封版后修改：解除-locked → 版本号升为v2.2（不是v2.1-unlocked）

**liufeng终审清单（5分钟可完成）**：
1. 文档头部版本号与变更记录最新版本号一致
2. 变更记录最新条目日期与git log最后一次commit日期一致
3. 所有"待SXX定义"标记对应的目标文档已封版或有兜底策略
4. 自检声明中的计数与实际一致
5. P2=0确认

---

## 4. 架构设计

### 4.1 总体架构

```
三个独立Hermes Profile

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   writer        │    │   reviewer      │    │   watcher       │
│   (生产文档)     │    │   (审核文档)     │    │   (监控健康)     │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ Profile: yaya   │    │ Profile:        │    │ Profile:        │
│                 │    │ yaya-reviewer   │    │ yaya-watcher    │
│ Model: deepseek-│    │ Model: deepseek-│    │ (no_agent脚本,  │
│   reasoner      │    │   v4-pro        │    │  或daemon进程)  │
│ Cron: project-  │    │ Cron: review-   │    │ Daemon:         │
│   watch         │    │   yaya-zhujiao  │    │ watchdog监听   │
│ (no_agent脚本,  │    │ (完整agent,     │    │ (launchctl管理) │
│  0 token空转)   │    │  被触发启动)    │    │                 │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         │    共用同一文件系统                           │
         ▼                      ▼                      ▼
    ┌─────────────────────────────────────────────────────────┐
    │                    /Users/liufeng/Documents/             │
    │                    DocProductionReview/                  │
    │    ├── projects/             各项目的文档目录             │
    │    │   ├── yaya-zhujiao/                                │
    │    │   ├── project-spark/                               │
    │    │   └── project-spark-adult/                          │
    │    ├── audit-reports/        审核报告目录                │
    │    ├── .kanban/              kanban board               │
    │    ├── evolution_rules.yaml  自我进化规则                │
    │    └── reusable-review-rules/ 可复用检测规则             │
    │        ├── vale/             Vale规则集                 │
    │        ├── markdownlint/     markdownlint规则集          │
    │        └── wrapper.py        统一调用入口                │
    └─────────────────────────────────────────────────────────┘
```

### 4.2 目录结构说明

项目独立于任何具体业务系统（如芽芽AI助教）。每个被服务的项目放在 `projects/` 目录下。Writer和Reviewer通过项目名来区分工作内容。

### 4.3 三个Profile的分工

#### 4.3.1 Writer Profile (yaya)

**职责**：扫描kanban board，发现有backlog或needs_revision的task时，启动写作会话。

**运作方式**：
- 注册一个cron job `project-watch`，no_agent=True（脚本模式）
- 脚本内容：读每个项目的`.kanban/board.db`，扫描task状态
- 发现活后：用subprocess启动`hermes chat -q "..."`执行写作任务
- 写作任务内：读需求 -> 写文档 -> git commit -> 实物验证（查git log、git diff、grep关键概念）
- 验证通过后：执行`HERMES_PROFILE=yaya-reviewer hermes cron run review-<project>`触发reviewer
- 更新kanban状态为`awaiting_review`
- Writer自检时调用 `reusable-review-rules/wrapper.py` 自动跑 Vale + markdownlint

**写完后通知reviewer的机制**：
```bash
HERMES_PROFILE=yaya-reviewer hermes cron run review-yaya-zhujiao
```
不依赖reviewer的gateway是否运行；不消耗writer的token（只是进程间调用）；reviewer用自己的模型独立工作。

#### 4.3.2 Reviewer Profile (yaya-reviewer)

**职责**：被writer触发后，扫描kanban中的awaiting_review任务，按updated_at最旧优先处理，执行完整审核。

**配置**：
- 模型：deepseek-v4-pro（与writer的deepseek-reasoner完全隔离）
- 记忆：独立session，不受writer写作历史污染
- 技能：独立的skill集（审计技能，不含写作技能）

**运作方式**：
- 注册cron job：`review-yaya-zhujiao`等，完整agent模式（no_agent=False）
- 被writer的`hermes cron run`触发
- 读文档 -> 按审计标准逐条检查 -> 写审计报告到audit-reports/ -> 更新kanban状态
- 审核完成后，如果进入approved状态，watcher自动触发质量评分

#### 4.3.3 Watcher Profile (yaya-watcher)

**职责**：实时监控整个工作流的健康状态。

**运作方式**：
- 后台daemon进程，Python watchdog库监听文件系统事件
- 监听事件：kanban board写入、文档目录变更、审计报告变更
- 事件触发后执行4个看门狗检测（卡死/死循环/数据丢失/Token超支）
- daemon通过launchctl管理，自动启动、崩溃自拉、日志记录
- 0 token消耗（纯Python脚本）

---

## 5. 状态机与工作流

### 5.1 Kanban Board

每个项目一个独立的kanban board，用SQLite文件存储在项目根目录的`.kanban/board.db`。

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'backlog',
    assigned_to TEXT,
    project TEXT NOT NULL,
    file_path TEXT,
    version TEXT,
    commit_sha TEXT,
    iteration_count INTEGER DEFAULT 0,
    tokens_budget INTEGER,
    tokens_spent INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT,
    blocked_reason TEXT,
    blocked_recovery_target TEXT
);

CREATE TABLE task_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    author TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE TABLE quality_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    version TEXT NOT NULL,
    compliance_score REAL,       -- 合规分 (0-100)
    ai_quality_score REAL,      -- AI质量分 (0-100)
    defect_trend_score REAL,    -- 缺陷趋势分 (0-100)
    total_score REAL,           -- 总分
    scored_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE TABLE evolution_suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,         -- writer / reviewer
    task_id TEXT NOT NULL,
    round_number INTEGER NOT NULL,
    tech_description TEXT NOT NULL,  -- 技术描述（规则本身）
    recommendation TEXT NOT NULL,    -- 生效建议+理由
    plain_explanation TEXT NOT NULL, -- 大白话
    status TEXT DEFAULT 'pending',  -- pending / approved / rejected
    decided_by TEXT,
    decided_at TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
```

### 5.2 六状态状态机

```
backlog ──→ drafting ──→ awaiting_review ──→ needs_revision ──→ approved ──→ signed_off
                ↑                                  ↑
           writer开始写                       reviewer审不过
            (3轮上限)                         writer修完再提审

blocked ←──── 任意状态 (watcher发现异常 / 3轮上限 / token超支)
```

| 状态 | 含义 | 谁处理 | 触发条件 |
|------|------|--------|----------|
| backlog | 待写作 | writer | liufeng创建task或cron扫描发现 |
| drafting | 写作中 | writer | writer claim后立即设置 |
| awaiting_review | 等待审核 | reviewer | writer完成 + 实物验证通过后触发 |
| needs_revision | 需要修改 | writer | reviewer判定不过 + 附问题清单 |
| approved | 审核通过 | reviewer | reviewer判定通过 |
| signed_off | 封版 | **liufeng手动** | liufeng亲自确认 |
| blocked | 卡死 | watcher / liufeng | 异常 / 3轮上限 / token超支 |

### 5.3 状态迁移验证关卡

每个状态迁移前必须通过验证，防止自报告替代实物验证。

**drafting → awaiting_review 验证关卡**：
```
1. writer 执行 git add + git commit
2. writer 执行 git log -3，确认有新commit
3. writer 执行 git diff HEAD~1，确认文件内容有实质变化
4. writer grep 关键概念（跨系统引用、协议字段等），确认完整
5. 调用 reusable-review-rules/wrapper.py 自动跑 Vale + markdownlint
6. 全部通过 → 触发 reviewer
   任意一项失败 → 进入 blocked，comment写失败原因
```

**awaiting_review → approved/needs_revision 验证关卡**：
```
1. reviewer 完整读文档
2. reviewer 按审计模板检查（8项必审）
3. reviewer 写审计报告到 audit-reports/ 目录
4. reviewer 写comment包含：问题逐条清单 + 严重等级 + 文档行号 + 审核证据
5. 判定通过 → 更新为 approved，触发生成 quality_scores
   判定不通过 → 更新为 needs_revision，在comment中写问题清单
```

---

## 6. 通知机制（事件驱动，零轮询）

### 6.1 Writer → Reviewer 通知

Writer完成写作并验证通过后，执行：
```bash
HERMES_PROFILE=yaya-reviewer hermes cron run review-<project>
```

跨profile调用不消耗writer的token。`hermes cron run`是CLI命令，不经过LLM。

### 6.2 Reviewer → Writer 通知

Reviewer判定不通过时，通过kanban board状态更新来通知writer。Writer的`project-watch` cron job在no_agent脚本扫描到`needs_revision`且`assigned_to=writer`的task时接手修改。

### 6.3 Watcher 通知

Watcher检测到异常时：
1. 暂停writer和reviewer的相关cron job（`hermes cron pause <job_id>`）
2. 写alert文件到项目`.kanban/.alerts/`目录
3. 通过launchctl日志通道输出

---

## 7. 监控机制（Watchdog）

### 7.1 Watcher Daemon 架构

Python watchdog daemon，launchctl管理，监听 .kanban/board.db / subsystems/ / audit-reports/ 的文件事件。事件触发后执行4个看门狗检测。

### 7.2 四个看门狗

#### 7.2.1 看门狗1：卡死检测

如果task在 drafting 或 awaiting_review 状态下，updated_at 超过以下阈值且无进展：
- 文档 < 500 行：45分钟
- 文档 500-800 行：90分钟
- 文档 > 800 行：150分钟

#### 7.2.2 看门狗2：死循环检测

如果 task.iteration_count >= 3 → blocked

#### 7.2.3 看门狗3：数据丢失检测

如果 kanban 状态与实际文件不一致（如 awaiting_review 但文件不存在）→ 检查git历史 → 有则checkout恢复，无则回退状态

#### 7.2.4 看门狗4：Token超支检测

如果 task.tokens_spent > task.tokens_budget * 1.5 → blocked

### 7.3 Watcher 自我监控

1. launchctl自动重启
2. 每次启动时写入`.kanban/watcher_started.json`
3. 每30分钟写入心跳文件`.kanban/watcher_heartbeat.json`

---

## 8. 质量保障策略

### 8.1 Writer侧质量策略

**策略1：写作前加载自查清单**。Writer开始写作前，加载7项必备交付物清单 + 硬编码grep清单。

**策略2：写作后实物验证**。三样验证（git log / git diff / grep关键概念）+ 调用 reusable-review-rules/wrapper.py。

### 8.2 Reviewer侧质量策略

**策略3：审计模板**。每条问题必须包含：编号、严重等级、类别、问题描述（含行号/引用原文）、修复建议。

**策略4：单轮问题全量输出**。Reviewer一次审核必须输出所有发现的问题，不能分批。

### 8.3 流程级质量策略

**策略5：3轮循环上限**。reviewer判定needs_revision时iteration_count+1，达到3轮自动blocked。

**策略6：Token预算制度**。Writer和reviewer在各自会话结束前必须更新kanban的tokens_spent字段。

**策略7：审计报告独立存档**。每次审核结果写入 `audit-reports/<编号>_audit_report_v<版本>.md`。

### 8.4 质量评分体系

在文档被approved后，由watcher触发自动评分，写入quality_scores表。评分由三部分组成：

**总分 = 合规分 × 0.4 + AI质量分 × 0.4 + 缺陷趋势分 × 0.2**

#### 合规分（自动化计算，0 token成本）

| 指标 | 计算方式 | 满分 |
|------|---------|------|
| 必备章节完整度 | 7项必备内容实际有几项 | 20 |
| 跨引用准确率 | 认领的Sxx引用在目标文档头部版本号一致比例 | 20 |
| 默认值一致性 | AI-MUTABLE字段最多出现几个不同值的倒数 | 20 |
| 极端场景覆盖率 | 3个场景中实际覆盖几个 | 20 |
| 变更记录合规 | 版本号/日期/格式都对齐给分，不对齐0 | 20 |

#### AI质量分（文档approved后自动化执行，约10K tokens）

AI独立阅读全文（不是reviewer的同一思考），对5个维度分别评分，每个维度1-5分，换算为百分制：

1. **可操作性**：如果让一个新工程师照着这篇文档写代码，他能不能不跑回来问问题就写出来？
2. **异常覆盖度**：文档提到的各种意外情况（崩溃/超时/数据丢失/格式错误）是否都有考虑和方案？
3. **决策可追溯**：每个重要设计决定有没有说明"为什么这么做，而不是那么做"？
4. **外部一致性**：引用的其他系统的信息，与其他系统当前版本是否对得上？
5. **内部自洽**：同一个信息出现在不同章节，说法是否一致？

评分完成后，AI质量分写入quality_scores表。如果AI质量分与合规分相差超过40分（如合规分95但AI质量分45），触发一条"质量偏差警告"写入watcher日志，提示owner关注"文档规范化程度高但实质质量低"的情况。

#### 缺陷趋势分（自动化计算，0 token成本）

追踪同一文档在各版本间的P0/P1/P2数量变化：
- 首版基线：0分（无论如何，第一版缺陷数量不扣分也不加分）
- 后续版本：每轮下降一个P0/P1 -> 加分；上升 -> 扣分
- 计算方式：`(首版P0计数 - 当前版P0计数) × 10 + (首版P1计数 - 当前版P1计数) × 5`

#### 评分的使用方式

- 不作为通过/不通过的决策依据（通过与否由reviewer判定）
- 作为owner观察质量趋势的工具
- liufeng每几周抽样一份文档，亲自阅读后与AI评分对比，验证评分可靠性
- 如果长期发现AI质量分与人工判断偏差过大，调整AI质量分的问题权重或替换问题

### 8.5 自我进化机制

#### 进化的触发时机

每轮文档达到approved后（writer提交、reviewer审完、修改后通过验收的闭环完成），触发一次进化总结。一次就过的文档也触发，但内容不同——只总结"为什么没问题，是质量好还是审得不够深"。

#### Writer的回顾

Writer回顾本轮被提出的问题清单（从kanban comment和审计报告中提取），回答以下问题：
- 这轮被提了多少条问题？P0/P1/P2各多少？
- 哪些问题是我在自检时就应该能发现但没发现的？为什么？
- 有没有某个章节或某类问题反复被提？说明我在那个领域有系统性盲区
- 总结一条：我需要在自检清单里多加一句什么检查？

#### Reviewer的回顾

Reviewer回顾本轮审核过程，回答以下问题：
- 这轮我给出的问题清单里，有多少是第二轮才发现（第一轮漏掉）的？
- 漏掉的那些有没有共同模式？（都是从极端场景章节漏的？都是跨系统引用没去验证？）
- 有没有哪条我给了P2但writer改了之后造成了更大的P0？说明我低估了那条问题的严重性
- 总结一条：我需要在审计模板里多加什么检查项？或调整什么问题的P等级？

#### 进化规则的管理

进化规则集中在项目根目录的 `evolution_rules.yaml` 文件中，不做两份分开管理。规则分两段：

```yaml
pre_flight:  # 提交前的检查，writer执行
  - id: "evo-001"
    check: "信用分初始值一致"
    grep_pattern: "初始值="
    p_level: P0
    plain_explanation: "信用分在全文只有一个初始值，就像报名表的手机号在每一页必须一样"
    added_by: "writer回顾"
    hit_count: 3          # 最近100轮中命中的次数
    total_rounds: 12      # 从加人到现在经过的轮数
    last_hit_round: "yaya-s08-v4"

post_flight:  # 审核阶段的检查，reviewer执行
  - id: "evo-002"
    check: "信用分初始值一致性验证"
    description: "验证writer已检查过此条"
    verify_method: "grep全文，确认没有矛盾值"
    p_level: P0
    added_by: "reviewer回顾"
    hit_count: 3
    total_rounds: 12
    last_hit_round: "yaya-s08-v4"
```

两条规则（pre_flight + post_flight）的ID配对，一并启用或一并停用，保证Writer和Reviewer同步进化。

#### 进化建议的三字段格式

每条进化建议提交到 owner（系统owner）时，必须包含三个字段：

```
字段1：技术描述（规则本身的技术表达）
  例："在self_check_patterns加一条：grep所有'初始值='字段，确认每次出现的是同一数值"

字段2：建议 + 理由（推荐生效/不生效 + 为什么）
  例："推荐生效。信用分初始值在S08§3.1=50，§4.2=65，§6.7=50，三次出现两个不同值
       若自检时有grep规则可在提交前拦截，减少一轮返工。"

字段3：大白话（不用技术术语，让非技术人员能看懂）
  例："就像填报名表，你的手机号在报名表第一页、第二页、第三页各填了一次，
       但三个号码不一样。这表交上去别人不知道该打哪个电话找你。
       加一条自动检查，确保同一个信息在全文中只出现一个值。"
```

Owner看大白话理解问题，看建议+理由决定是否采纳。P等级单独标注在配置文件中，不做大白话翻译。

#### 进化规则的生命周期

- 每条规则记录"最近100轮命中次数"（hit_count）和"总轮数"（total_rounds）
- 如果一条规则连续50轮无命中，标记为"过时"（stale），owner决定是否删除
- 规则不自动生效力。owner在kanban board的 "进化建议" 任务中定期（每周或每两周）查看pending建议，手工点击 approve / reject

---

## 9. Token消耗控制

### 9.1 零空转设计

| 组件 | 运作方式 | 空转成本 |
|------|----------|----------|
| writer的`project-watch` | no_agent脚本模式，读SQLite | 0 token |
| reviewer的`review-*` | 完整agent，但只被触发时才启动 | 0 token（不触发不消耗） |
| watcher daemon | Python watchdog进程，不经过LLM | 0 token |
| 通知机制 | `hermes cron run` CLI命令 | 0 token |
| AI质量评分 | approved后触发一次，约10K tokens | 10K tokens/文档 |
| 进化回顾 | approved后触发一次，约5K tokens | 5K tokens/轮 |

### 9.2 预算管控

每个task在创建时预估token消耗，超出50%自动blocked。参考值：
- 写一个子系统文档（400-1000行）：预算 150万-300万 tokens
- 审核一次：预算 50万-100万 tokens
- 一轮完整循环（1写+1审）：预算 200万-400万 tokens

### 9.3 逃生节省

同一task迭代第3轮时，writer的prompt中嵌入提示：
"当前是第3轮迭代。请重点检查前两轮reviewer标记的每一条问题是否全部修复。如果本轮仍然无法通过，task将自动blocked。"

---

## 10. 异常处理与恢复

### 10.1 异常分类

| 类型 | 检测者 | 自动处置 | 需要人工 |
|------|--------|----------|----------|
| task卡死 | watcher | 暂停cron + alert | 接入分析原因 |
| task循环3轮 | watcher | 暂停 + blocked + alert | 判断是需求问题还是质量太差 |
| 文件丢失 | watcher | 回退状态 + 暂停 + alert | 决定重写还是恢复备份 |
| Token超支 | watcher | 暂停 + blocked + alert | 调整预算或降低质量要求 |
| Watcher自身挂掉 | launchctl | 自动重启 | 检查心跳是否正常 |
| 质量偏差（质量分差>40） | watcher | 写入alert日志 | 抽查文档判断评分的偏差源 |

### 10.2 恢复流程

watcher 发现异常 → 暂停writer/reviewer的cron job → 写alert → 输出日志 → liufeng介入分析 → 按异常类型选择恢复路径。

---

## 11. 实现计划

### Phase 1：基础设施（预计 1-2 天）
1. 创建项目目录结构（已完成）
2. 创建evolution_rules.yaml初始模板
3. 实现no_agent watch脚本（30行Python，扫描SQLite）
4. 编写reusable-review-rules/wrapper.py（调用Vale + markdownlint）
5. 注册writer的cron job

### Phase 2：核心循环（预计 2-3 天）
6. 实现kanban SQLite操作
7. 实现Writer写作流程（读取task → 写作 → 自检 → 提交 → 通知reviewer）
8. 实现Reviewer审核流程（被触发 → 审核 → 输出审计报告 → 更新状态）
9. 实现Writer→Reviewer通知（HERMES_PROFILE=... hermes cron run）
10. 放置测试task，跑通第一轮完整循环

### Phase 3：质量与监控（预计 2-3 天）
11. 实现Watcher daemon（Python watchdog + 4个看门狗）
12. 实现质量评分体系（合规分 + AI质量分 + 缺陷趋势分）
13. 实现自我进化机制（提议生成 + evolution_rules.yaml更新）
14. launchctl管理

### Phase 4：打磨与扩展
15. 扩展到Project Spark、Project Spark Adult
16. 进化机制验证（跑5-10轮后，比较P0/P1数量的趋势）
17. 如果进化有效，将workflow package成可复用的模板
