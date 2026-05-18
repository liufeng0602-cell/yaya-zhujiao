# 自动化文档生产-审核循环工作流 PRD v2.1

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v2.1 | 2026-05-18 12:55 | 18项审核问题修复：p2_clearing状态/iteration_count对齐/failed合并blocked/blocked恢复路径枚举/Writer-Reviewer检查区分/自检增第6项/AI评分分差阻断/ wrapper.py定义/Watcher竞态锁/Token中间预警/Profile权限边界/规则scope字段/部署脚本改托管配置/task_comments加iteration字段/跨文档版本兼容/日期表述统一/终审增否决权/Watcher项目隔离 |
| v2.0 | 2026-05-18 12:43 | 第一完整版 PRD：Writer/Reviewer 人设标准、质量评分体系、自我进化机制、商业化开源策略、三层愿景展望 |
| v1.2 | 2026-05-18 10:08 | Writer/Reviewer 人设定义、质量评分体系、自我进化机制、独立项目目录 |
| v1.1 | 2026-05-18 10:08 | liufeng PRD 评审修复 10 项问题 |

---

## 0. 核心概念

### 0.1 这个项目是什么

一套自动化的文档生产-审核循环工作流。它不是文档编辑器，不是模板工具，而是一个 "写+审=交付" 的自动化流水线。

三个角色（三个独立的 Hermes Profile）分别承担不同职责：

- 生产P（Writer）：写文档的人，承担 "文档能不能用" 的第一责任
- 审核P（Reviewer）：审文档的人，承担 "文档能不能过" 的把关责任
- 监控P（Watcher）：监控循环健康的人，承担 "循环有没有死" 的预警责任

两个P各自有独立的角色定位、检查清单、进化路径。不在同一个思考里。

### 0.2 一个文档的 "合格" 标准

一份高质量文档 = 能让人照着写代码。不是检查清单打勾越多越好，而是内容到位。

### 0.3 本项目的定位

独立于任何具体业务系统（如芽芽AI助教、Project Spark）。是一个通用的文档生产-审核服务。任何项目（产品 PRD、技术设计文档、规范文档）都可以接入走这套流程。

核心创新点：多 Profile 隔离 + 自我进化 + 零 token 空转。

### 0.4 项目与商业的关系

项目本身服务于多个团队的文档质量需求。成熟后可以走开源+商业双轨：核心框架开源，增值服务（质量评分 API、预置规则包、质量趋势仪表盘、托管配置服务）付费。核心壁垒是积累的审核规则集，不是架构代码。

---

## 1. 项目背景

### 1.1 痛点

芽芽项目有16个子系统文档（S01-S16）需要持续生产、审计、迭代。项目当前已暴露出系统性质问题：

- 文档写完不自检，跨系统引用验证缺失、概念不一致、字段名残留等问题反复出现
- 生产和审核由同一个 Agent 在同一 session 内完成，无视角隔离
- 审核流程依赖人工推动，无法自动化
- 多个项目（芽芽、Project Spark、Project Spark Adult）每个都需要独立的文档生产-审核循环
- 此前尝试的 kanban 调度器方案（76轮 dispatch、0 commit 落地）被验证为不可靠，本质问题是 subagent 无持久化能力 + 自报告替代实物验证

### 1.2 为什么需要自动化

- 文档迭代是高频操作——单个文档平均每月迭代3-5个版本
- 审核标准是量化的，重复检查工作可被自动化
- 多个项目并行，人工无法同时跟进全部循环
- 审核的客观性要求：独立审查员的判定不应受写作者的偏见影响

### 1.3 为什么不能简单轮询

- 轮询消耗 token——每次空跑约2000-3000 tokens，乘以多个项目、多个 profile，日积月累浪费巨大
- 轮询有延迟——最长等待周期决定了响应速度
- 同一台机器上、同一个文件系统内，事件驱动是技术上更合理的选择

---

## 2. 项目目标

### 2.1 核心目标

搭建一个事件驱动 + 多 Profile 隔离 + 自我进化的自动化文档生产-审核循环工作流，满足：

1. 多项目平行运行：每个项目独立的生产-审核循环互不干扰
2. 全自动循环：从 backlog 到 approved，全程无人值守
3. 质量可控：审核视角独立，迭代轮次有上限，文档封版前走完完整审核流程
4. 低 token 消耗：只在实际干活时消耗 token，空转成本为 0
5. 可监控可恢复：流程卡死、死循环、数据丢失能被自动发现并暂停

### 2.2 三层愿景

愿景分三层，逐层扩展：

**第一层：子系统设计文档（当前阶段）**
面向技术团队内部。S01-S16 子系统设计文档的自动化生产-审核-封版。本 PRD 即为此层设计。

**第二层：产品 PRD + 技术设计文档**
面向产品和技术协作。非技术人员说出想法 -> 系统问问题对齐认知 -> 生成完整产品 PRD -> 拆分为模块 PRD -> 每个模块走生产-审核-封版循环。产品 PRD 全部封版后，自动生成技术设计文档，再走一遍循环，直到技术文档封版。

**第三层：开发实现（不做代码审核，做文档交付）**
产品 PRD 和技术设计文档全部封版后，输出给 Claude Code、Cursor 等 IDE 做开发。项目自己不做代码写、审循环。

### 2.3 远期目标

工作流模式验证成功后，可将同一套架构复用到代码开发-审核自动化循环。同时也以独立项目的形式开源或封装为付费服务，核心卖点是：多 Profile 隔离 + 自我进化 + 零 token 空转。

---

## 3. 人设与标准

### 3.1 Writer（生产P）人设

身份定位：文档生产者，负责按规范写出可通过审核的详细设计文档。

**必备交付物（7项，缺少任何一项算不合格，reviewer 直接退回）：**

1. 核心概念定义（交付物清单硬性要求）：
   - 数据结构：所有枚举、字段定义、JSON Schema
   - 状态机：完整迁移表（源状态->目标状态->触发条件->后置动作）
   - 接口协议：发出/消费的所有事件类型名、字段结构（或引用 S10）

2. 系统冷启动默认值：AI-MUTABLE 参数、信用分、缓存状态的初始值

3. 新实体默认值：新学生/新知识点/新错因首次进入时的默认参数

4. 异常恢复策略（覆盖6种场景清单，逐项回答"有/无/不适用"）：
   - 自身进程崩溃重启
   - 自身处理超时（单次操作超过上限）
   - 上游依赖宕机（S01-S08 任一不可用）
   - 上游返回格式错误（非宕机，数据不可解析）
   - 数据文件缺失/损坏（不存在、空、格式错）
   - 并发冲突（同一实体两操作同时修改）

5. 与已有系统的交互风险：依赖哪些子系统、改写/新增接口、交互冲突推演

6. 极端场景验证：刚启动、崩溃重启、所有依赖同时挂——三项文本推演

7. 跨系统引用落地验证：每个引用在目标系统中确认存在，引用格式含文件路径

**生产流程（4步，禁跳步）：**
- 第1步：读 NORTH_STAR.md + 相关已有子系统文档（标注了"待本系统定义"的条目）
- 第2步：按模板写初稿
- 第3步：5分钟自检——自检查"有没有写"（7项必备内容是否都有覆盖），不是检查"写得对不对"（那是reviewer的事）。执行硬编码 grep 清单（见下）。
- 第4步：版本号 bump + 变更记录写"变更说明diff"格式

**硬编码 grep 自检清单：**
1. grep 所有 AI-MUTABLE 参数名，确认每个参数全文只出现一种默认值
2. grep 信用分初始值（"=50"/"= 50"/"初始值=50"），全文一致
3. grep 所有"待 SXX 定义"标记，确认 SXX 已封版或有兜底策略
4. grep 所有版本号引用（如"S01 v3.1.17"），与目标文档头部一致
5. grep 所有硬编码行号（如"L180"），无残留
6. 确认已读取 NORTH_STAR.md：在自检声明中列出 NORTH_STAR 中标注的"待本系统定义"条目清单，确认已阅读

**变更记录格式：**
"<版本号> | <问题编号列表>——<每条问题的修复摘要>"
示例："v1.13 | P01-P24——版本号矛盾修正、Phase 0 终局措辞统一"

变更记录中不写日期。日期仅在文档头部的封版标记中出现，从 git log 取真实提交时间。

**Writer 提交审核时附带的交接上下文（写在 kanban comment 或 commit message 中）：**
```
自检声明：
- 本轮修改范围：<改动最大的3个章节>
- 已知遗留问题：<未解决的 P3 项或 Phase 2+ 预留项>
- 自检通过项：7项必备内容/3极端场景/grep清单
- NORTH_STAR 待定义条目已阅读：<列出条目>
```

### 3.2 Reviewer（审核P）人设

身份定位：文档质量把关人，有权打回/通过。最终目标是把文档推到"可封版"状态。

**审核覆盖范围（8项必审，缺审算审核不完整）：**

1. 文档完整度：7项必备章节是否齐全
2. 术语一致性：同一概念全文使用同一术语（无"知识点"和"技能点"混用）
3. 规则一致性：同一规则在全文所有出现位置的描述一致（无"信用分=min(三子分)"和"信用分=单一分数"同时出现）
4. 自洽性数学验证：所有裸数字能从上下文推导？百分比加总=100%？计数与章节数一致？
5. 极端场景推演是否合理（不是检查"有没有写"，而是检查"写得对不对"）
6. 跨系统引用：每个引用在另一端有实现，引用格式含路径
7. 生产P 2-4项交付物检查：系统冷启动默认值 / 新实体默认值 / 异常恢复策略 / 交互风险
8. 变更记录规范：版本号 bump、变更记录中不应出现日期（日期占位符应无，如有则打回）

**缺陷分级：**

| 等级 | 定义 | 对状态影响 |
|------|------|-----------|
| P0 | 架构矛盾、安全漏洞、数据丢失风险 | 直接打回，必须修复才能再次提交 |
| P1 | 规则不一致、缺失关键章节（7项之一） | 打回，必须修复才能再次提交 |
| P2 | 术语不一致、格式错误、引用未标注路径 | 允许当前轮次修复后通过，但必须清零才能封版 |
| P3 | 优化建议、可读性、示例不够 | 记录建议，不阻塞流程 |

P0/P1 问题必须附带审核证据（行号或引用原文），不能只说"有问题"。

**通过条件：**
- passed：P0=0 且 P1=0（无论 P2/P3 多少个）
- needs_revision：P0>0 或 P1>0
- blocked（max_iterations_exceeded）：连续3轮 needs_revision 仍无法 passed

### 3.3 封版标准

**阶段A——审核通过（approved）**
- 条件：P0=0 且 P1=0
- kanban 状态：awaiting_review -> approved
- 此时可能仍有 P2 问题未清零

**阶段A.5——P2 清零（p2_clearing）**
- 触发条件：approved 后仍有 P2 问题残留
- 谁处理：writer
- 动作：仅修复 P2 问题（不改文档结构、不改逻辑），修完后直接标记 p2_cleared
- 不需要再次提交 reviewer 审核（P2 不阻塞流程）
- 如果 writer 在修 P2 时发现需要改变文档结构或逻辑，必须回退到 needs_revision 状态重新提交 reviewer

**阶段B——封版（signed_off）**
- 条件：1) approved 且 P2=0（p2_cleared） 2) liufeng 人工终审签字
- 版本号标记：v2.1-locked，锁定标记不是版本号的一部分
- git tag 仍是 v2.1，仅文档头部标注"封版版本：v2.1-locked"
- 封版后修改：解除 -locked -> 版本号升为 v2.2（不是 v2.1-unlocked）

**liufeng 终审清单（5分钟可完成）：**
1. 文档头部版本号与变更记录最新版本号一致
2. 变更记录最新条目不包含日期（或日期与 git log 最后一次 commit 日期一致——看具体实现方案）
3. 所有"待 SXX 定义"标记对应的目标文档已封版或有兜底策略
4. 自检声明中的计数与实际一致
5. P2=0 确认
6. （一票否决权）liufeng 读到任何逻辑错误或质量不达标，有权直接 blocked（需附否决原因）

---

## 4. 架构设计

### 4.1 总体架构

三个独立 Hermes Profile 共用同一文件系统。项目路径：/Users/liufeng/Documents/DocProductionReview/

```
DocProductionReview/
├── projects/             各项目的文档目录
│   ├── yaya-zhujiao/
│   ├── project-spark/
│   └── project-spark-adult/
├── audit-reports/        审核报告目录
├── .kanban/              kanban board + alert 文件
├── evolution_rules.yaml  自我进化规则
└── reusable-review-rules/ 可复用检测规则（Vale + markdownlint + wrapper.py）
```

### 4.2 三个 Profile 的分工

**Writer Profile (yaya)**
- 职责：扫描 kanban board，发现 backlog 或 needs_revision 的 task 时启动写作
- cron job：project-watch，no_agent=True（脚本模式，0 token 空转）
- 写作流程：读需求->写文档->自检（含 wrapper.py 调 Vale/markdownlint）->git commit->实物验证->触发 reviewer->更新 kanban
- Writer 自检时自动调 wrapper.py 跑语法检查
- **权限边界**：写权限：projects/ 目录、audit-reports/ 目录（写自检报告）、.kanban/（更新 task 状态和 comment）。读权限：evolution_rules.yaml。无权限：修改 reviewer 的配置或记忆

**Reviewer Profile (yaya-reviewer)**
- 职责：被 writer 触发后扫描 awaiting_review 任务，按 updated_at 最旧优先处理
- 模型：deepseek-v4-pro（与 writer 的 deepseek-reasoner 完全隔离）
- 记忆和技能独立于 writer
- 审核流程：读文档->按8项必审检查->写审计报告->更新 kanban 状态
- 文档进入 approved 后，watcher 自动触发质量评分
- **权限边界**：读权限：projects/ 目录下的被审核文档。写权限：audit-reports/（写审计报告）、.kanban/（更新 task 状态和 comment）。无权限：修改文档文件本身。发现错别字或格式问题，标注 P2 让 writer 改，不直接修改文档

**Watcher Profile (yaya-watcher)**
- 职责：实时监控工作流健康
- 后台 daemon 进程，Python watchdog 监听文件系统事件
- 4个看门狗：卡死检测 / 死循环检测 / 数据丢失检测 / Token 超支检测
- daemon 通过 launchctl 管理，自动启动、崩溃自拉、0 token 消耗
- **权限边界**：读权限：.kanban/（读 task 状态）。写权限：.kanban/.alerts/（写 alert 文件）。暂停/恢复 cron job 的权限。无权限：修改 projects/ 下的文档或 audit-reports/ 下的报告。文件丢失检测执行 git checkout 前必须检查 kanban 中该文档是否处于 drafting 状态——是则只报警不做 checkout（防止与 Writer 正在写作产生竞态）

### 4.3 Watcher 的多项目隔离策略

每个被服务的项目有自己独立的 watcher 实例。芽芽项目的 watcher 只暂停/恢复芽芽项目的 cron job，不影响 Project Spark 的正常流程。

### 4.4 多 Profile 架构 vs 现有工具的差异化优势

| 维度 | 现有工具（Vale/Qodo/CodeRabbit/Danger） | 本系统 |
|------|----------------------------------------|--------|
| 检查层 | 语法层（规则匹配） | 语义层（理解架构意图） |
| 文档生成 | 不生成，仅检测 | Writer 从 NORTH_STAR 推理生成 |
| 极端场景推演 | 不做 | Reviewer 强制检查3种极端场景 |
| 角色隔离 | 单 agent | 三 profile 独立模型/记忆/技能/工具权限 |
| 空转消耗 | CI 排队/轮询消耗 token | 0 token 空转（事件驱动） |
| 进化能力 | 规则手工更新 | 自动总结+owner 审核生效 |

Vale/markdownlint 在语法层用零 token 瞬间跑完，本系统不自竞争语法层，而是将它们的检查能力嵌在 writer 自检步骤中（wrapper.py 调用）。深层质量检查（架构一致、逻辑自洽、极端场景）是 profile 的核心价值。

---

## 5. 状态机与工作流

### 5.1 Kanban Board

每个项目一个独立的 kanban board，使用 SQLite 文件，核心表结构：

- tasks：id, title, status, assigned_to, project, file_path, version, commit_sha, iteration_count, tokens_budget, tokens_spent, created_at, updated_at, blocked_reason, blocked_recovery_target
- task_comments：task_id, author, content, created_at, **iteration_number**（标记这条评论属于第几轮迭代，方便回溯）
- quality_scores：task_id, version, compliance_score, ai_quality_score, defect_trend_score, total_score
- evolution_suggestions：source, task_id, round_number, tech_description, recommendation, plain_explanation, status

### 5.2 状态机与迁移图

```
backlog -> drafting -> awaiting_review -> needs_revision -> approved -> p2_clearing -> signed_off
                ↑                             ↑
           writer开始写                  reviewer审不过
           (3轮上限)                    writer修完再提审

p2_clearing -> approved（如果修P2过程中需要改逻辑）
blocked <- 任意状态（watcher发现异常/3轮上限/token超支/连续3轮审核不过）
```

| 状态 | 含义 | 谁处理 | 触发条件 |
|------|------|--------|----------|
| backlog | 待写作 | writer | liufeng 创建 task 或 cron 扫描发现 |
| drafting | 写作中 | writer | writer claim 后立即设置 |
| awaiting_review | 等待审核 | reviewer | writer 完成 + 实物验证通过后触发 |
| needs_revision | 需要修改 | writer | reviewer 判定不过 + 附问题清单 |
| approved | 审核通过 | reviewer | reviewer 判定通过，P0=0 且 P1=0 |
| p2_clearing | P2 清零中 | writer | approved 后仍有 P2 残留时自动进入 |
| signed_off | 封版 | **liufeng 手动** | P2=0 确认 + liufeng 终审签字 |
| blocked | 卡死 | watcher / liufeng | 异常 / 3轮上限 / token 超支 / 连续3轮审核不过 |

5.2.1 blocked 恢复路径

blocked 的恢复路径按原因分类枚举，liufeng 介入时选择：

| 原因 | 恢复路径 | 说明 |
|------|----------|------|
| task 卡死（超时） | 继续原状态，恢复 cron 后从卡死点继续 | 网速/模型响应慢导致超时，任务本身没问题 |
| 3轮循环上限 | 回退到 backlog，重置 iteration_count=0，liufeng 补充需求说明后重开 | 需求和文档质量差距过大，需要重新对齐 |
| token 超支 | 回退到 drafting，调整 tokens_budget（x1.5或更多），继续写作 | 预估算少了，调完预算继续 |
| 数据丢失 | git checkout 恢复或回退到 drafting 重新写 | 看能否从 git 恢复 |
| 连续3轮审核不过 | 回退到 backlog，liufeng 判断是需求问题还是质量太差 | 需要人工决定是改需求还是改写法 |

### 5.3 状态迁移验证关卡

**drafting -> awaiting_review 验证关卡：**
1. git commit 确认
2. git log -3 确认有新 commit
3. git diff HEAD~1 确认实质变化
4. grep 关键概念确认完整
5. 调用 reusable-review-rules/wrapper.py 跑语法检查
6. 全部通过->触发 reviewer；任意失败->进入 blocked + comment 写原因

**awaiting_review -> approved/needs_revision 验证关卡：**
1. reviewer 完整读文档
2. 按8项必审检查
3. 写审计报告到 audit-reports/
4. comment 包含：问题逐条清单 + 严重等级 + 行号 + 审核证据
5. 通过->更新为 approved，触发 quality_scores 评分
6. 不通过->更新为 needs_revision + 问题清单

**approved -> signed_off 验证关卡：**
1. P2=0 确认（在 p2_clearing 阶段由 writer 完成）
2. liufeng 终审清单6项全部通过
3. liufeng 手动将 kanban 状态设为 signed_off

---

## 6. 通知机制（事件驱动，零轮询）

### 6.1 Writer -> Reviewer 通知

Writer 完成写作并验证通过后执行：
```
HERMES_PROFILE=yaya-reviewer hermes cron run review-<project>
```
跨 profile 调用不消耗 writer 的 token。

### 6.2 Reviewer -> Writer 通知

Reviewer 判定不通过时，通过 kanban 状态更新通知 writer。Writer 的 project-watch cron job 在 no_agent 脚本扫描到 needs_revision 时接手修改。

### 6.3 Watcher 通知

Watcher 检测到异常时：暂停该项目的 writer/reviewer 的 cron job（不影响其他项目）+ 写 alert 文件到 .kanban/.alerts/ + launchctl 日志输出。

---

## 7. 监控机制（Watchdog）

### 7.1 Watcher Daemon 架构

Python watchdog daemon，launchctl 管理。监听 .kanban/board.db / projects/ / audit-reports/ 的文件事件。事件触发后执行4个看门狗检测。

每个项目有独立的 watcher 实例，互不干扰。

### 7.2 四个看门狗

1. 卡死检测：task 在 drafting/awaiting_review 状态下超时（<500行45min/500-800行90min/>800行150min）-> 暂停 cron + alert
2. 死循环检测：iteration_count >= 3（iteration_count 从 0 开始计数。Writer 首次提交时为 0，Reviewer 每次判定 needs_revision 时 +1。>= 3 时表示第 4 轮提交仍被退回，直接 blocked）-> blocked + alert
3. 数据丢失检测：kanban 状态与实际文件不一致 -> 先检查该文档的 kanban 状态：如果是 drafting 状态（Writer 正在写），只报警不做 git checkout（防止竞态）。非 drafting 状态则检查 git 历史 -> 有则 checkout 恢复，无则回退状态
4. Token 超支检测：tokens_spent > tokens_budget x 1.5 -> blocked + alert

### 7.3 Token 中间预警

在 tokens_spent 达到 tokens_budget 的 80% 和 100% 时，向 writer/reviewer 的 prompt 中嵌入警告提示，避免突然 blocked：

```
[预算警告] 当前 token 消耗已占预算的 80%。剩余预算约 X tokens。请根据实际情况检查是否需要调整后续工作范围。
[预算警告] 当前 token 消耗已达预算 100%！如果继续消耗，超出 50% 后将自动 blocked。
```

### 7.4 Watcher 自我监控

- launchctl 自动重启
- 每次启动写入 .kanban/watcher_started.json
- 每30分钟写入心跳文件 .kanban/watcher_heartbeat.json

---

## 8. 质量保障策略

### 8.1 Writer 侧质量策略

策略1：写作前加载自查清单。Writer 开始写作前，加载7项必备交付物清单 + 硬编码 grep 清单（含第6项 NORTH_STAR 阅读确认）。

策略2：写作后实物验证。三项验证（git log / git diff / grep 关键概念）+ 调用 reusable-review-rules/wrapper.py 跑语法检查。自检的定位是"有没有写"，不是"写得对不对"。

### 8.2 Reviewer 侧质量策略

策略3：审计模板。每条问题必须包含：编号、严重等级、类别、问题描述（含行号/引用原文）、修复建议。

策略4：单轮问题全量输出。Reviewer 一次审核必须输出所有发现的问题，不能分批。

### 8.3 流程级质量策略

策略5：3轮循环上限。reviewer 判定 needs_revision 时 iteration_count+1（从0开始，首次提交为0），达到3时自动 blocked(reason: max_iterations_exceeded)。

策略6：Token 预算制度。Writer 和 reviewer 在各自会话结束前必须更新 kanban 的 tokens_spent 字段。在 tokens_spent 达 80%/100% 时嵌入预警提示。超出 50% 自动 blocked。

策略7：审计报告独立存档。每次审核结果写入 audit-reports/<编号>_audit_report_v<版本>.md。

### 8.4 质量评分体系

文档 approved 后由 watcher 触发自动评分，写入 quality_scores 表。

**总分 = 合规分 x 0.4 + AI 质量分 x 0.4 + 缺陷趋势分 x 0.2**

**合规分（自动化计算，0 token 成本）**
| 指标 | 计算方式 | 满分 |
|------|---------|------|
| 必备章节完整度 | 7项必备内容实际有几项 | 20 |
| 跨引用准确率 | Sxx 引用在目标文档头部版本号一致比例 | 20 |
| 默认值一致性 | AI-MUTABLE 字段最多出现几个不同值的倒数 | 20 |
| 极端场景覆盖率 | 3个场景中实际覆盖几个 | 20 |
| 变更记录合规 | 版本号/格式对齐给分 | 20 |

**AI 质量分（文档 approved 后独立执行，约 10K tokens，用 deepseek-chat 等廉价模型）**

AI 独立阅读全文（不是 reviewer 的同一思考），对5个维度评分，每个1-5分换为百分制：
1. 可操作性：新工程师能否照着文档写代码？
2. 异常覆盖度：崩溃/超时/数据丢失/格式错误是否有方案？
3. 决策可追溯：重要设计决定是否说明了"为什么这么做"？
4. 外部一致性：引用的其他系统信息是否对得上？
5. 内部自洽：同一信息在不同章节说法是否一致？

**AI 质量分与 reviewer 判断分歧处理：**
- 如果 AI 质量分与 reviewer 判断不一致（如 reviewer 给了 passed 但 AI 打出极低分），分差超过 40 分时，**阻断 approved 状态**，写入一条"质量偏差阻断"记录，将 task 回退到 needs_revision 状态让 writer 重审。该文档需要 liufeng 亲自判断后才可继续流程。
- 正常分差（不超过 40 分）：仅写入日志，不阻断流程。

**缺陷趋势分（自动化计算，0 token 成本）**

追踪同一文档各版本间的 P0/P1/P2 数量变化。首版基线0分。每轮下降一个 P0/P1 -> 加分；上升->扣分。

**评分的使用方式：**
- 不作为通过/不通过的决策依据（通过与否由 reviewer 判定，分差>40 例外）
- 作为 owner 观察质量趋势的工具
- liufeng 定期抽样对比 AI 评分与人工判断，验证可靠性

**跨文档版本兼容性检查（扩展项）：**
在质量评分中加入跨文档版本兼容性检查：如果文档 A 引用了文档 B，检查 A 引用的版本号是否与 B 当前封版版本号匹配。不匹配时在质量评分中扣分，并写入一条"版本兼容性预警"。

### 8.5 自我进化机制

**进化触发时机：**
每轮文档达到 approved 后触发一次进化总结。一次就过的文档也触发。

**Writer 的回顾：**
- 这轮被提了多少 P0/P1/P2？
- 哪些问题自检时就应该发现但没发现？为什么？
- 有没有某类问题反复被提？说明系统性盲区
- 总结一条：需要在自检清单里加什么检查？

**Reviewer 的回顾：**
- 这轮有多少问题是第二轮才发现（第一轮漏掉）？
- 漏掉的有无共同模式？
- 有没有给了 P2 但 writer 改了之后造成更大 P0 的问题（误判严重性）？
- 总结一条：需要在审计模板里加什么检查？或调整什么 P 等级？

**进化规则管理（集中式，不分开两份）：**

规则集中在 evolution_rules.yaml，分两段：
- pre_flight：writer 执行（提交前检查）
- post_flight：reviewer 执行（审核阶段检查）

每条规则包含 scope 字段：
- scope: universal（通用规则，可用于开源版）
- scope: project（项目特定规则，包含内部路径/子系统名等敏感信息，不公开）

两条规则配对启用/停用，保证 writer 和 reviewer 同步进化。每条规则记录 hit_count 和 total_rounds，连续50轮无命中标记为过时。

**进化建议的三字段格式（让非技术人员也能决策）：**
1. 技术描述：规则本身的技术表达
2. 建议+理由：推荐生效/不生效 + 为什么
3. 大白话：不用技术术语，用生活类比解释

owner 看大白话理解问题，看建议+理由决定是否采纳。P 等级单独标注，不做大白话翻译。规则不自动生效，owner 定期查看 pending 建议后手动 approve/reject。

---

## 9. Token 消耗控制

### 9.1 零空转设计

| 组件 | 运作方式 | 空转成本 |
|------|----------|----------|
| writer 的 project-watch | no_agent 脚本模式 | 0 token |
| reviewer 的 review-* | 完整 agent，只被触发时启动 | 0 token |
| watcher daemon | Python watchdog | 0 token |
| 通知机制 | hermes cron run CLI | 0 token |
| AI 质量评分 | approved 后触发一次，约 10K tokens | 10K tokens/文档 |
| 进化回顾 | approved 后触发一次，约 5K tokens | 5K tokens/轮 |

AI 质量评分和进化回顾使用廉价模型（deepseek-chat），占总 token 消耗 < 1%。

### 9.2 预算管控

- 写一个子系统文档（400-1000行）：预算 150万-300万 tokens
- 审核一次：预算 50万-100万 tokens
- 一轮完整循环（1写+1审）：预算 200万-400万 tokens

### 9.3 逃生节省

同一 task 迭代第3轮时（iteration_count=2），writer 的 prompt 中嵌入提示：
"当前是第3轮修改机会。请重点检查前两轮 reviewer 标记的每一条问题是否全部修复。如果本轮仍然无法通过，iteration_count 将达 3，task 将自动 blocked。"

---

## 10. 异常处理与恢复

### 10.1 异常分类

| 类型 | 检测者 | 自动处置 |
|------|--------|----------|
| task 卡死 | watcher | 暂停 cron + alert |
| task 循环3轮 | watcher | 暂停 + blocked + alert |
| 文件丢失 | watcher | 先检查状态：drafting 则只报警不做 checkout；非 drafting 则 git checkout 恢复或回退状态 + alert |
| Token 超支 | watcher | 暂停 + blocked + alert |
| Watcher 自身挂掉 | launchctl | 自动重启 |
| 质量偏差（分差>40） | watcher | 阻断 approved，回退到 needs_revision + alert，需 liufeng 判断 |
| 跨文档版本不兼容 | 质量评分 | 写入预警日志，不阻断流程 |

### 10.2 恢复流程

watcher 发现异常 -> 暂停该项目的 writer/reviewer 的 cron job -> 写 alert -> 输出日志 -> liufeng 介入分析 -> 按异常类型选择恢复路径（见 5.2.1 节枚举的5种恢复路径）。

---

## 11. 实现计划

### Phase 1：基础设施（预计 1-2 天）
1. 创建项目目录结构（已完成）
2. 创建 evolution_rules.yaml 初始模板（含 scope 字段）
3. 实现 no_agent watch 脚本（30行 Python，扫描 SQLite）
4. 编写 reusable-review-rules/wrapper.py
5. 注册 writer 的 cron job

### Phase 2：核心循环（预计 2-3 天）
6. 实现 kanban SQLite 操作（含 iteration_number 字段）
7. 实现 Writer 写作流程（读取 task -> 写作 -> 自检 -> 提交 -> 通知 reviewer）
8. 实现 Reviewer 审核流程（被触发 -> 审核 -> 输出审计报告 -> 更新状态）
9. 实现 Writer->Reviewer 通知（HERMES_PROFILE=... hermes cron run）
10. 放置测试 task，跑通第一轮完整循环（含 p2_clearing 过渡）

### Phase 3：质量与监控（预计 2-3 天）
11. 实现 Watcher daemon（Python watchdog + 4个看门狗 + 竞态检查 + 多项目隔离）
12. 实现质量评分体系（合规分 + AI 质量分 + 缺陷趋势分 + 分差>40 阻断 + 跨文档版本兼容性检查）
13. 实现自我进化机制（提议生成 + evolution_rules.yaml 更新 + scope 区分）
14. launchctl 管理

### Phase 4：打磨与扩展
15. 扩展到 Project Spark、Project Spark Adult
16. 进化机制验证（跑5-10轮后，比较 P0/P1 数量的趋势）
17. 如果进化有效，将 workflow package 成可复用的模板
18. 筹备开源+商业化分轨（开源版去除 project scope 规则，公开版含全部规则）

---

## 12. 商业化与开源策略

### 12.1 为什么开源

- 核心框架本身是通用模式，对开源社区有价值
- 开源吸引贡献者，反哺规则集积累
- 验证模式可行性后，降低传播门槛

### 12.2 开源的内容

- 三 profile 架构设计、kanban 状态机、自检/审核模板
- evolution_rules.yaml 的结构设计（仅含 scope: universal 的规则）
- writer.py / reviewer.py / watcher.py 的基础实现
- PRD、标准、验收规范文档

### 12.3 付费的内容

- 质量评分 AI 模型（5维评分器，封装 API，不开源）
- 预置规则包（scope: project 的成熟规则集，基于几百轮审计经验积累，按月订阅更新）
- 质量趋势仪表盘（跨文档/跨项目/跨时间可视化界面，不开源）
- **托管配置服务**（不是"一键脚本"，是托管的三 profile 配置 + System Prompt + 规则初始化 + 后续维护更新，不开源）

### 12.4 两条线不冲突

- 开源用户：能自己跑起来，通用规则自己写，不依赖任何人
- 付费用户：半小时上线开箱即用，白嫖几百轮积累的项目级规则，省下自己写规则和调参的时间

核心壁垒是审核规则集的质量和积累，不是架构代码。规则集是几百轮真实审计中积累的经验。通过 scope: universal / scope: project 区分，开源版只有通用规则，不泄露内部敏感信息。

### 12.5 商业化最小路径

1. 现在阶段：就你一个用户，跑通芽芽的生产-审核循环，验证可行性
2. 第一阶段：稳定运行1个月，积累50条左右的进化规则 -> 发 GitHub（仅 universal 规则）+ 完善部署文档
3. 第二阶段：在 AI 圈子群分享运行数据 -> 自然有人问"怎么弄" -> 提供付费托管方案

---

## 13. 未来展望：三层愿景

### 13.1 第一层：子系统设计文档（当前已完成设计）

面向技术团队内部。S01-S16 子系统设计文档的自动化生产-审核-封版。当前 PRD 即为此层而写，所有设计决策（7项必备/8项必审/质量评分/自我进化/blocked恢复路径/Profile权限边界）均在此层验证。

### 13.2 第二层：产品 PRD 到技术文档（扩展方案已明确）

非技术用户说出想法（"我要开发一个XXX"）-> 系统问问题对齐认知 -> 生成完整产品 PRD -> 拆分为模块 PRD -> 每个模块走自动化生产-审核-封版循环。

产品 PRD 全部封版后，系统根据产品文档自动生成对应的技术设计文档。技术文档再走一遍完整的生产-审核-封版循环。

所有文档封版后，工作流自然停止。

### 13.3 第三层：开发实现（本文档只做到文档交付）

产品 PRD + 技术设计文档全部封版后，直接输出给 Claude Code、Cursor 等 IDE 进行开发。本系统不做代码的写、审循环——代码审核市场已有大量成熟产品，不做同一件事。

本系统的正确位置是：文档质量的最后一道关，开发流程的第一道输入。

---

## 14. 附录

### A. 文件位置

项目根目录：/Users/liufeng/Documents/DocProductionReview/
PRD 文件：PRD_AUTO_DOC_WORKFLOW.md
进化规则：evolution_rules.yaml
可复用规则：reusable-review-rules/
审核报告：audit-reports/

### B. 关键术语对照表

| 术语 | 含义 |
|------|------|
| Profile | Hermes 框架中的独立角色实例，有独立的模型、记忆、技能、工具权限配置 |
| Kanban | 文档任务的状态看板，用 SQLite 实现 |
| Writer | 生产P，负责写文档 |
| Reviewer | 审核P，负责审文档 |
| Watcher | 监控P，负责监控循环健康 |
| P0-P3 | 缺陷分级，P0 最严重 |
| approved | 审核通过（P0=P1=0） |
| p2_clearing | P2 清零阶段（approved 到 signed_off 的过渡态） |
| signed_off | 封版（P2=0 + liufeng 签字） |
| iteration_count | 迭代轮次计数（从0开始，reviewer 每次 needs_revision 时 +1） |
