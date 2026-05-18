# 自动化文档生产-审核循环工作流 开发者指南 v1.1

基于 PRD v2.2 实现。本文档提供每个模块的实现细节：文件路径、接口签名、数据模型 DDL、配置文件模板、命令行参数。目标是：照着本文档就能写代码。

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.1 | 2026-05-18 14:09 | 审核 v1.0 全量修复：P0-1 p2_clearing->needs_revision 状态机修正；P0-2 Reviewer 直接设 p2_clearing 不再等 watcher；P0-3 增加 p2_cleared 中间状态+Writer P2_FIXED 标记；P1-1 get_tasks_by_status status 参数改为可选；P1-2 blocked 恢复 fallback 修复；P1-3 心跳/启动标记文件按项目区分；P1-4 质量评分触发改到 signed_off 后；P1-5 fromisoformat 改 strptime；P1-6 移除 no_agent watch.py 改为 Writer agent cron 直接扫描 kanban；P1-7 needs_revision->drafting 遗漏（writer_revision_workflow 跳过 claim，与状态机矛盾）；P2-1 3.2 注释残留修复；P2-2 6.2 通知+暂停cron 函数修复；P2-2 git 仓库路径统一；P2-3 部署步骤修复；P2-4 Writer 新增 3.4 p2_clearing 处理流程；P3-3 check_stuck_tasks 增加 p2_clearing 超时；P3-1 PRD 质量评分触发时机同步 signed_off；补充建议：previous_status 字段/git diff 守卫/wrapper.py 强制自检/prompt 单任务锁定/PRD 同步； |

## 目录

1. [项目目录结构](#1-项目目录结构)
2. [Kanban 模块](#2-kanban-模块)
3. [Writer 模块](#3-writer-模块)
4. [Reviewer 模块](#4-reviewer-模块)
5. [Watcher 模块](#5-watcher-模块)
6. [通知机制](#6-通知机制)
7. [Profile 配置](#7-profile-配置)
8. [wrapper.py](#8-wrapperpy)
9. [evolution_rules.yaml](#9-evolution_rulesyaml)
10. [质量评分模块](#10-质量评分模块)
11. [部署与运维](#11-部署与运维)

---

## 1. 项目目录结构

```
/Users/liufeng/Documents/DocProductionReview/
├── DEV_GUIDE.md                        # 本文档
├── PRD_AUTO_DOC_WORKFLOW.md            # PRD v2.2
├── evolution_rules.yaml                # 自我进化规则
├── reusable-review-rules/              # 可复用检测规则
│   ├── wrapper.py                      # Vale/markdownlint 调用入口
│   ├── .vale.ini                       # Vale 配置
│   └── .markdownlint.yaml              # markdownlint 配置
├── projects/                           # 各项目的文档目录
│   ├── yaya-zhujiao/
│   ├── project-spark/
│   └── project-spark-adult/
├── audit-reports/                      # 审核报告目录
├── .kanban/                            # kanban board + alert 文件
│   ├── yaya.db                         # 芽芽项目的 kanban SQLite
│   ├── project-spark.db                # Spark 项目的 kanban SQLite
│   ├── project-spark-adult.db          # Spark Adult 项目的 kanban SQLite
│   ├── watcher_started_<project>.json   # Watcher 启动标记（按项目区分）
│   ├── watcher_heartbeat_<project>.json # Watcher 心跳（按项目区分）
│   └── .alerts/                        # Alert 文件目录
└── scripts/                            # 辅助脚本
    ├── watch.py                        # （已弃用）agent cron 直接扫描 kanban，此文件可删除
    ├── quality_score.py                # 质量评分计算
    └── evolution_summary.py            # 进化总结生成
```

---

## 2. Kanban 模块

### 2.1 SQLite 数据库

每个项目一个独立的 SQLite 文件：`.kanban/<project>.db`

### 2.2 表结构 DDL

```sql
-- tasks 表：核心任务
CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY,         -- 格式: t_<random_hex>, 如 t_a1b2c3d4
    title           TEXT NOT NULL,            -- 任务标题, 如 "审核 S01"
    status          TEXT NOT NULL DEFAULT 'backlog',  -- 状态值: backlog|drafting|awaiting_review|needs_revision|approved|p2_clearing|p2_cleared|signed_off|blocked
    assigned_to     TEXT,                     -- 分配给哪个 profile: writer|reviewer|liufeng
    project         TEXT NOT NULL,            -- 项目标识: yaya-zhujiao|project-spark|project-spark-adult
    file_path       TEXT,                     -- 被审核文档的绝对路径
    version         TEXT,                     -- 文档当前版本号, 如 v3.1.17
    commit_sha      TEXT,                     -- 当前版本对应的 git commit SHA
    iteration_count INTEGER DEFAULT 0,        -- 迭代轮次, 从0开始。reviewer 判定 needs_revision 时 +1
    tokens_budget   INTEGER,                  -- token 预算（实测后启用）
    tokens_spent    INTEGER DEFAULT 0,        -- 已消耗 token 数
    blocked_reason  TEXT,                     -- blocked 原因: max_iterations_exceeded|timeout|token_overrun|data_loss|quality_deviation
    blocked_recovery_target TEXT,             -- blocked 恢复后的目标状态: backlog|drafting|原状态
    previous_status TEXT,                     -- 进入 blocked 前的状态（用于断点续传/精确恢复原上下文）
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- task_comments 表：任务评论/审计意见
CREATE TABLE IF NOT EXISTS task_comments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    author          TEXT NOT NULL,            -- writer|reviewer|watcher|liufeng
    content         TEXT NOT NULL,            -- 评论内容 / 审计报告路径
    iteration_number INTEGER DEFAULT 0,       -- 这条评论属于第几轮迭代
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- quality_scores 表：质量评分
CREATE TABLE IF NOT EXISTS quality_scores (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id             TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    version             TEXT NOT NULL,        -- 被评分的文档版本
    compliance_score    REAL,                 -- 合规分 0-100
    ai_quality_score    REAL,                 -- AI 质量分 0-100
    defect_trend_score  REAL,                 -- 缺陷趋势分
    total_score         REAL,                 -- 总分
    score_breakdown     TEXT,                 -- JSON 格式的评分细项
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- evolution_suggestions 表：进化建议
CREATE TABLE IF NOT EXISTS evolution_suggestions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,            -- writer|reviewer
    task_id         TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    round_number    INTEGER NOT NULL,         -- 第几轮触发的进化
    tech_description    TEXT NOT NULL,        -- 技术描述
    recommendation      TEXT NOT NULL,        -- 建议+理由
    plain_explanation   TEXT NOT NULL,        -- 大白话解释
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending|approved|rejected|obsolete
    p_level         TEXT,                     -- 关联的 P 等级 P0|P1|P2|P3
    scope           TEXT NOT NULL DEFAULT 'universal', -- universal|project
    hit_count       INTEGER DEFAULT 0,        -- 被命中的次数
    total_rounds    INTEGER DEFAULT 0,        -- 失效检测总轮数
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project);
CREATE INDEX IF NOT EXISTS idx_comments_task ON task_comments(task_id);
CREATE INDEX IF NOT EXISTS idx_scores_task ON quality_scores(task_id);
CREATE INDEX IF NOT EXISTS idx_evo_status ON evolution_suggestions(status);
```

### 2.3 Kanban 操作 API

所有 kanban 操作封装为 Python 模块 `kanban_ops.py`，放在项目根目录。

```python
# /Users/liufeng/Documents/DocProductionReview/kanban_ops.py

import sqlite3
import os
import json
from datetime import datetime

KANBAN_DIR = os.path.dirname(os.path.abspath(__file__)) + '/.kanban'

def _db_path(project: str) -> str:
    """获取项目对应的 kanban 数据库路径"""
    return os.path.join(KANBAN_DIR, f'{project}.db')

def _conn(project: str) -> sqlite3.Connection:
    """获取数据库连接（自动创建表）"""
    path = _db_path(project)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_tables(conn)
    return conn

def _ensure_tables(conn: sqlite3.Connection):
    """确保所有表存在"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
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
            blocked_reason TEXT,
            blocked_recovery_target TEXT,
            previous_status TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        -- ...（其余表同上 DDL）
    """)
    conn.commit()

def create_task(project: str, title: str, file_path: str = None, version: str = None) -> str:
    """创建新任务，返回 task_id"""
    import random, string
    task_id = 't_' + ''.join(random.choices(string.hexdigits.lower(), k=8))
    conn = _conn(project)
    conn.execute(
        "INSERT INTO tasks (id, title, status, assigned_to, project, file_path, version) VALUES (?,?,?,?,?,?,?)",
        (task_id, title, 'backlog', 'writer', project, file_path, version)
    )
    conn.commit()
    conn.close()
    return task_id

def get_task(project: str, task_id: str) -> dict:
    """获取单个任务"""
    conn = _conn(project)
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_tasks_by_status(project: str, status: str = None) -> list:
    """按状态获取任务列表。status=None 返回该项目的全部任务。"""
    conn = _conn(project)
    if status is None:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE project=? ORDER BY updated_at ASC",
            (project,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE project=? AND status=? ORDER BY updated_at ASC",
            (project, status)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_task_status(project: str, task_id: str, new_status: str, **extra):
    """更新任务状态，同时更新 updated_at"""
    conn = _conn(project)
    fields = ['status=?, updated_at=datetime(\'now\')']
    values = [new_status]
    for k, v in extra.items():
        fields.append(f'{k}=?')
        values.append(v)
    conn.execute(
        f"UPDATE tasks SET {', '.join(fields)} WHERE id=?",
        values + [task_id]
    )
    conn.commit()
    conn.close()

def add_comment(project: str, task_id: str, author: str, content: str, iteration_number: int = 0):
    """添加评论"""
    conn = _conn(project)
    conn.execute(
        "INSERT INTO task_comments (task_id, author, content, iteration_number) VALUES (?,?,?,?)",
        (task_id, author, content, iteration_number)
    )
    conn.commit()
    conn.close()

def get_comments(project: str, task_id: str) -> list:
    """获取所有评论"""
    conn = _conn(project)
    rows = conn.execute(
        "SELECT * FROM task_comments WHERE task_id=? ORDER BY created_at ASC",
        (task_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def increment_iteration(project: str, task_id: str):
    """iteration_count +1（reviewer 判定 needs_revision 时调用）"""
    conn = _conn(project)
    conn.execute(
        "UPDATE tasks SET iteration_count = iteration_count + 1, updated_at = datetime('now') WHERE id=?",
        (task_id,)
    )
    conn.commit()
    conn.close()

def save_quality_score(project: str, task_id: str, version: str, scores: dict):
    """保存质量评分"""
    conn = _conn(project)
    conn.execute(
        """INSERT INTO quality_scores 
           (task_id, version, compliance_score, ai_quality_score, defect_trend_score, total_score, score_breakdown)
           VALUES (?,?,?,?,?,?,?)""",
        (task_id, version, scores.get('compliance'), scores.get('ai_quality'),
         scores.get('defect_trend'), scores.get('total'), json.dumps(scores.get('breakdown', {})))
    )
    conn.commit()
    conn.close()
```

### 2.4 状态迁移规则

| 迁移 | 谁执行 | 条件 |
|------|--------|------|
| backlog -> drafting | writer | writer claim task |
| drafting -> awaiting_review | writer | 写作完成 + 自检通过 + 实物验证通过 |
| awaiting_review -> needs_revision | reviewer | P0>0 或 P1>0 |
| awaiting_review -> approved | reviewer | P0=0 且 P1=0 |
| needs_revision -> drafting | writer | writer 接手修改 |
| approved -> p2_clearing | reviewer | P2>0 且 P0=P1=0 时 reviewer 直接置入 |
| p2_clearing -> needs_revision | writer | 修 P2 时发现需改逻辑，需重新审核 |
| p2_clearing -> p2_cleared | writer | P2 全部修复完毕，添加 P2_FIXED 标记 comment 后置入 |
| p2_cleared -> signed_off | liufeng | P2=0 确认 + liufeng 终审签字 |
| 任意状态 -> blocked | watcher/liufeng | 异常/6轮上限/token超支/连续6轮审核不过（自检失败和commit失败已不再阻塞，改为自动修复重试3次后送审） |

### 2.5 blocked 恢复路径

恢复时更新 `blocked_recovery_target` 字段，由 liufeng 手动操作：

```python
# 恢复操作示例
def recover_blocked_task(project: str, task_id: str, action: str):
    """action: 'continue'|'reset_backlog'|'adjust_budget'|'git_restore'|'manual_review'"""
    task = get_task(project, task_id)
    if not task or task['status'] != 'blocked':
        return
    
    recovery_map = {
        'continue': task['blocked_recovery_target'] or 'backlog',
        'reset_backlog': 'backlog',
        'adjust_budget': 'drafting',
        'git_restore': 'drafting',
        'manual_review': 'backlog',
    }
    target = recovery_map.get(action, 'backlog')
    
    update_task_status(project, task_id, target)
    add_comment(project, task_id, 'liufeng', 
                f'手动恢复: blocked_reason={task["blocked_reason"]}, action={action}, target={target}')
```

---

## 3. Writer 模块

### 3.1 Writer 触发机制（agent cron 直接扫描 kanban）

Writer 不使用 no_agent 扫描脚本，改为 agent cron job 直接查询 kanban。
每个项目注册一个 Writer agent cron job，每 5 分钟运行一次。

```yaml
# 在 Writer profile 的 cron 配置中注册
name: writer-yaya-zhujiao
schedule: "*/5 * * * *"
prompt: |
  在 /Users/liufeng/Documents/DocProductionReview/ 项目目录中，
  扫描 yaya-zhujiao 项目的 kanban 任务（使用 kanban_ops.py）：
  
  1. 先扫描 backlog 状态任务：取最旧的 1 个开始写作
  2. 如果没有 backlog，扫描 needs_revision 状态任务：取最旧的 1 个，claim（needs_revision->drafting）后开始修改
  3. 如果没有 needs_revision，扫描 p2_clearing 状态任务：取最旧的 1 个开始修 P2
  4. 以上都没有就什么都不做
  
  检测到待处理任务后，先 claim（backlog->drafting），
  再执行对应的写作/修改/P2 修复流程。
  一个 cron tick 只处理 1 个任务。完成当前任务后立即退出本轮 cron tick，
  不要扫描并启动第二个任务。
```

不再需要 watch.py 脚本。如果已存在 `scripts/watch.py` 可删除。
### 3.2 Writer 写作流程

Writer agent 被 agent cron 扫描 kanban 触发后（每次 tick 只处理 1 个任务），执行以下流程：

```python
# 伪代码：Writer 主流程
def writer_workflow(project: str, task_id: str, status: str):
    # 1. claim task：backlog -> drafting
    update_task_status(project, task_id, 'drafting', assigned_to='writer')
    add_comment(project, task_id, 'writer', f'开始写作（来自 {status}）')
    
    task = get_task(project, task_id)
    
    # 2. 读需求
    # 从 task.title 和 task.file_path 确定要写什么
    # 读 NORTH_STAR.md（如果项目是芽芽）
    # 读相关已有子系统文档
    
    # 3. 写作
    # 调用大模型生成文档
    # 写完后保存到 projects/<project>/<filename>
    
    # 4. 自检（hard-coded grep 清单）
    # - grep AI-MUTABLE 参数名，确认默认值一致
    # - grep 信用分初始值，全文一致
    # - grep "待 SXX 定义" 标记，确认封版或有兜底
    # - grep 版本号引用，与目标文档头部一致
    # - grep 硬编码行号，无残留
    # - 确认已读 NORTH_STAR
    
    # 5. 实物验证
    # - git commit
    # - git log -3 确认有新 commit
    # - git diff HEAD~1 确认实质变化
    # - grep 关键概念确认完整
    # - 调用 wrapper.py 跑语法检查
    
    # 6. 更新 kanban
    update_task_status(project, task_id, 'awaiting_review')
    add_comment(project, task_id, 'writer', '自检声明：...')
    
    # 7. 触发 reviewer
    # 执行: HERMES_PROFILE=yaya-reviewer hermes cron run review-<project>
```

### 3.3 needs_revision 修改规则

```python
def writer_revision_workflow(project: str, task_id: str):
    """needs_revision 状态下的修改流程"""
    task = get_task(project, task_id)
    
    # 1. claim task：needs_revision -> drafting（等 watcher 可见，避免监控盲区）
    update_task_status(project, task_id, 'drafting', assigned_to='writer')
    add_comment(project, task_id, 'writer', f'开始修改（来自 needs_revision）')
    
    # 2. 读取审核报告（从 audit-reports/ 或 task_comments）
    comments = get_comments(project, task_id)
    review = [c for c in comments if c['author'] == 'reviewer'][-1]
    
    # 3. 修复所有 P0/P1 问题
    # 4. 可修复自己发现的额外问题
    # 5. 用 git diff 记录额外修改
    
    # 6. 自检 + 版本号 bump + 变更记录
    # 7. 实物验证
    # 8. 提交审核（drafting -> awaiting_review）
    update_task_status(project, task_id, 'awaiting_review')
    
    # 提交审核时附带的交接上下文
    add_comment(project, task_id, 'writer', f'''
自检声明：
- 本轮修改范围：<章节1、章节2、章节3>
- 已知遗留问题：<P3 项>
- 额外修改内容：
  git diff HEAD~1 --stat
  （列出 Reviewer 未指出的额外修改）
- 自检通过项：7项必备内容/3极端场景/grep清单
- NORTH_STAR 待定义条目已阅读：<条目清单>
''')
```


### 3.4 p2_clearing 处理流程

当 Writer agent cron 扫描到 `p2_clearing` 状态的任务时，执行以下流程：

```python
def writer_p2_clearing_workflow(project: str, task_id: str):
    """p2_clearing 状态下的 P2 修复流程"""
    task = get_task(project, task_id)
    
    # 1. 读取审核报告，定位 P2 项
    # 从 audit-reports/<project>/ 目录读取最近的审核报告
    # 提取所有 P2 项的修复建议
    
    # 2. 逐一修复 P2 问题
    # - 术语不一致 -> 全文统一
    # - 格式错误 -> 修正格式
    # - 引用未标注路径 -> 补全路径
    # - 其他 P2 项同理
    
    # 3. git diff 守卫：确认仅修改 P2 项
    # - git diff HEAD~1 --stat，检查修改文件范围
    # - git diff HEAD~1，确认 diff 仅涉及术语/格式/路径修正
    # - 如果 diff 涉及核心逻辑变更（状态机、数据流、新增章节结构），
    #   必须在 comment 说明理由并退回 needs_revision（而不是强行签入 p2_cleared）
    
    # 4. 自检
    # - 确认所有 P2 项已修复
    # - 运行 wrapper.py 做语法检查（强制步骤，不可跳过）
    # - 确认未引入新的 P0/P1
    
    # 4. 标记 P2 修复完毕
    add_comment(project, task_id, 'writer', 
                'P2_FIXED: 所有 P2 项已修复。变更清单：<git diff 摘要>')
    update_task_status(project, task_id, 'p2_cleared')
    
    # 5. 通知 liufeng 终审
    # （liufeng 检查任务状态为 p2_cleared 以及 P2_FIXED comment 后做终审签字）
```

注意：
- 执行环境与 Writer 3.2/3.3 一致，使用 Writer profile 的 API Key
- 修复 P2 时如果发现实际需要改动文档逻辑/结构（超出纯 P2 范围），应回到 3.3 流程走 needs_revision
- 无论 P2 修复多简单（哪怕只改一个词），必须调用 wrapper.py 做语法检查，禁止直接跳过
- git diff 守卫建议：修完 P2 后先 git diff 检查修改范围，确认不涉及核心逻辑再提交
- 修复完成后务必在 comment 中包含 `P2_FIXED` 标记，liufeng 终审时以此作为"修完"信号

---

---

## 4. Reviewer 模块

### 4.1 cron job 配置

Reviewer 被 Writer 触发：`HERMES_PROFILE=yaya-reviewer hermes cron run review-<project>`

cron job 注册：
```yaml
# 在 reviewer profile 中注册
name: review-yaya-zhujiao
schedule: "on-demand"  # 仅通过 hermes cron run 触发
prompt: "扫描 yaya-zhujiao 项目的 awaiting_review 任务，按 updated_at 最旧优先处理"
```

### 4.2 审核流程

```python
# 伪代码：Reviewer 主流程
def reviewer_workflow(project: str):
    # 1. 获取一个 awaiting_review 任务（最旧优先）
    tasks = get_tasks_by_status(project, 'awaiting_review')
    if not tasks:
        return  # 没有待审核任务
    
    task = tasks[0]  # updated_at ASC，取最旧的
    
    # 2. 全量审核
    # 读文档全文
    # 按8项（不限于8项）检查
    # 1) 文档完整度：7项必备
    # 2) 术语一致性
    # 3) 规则一致性
    # 4) 自洽性数学验证
    # 5) 极端场景推演
    # 6) 跨系统引用
    # 7) 生产P 2-4项交付物检查
    # 8) 变更记录规范
    
    # 3. 生成审计报告
    # 路径: audit-reports/<project>/<document>_audit_report_v<version>.md
    report_path = f'audit-reports/{task["project"]}/{os.path.basename(task["file_path"])}_audit_report_v{task["version"]}.md'
    
    # 4. 判定
    if p0_count == 0 and p1_count == 0:
        # 通过
        if p2_count > 0:
            update_task_status(project, task['id'], 'p2_clearing')
            add_comment(project, task['id'], 'reviewer',
                        f'P0=P1=0 但 P2>0，直接进入 p2_clearing。审核报告：{report_path}')
        else:
            update_task_status(project, task['id'], 'approved')
        add_comment(project, task['id'], 'reviewer', f'审核通过。审计报告：{report_path}')
    else:
        # 不通过
        increment_iteration(project, task['id'])  # iteration_count +1
        task = get_task(project, task['id'])
        if task['iteration_count'] >= 6:
            update_task_status(project, task['id'], 'blocked',
                               blocked_reason='max_iterations_exceeded',
                               blocked_recovery_target='backlog')
            add_comment(project, task['id'], 'watcher',
                        f'iteration_count={task["iteration_count"]} >= 6，自动 blocked')
        else:
            update_task_status(project, task['id'], 'needs_revision')
        add_comment(project, task['id'], 'reviewer',
                    f'审核不通过。问题清单见：{report_path}')
```

### 4.3 审计报告模板

```markdown
# 审计报告：<文档标题>
审核版本：<版本号>
审核日期：<git commit 日期>
审核人：reviewer

## 问题清单

### P0（架构矛盾、安全漏洞、数据丢失风险）
| 编号 | 类别 | 行号 | 问题描述 | 修复建议 |
|------|------|------|----------|----------|
| P0-1 | 架构矛盾 | L45 | ... | ... |

### P1（规则不一致、缺失关键章节）
| 编号 | 类别 | 行号 | 问题描述 | 修复建议 |
|------|------|------|----------|----------|

### P2（术语不一致、格式错误、引用未标注路径）
| 编号 | 类别 | 行号 | 问题描述 | 修复建议 |
|------|------|------|----------|----------|

### P3（优化建议）
| 编号 | 类别 | 行号 | 建议内容 |
|------|------|------|----------|

## 审核结论
- P0: X 个
- P1: X 个
- P2: X 个
- P3: X 个
- 结论：passed / needs_revision
```

---

## 5. Watcher 模块

### 5.1 Watcher Daemon

路径：`/Users/liufeng/Documents/DocProductionReview/scripts/watcher_daemon.py`

使用 Python watchdog 库监听文件事件。

#### 安装依赖

```bash
pip install watchdog
```

#### 多项目启动

每个项目一个 watcher 实例：
```bash
# 启动芽芽项目的 watcher
python3 scripts/watcher_daemon.py --project yaya-zhujiao

# 启动 Spark 项目的 watcher
python3 scripts/watcher_daemon.py --project project-spark
```

如果有 3 个项目，开 3 个终端 / launchctl 各管理一个。

#### 核心实现

```python
#!/usr/bin/env python3
"""Watcher daemon - 监控文档生产审核循环健康"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kanban_ops import get_tasks_by_status, get_task, update_task_status, add_comment

PROJECT_ROOT = '/Users/liufeng/Documents/DocProductionReview'
ALERTS_DIR = os.path.join(PROJECT_ROOT, '.kanban', '.alerts')

class DocProductionHandler(FileSystemEventHandler):
    """文件事件处理器"""
    
    def __init__(self, project: str):
        self.project = project
        self.heartbeat_interval = 1800  # 30分钟
    
    def on_modified(self, event):
        """文件修改事件触发"""
        if event.is_directory:
            return
        # 检测到 kanban 更新、文档更新、审计报告更新后
        # 执行 4 个看门狗检测
        self.run_watchdogs()
    
    def run_watchdogs(self):
        """执行 4 个看门狗检测"""
        self.check_stuck_tasks()
        self.check_dead_loop()
        self.check_data_loss()
        self.check_token_overrun()
        self.update_heartbeat()
    
    def check_stuck_tasks(self):
        """卡死检测"""
        for status in ['drafting', 'awaiting_review', 'p2_clearing']:
            tasks = get_tasks_by_status(self.project, status)
            for task in tasks:
                updated = datetime.strptime(task['updated_at'], '%Y-%m-%d %H:%M:%S')
                elapsed = (datetime.now() - updated).total_seconds()
                
                # 根据文档行数判断超时阈值
                file_path = task.get('file_path', '')
                line_count = 0
                if file_path and os.path.exists(file_path):
                    with open(file_path) as f:
                        line_count = sum(1 for _ in f)
                
                if line_count < 500:
                    timeout = 2700  # 45min
                elif line_count < 800:
                    timeout = 5400  # 90min
                else:
                    timeout = 9000  # 150min
                
                if elapsed > timeout:
                    self.alert(f'STUCK: task {task["id"]} in {status} for {elapsed}s (limit {timeout}s)')
    
    def check_dead_loop(self):
        """死循环检测"""
        tasks = get_tasks_by_status(self.project, 'needs_revision')
        for task in tasks:
            if task['iteration_count'] >= 6:
                update_task_status(self.project, task['id'], 'blocked',
                                   blocked_reason='max_iterations_exceeded',
                                   blocked_recovery_target='backlog')
                add_comment(self.project, task['id'], 'watcher',
                           f'死循环检测：iteration_count={task["iteration_count"]} >= 6，自动 blocked')
                self.alert(f'DEAD_LOOP: task {task["id"]} iteration={task["iteration_count"]}')
    
    def check_data_loss(self):
        """数据丢失检测"""
        # kanban 状态与实际文件不一致检查
        tasks = get_tasks_by_status(self.project, 'drafting')
        for task in tasks:
            file_path = task.get('file_path', '')
            if file_path and not os.path.exists(file_path):
                # drafting 状态下文件丢失——只报警不做 checkout（防止竞态）
                self.alert(f'DATA_LOSS: task {task["id"]} in drafting, file missing: {file_path}')
        
        tasks = get_tasks_by_status(self.project, 'awaiting_review')
        for task in tasks:
            file_path = task.get('file_path', '')
            if file_path and not os.path.exists(file_path):
                # 非 drafting 状态——尝试 git checkout 恢复
                self.alert(f'DATA_LOSS: task {task["id"]} file missing, attempting git restore: {file_path}')
                # 执行 git checkout
                repo_dir = PROJECT_ROOT  # Git 仓库根目录，所有文档统一管理
                os.system(f'cd {repo_dir} && git checkout -- {file_path}')
                # 如果仍然不存在，回退状态
                if not os.path.exists(file_path):
                    update_task_status(self.project, task['id'], 'blocked',
                                       blocked_reason='data_loss',
                                       blocked_recovery_target='drafting')
                    self.alert(f'DATA_LOSS: git restore failed, task blocked')
    
    def check_token_overrun(self):
        """Token 超支检测（待 token 预算实测后启用）"""
        pass  # 当前阶段不启用
    
    def update_heartbeat(self):
        """更新心跳"""
        heartbeat = {
            'project': self.project,
            'timestamp': datetime.now().isoformat(),
            'pid': os.getpid()
        }
        heartbeat_path = os.path.join(PROJECT_ROOT, '.kanban', f'watcher_heartbeat_{self.project}.json')
        with open(heartbeat_path, 'w') as f:
            json.dump(heartbeat, f)
    
    def alert(self, message: str):
        """写 alert 文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        alert_file = os.path.join(ALERTS_DIR, f'{self.project}_{timestamp}.alert')
        with open(alert_file, 'w') as f:
            f.write(f'{datetime.now().isoformat()}\n{message}\n')
        print(f'[ALERT] [{self.project}] {message}', file=sys.stderr)

def write_started_marker(project: str):
    """写入启动标记"""
    marker = {
        'project': project,
        'started_at': datetime.now().isoformat(),
        'pid': os.getpid()
    }
    marker_path = os.path.join(PROJECT_ROOT, '.kanban', f'watcher_started_{project}.json')
    with open(marker_path, 'w') as f:
        json.dump(marker, f)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True, help='项目标识: yaya-zhujiao|project-spark|project-spark-adult')
    args = parser.parse_args()
    
    write_started_marker(args.project)
    
    event_handler = DocProductionHandler(args.project)
    observer = Observer()
    
    # 监听 .kanban/、projects/<project>/、audit-reports/<project>/
    watch_paths = [
        os.path.join(PROJECT_ROOT, '.kanban'),
        os.path.join(PROJECT_ROOT, 'projects', args.project),
        os.path.join(PROJECT_ROOT, 'audit-reports'),
    ]
    for path in watch_paths:
        if os.path.exists(path):
            observer.schedule(event_handler, path, recursive=True)
    
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    main()
```

### 5.2 launchctl 管理

每个 watcher 实例对应一个 launchctl plist 文件。

```xml
<!-- ~/Library/LaunchAgents/com.docprodreview.watcher.yaya.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.docprodreview.watcher.yaya</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/liufeng/Documents/DocProductionReview/scripts/watcher_daemon.py</string>
        <string>--project</string>
        <string>yaya-zhujiao</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/liufeng/Documents/DocProductionReview</string>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/docprod_watcher_yaya.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/docprod_watcher_yaya_err.log</string>
</dict>
</plist>
```

```bash
# 加载
launchctl load ~/Library/LaunchAgents/com.docprodreview.watcher.yaya.plist

# 卸载
launchctl unload ~/Library/LaunchAgents/com.docprodreview.watcher.yaya.plist

# 检查状态
launchctl list | grep docprodreview
```

---

## 6. 通知机制

### 6.1 Writer -> Reviewer 通知

Writer 完成写作并验证后执行：

```bash
# 触发芽芽项目的 reviewer
HERMES_PROFILE=yaya-reviewer hermes cron run review-yaya-zhujiao

# 触发 Spark 项目的 reviewer
HERMES_PROFILE=spark-reviewer hermes cron run review-project-spark

# 触发 Spark Adult 项目的 reviewer
HERMES_PROFILE=spark-adult-reviewer hermes cron run review-project-spark-adult
```

### 6.2 Reviewer -> Writer 通知

Reviewer 更新 kanban 状态为 `needs_revision`。Writer 的 agent cron job 在下一 tick 扫描到 needs_revision 时接手修改。

### 6.3 Watcher 通知

Watcher 检测到异常时：
1. 暂停该项目的 writer/reviewer 的 cron job（不影响其他项目）
2. 写 alert 文件到 `.kanban/.alerts/`
3. launchctl 日志输出

暂停 cron job 操作：

```python
def pause_project_cron(project: str, profile_type: str):
    """暂停某项目的 writer/reviewer cron job
    profile_type: 'writer' 或 'reviewer'
    """
    profile_map = {
        'yaya-zhujiao':    {'writer': 'yaya', 'reviewer': 'yaya-reviewer'},
        'project-spark':   {'writer': 'project-spark', 'reviewer': 'spark-reviewer'},
        'project-spark-adult': {'writer': 'project-spark-adult', 'reviewer': 'spark-adult-reviewer'},
    }
    profile = profile_map[project][profile_type]
    
    cron_name = f'writer-{project}' if profile_type == 'writer' else f'review-{project}'
    os.system(f'hermes cron pause {cron_name} --profile {profile}')
```

---

## 7. Profile 配置

每个项目需要 2 个 Hermes Profile（Writer + Reviewer）+ 1 个全局 Watcher。

### 7.1 Writer Profile（生产P）

示例：`yaya` profile（芽芽项目的 Writer）

配置文件：`~/.hermes/profiles/yaya/config.yaml`

```yaml
model: deepseek-reasoner
provider: deepseek

# cron job：agent 模式直接扫描 kanban（每 5 分钟）
cron:
  - name: writer-yaya-zhujiao
    schedule: "*/5 * * * *"
    prompt: |
      扫描 yaya-zhujiao 项目的 kanban 任务。
      优先处理 backlog，其次 needs_revision，最后 p2_clearing。
      一个 tick 只处理 1 个任务，完成即退出本轮 cron，不要启动第二个。

# SOUL.md 内容（在 ~/.hermes/profiles/yaya/SOUL.md）
# 职责：文档生产者，负责按规范写出可通过审核的详细设计文档
```

### 7.2 Reviewer Profile（审核P）

示例：`yaya-reviewer` profile

配置文件：`~/.hermes/profiles/yaya-reviewer/config.yaml`

```yaml
model: deepseek-v4-pro
provider: deepseek

# 记忆和技能独立于 writer profile

cron:
  - name: review-yaya-zhujiao
    schedule: "on-demand"  # 仅通过 hermes cron run 触发
    prompt: |
      扫描 yaya-zhujiao 项目的 awaiting_review 任务，
      按 updated_at 最旧优先处理。
      执行全量审核：读文档全文 -> 按审核覆盖范围检查 -> 写审计报告 -> 更新 kanban 状态。
```

### 7.3 Watcher Profile（监控P）

示例：`yaya-watcher` profile

配置文件：`~/.hermes/profiles/yaya-watcher/config.yaml`

```yaml
watchdogs:
  - name: stuck-task-check
  - name: dead-loop-check
  - name: data-loss-check
  - name: token-overrun-check  # 待实测后启用
```

实际上 Watcher 是 Python daemon，不是 Hermes cron job。Profile 只用于配置管理和 launchctl 日志归属。

### 7.4 API Key 配置

系统支持最多 3 个 API Key，每个 Key 2 个并发槽位。

```yaml
# 在 ~/.hermes/config.yaml 中
providers:
  deepseek:
    api_key_env: DEEPSEEK_API_KEY_1  # 默认 key
    # 额外 key 在 writer/reviewer profile 中覆盖
```

推荐分配：

| 项目 | Writer Profile | Reviewer Profile | Key 分配 |
|------|---------------|-----------------|----------|
| 芽芽 | yaya | yaya-reviewer | Key 1 |
| Project Spark | project-spark | spark-reviewer | Key 2 |
| Project Spark Adult | project-spark-adult | spark-adult-reviewer | Key 2 (共享) |

---

## 8. wrapper.py

路径：`/Users/liufeng/Documents/DocProductionReview/reusable-review-rules/wrapper.py`

```python
#!/usr/bin/env python3
"""语法检查包装器。调用 Vale 和 markdownlint 对文档做语法层检查。"""

import sys
import os
import subprocess
import json

def run_vale(file_path: str) -> list:
    """运行 Vale 检查，返回问题列表"""
    try:
        result = subprocess.run(
            ['vale', '--output', 'JSON', file_path],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and not result.stdout.strip():
            return []
        # 解析 Vale 的 JSON 输出
        issues = []
        try:
            data = json.loads(result.stdout)
            # Vale JSON 格式: {file_path: [{Check: ..., Line: ..., Message: ..., Severity: ...}]}
            for file, checks in data.items():
                for check in checks:
                    issues.append({
                        'tool': 'vale',
                        'file': file,
                        'line': check.get('Line', 0),
                        'severity': check.get('Severity', 'warning'),
                        'message': check.get('Message', ''),
                        'check': check.get('Check', ''),
                    })
        except json.JSONDecodeError:
            pass
        return issues
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return [{'tool': 'vale', 'error': 'Vale not available or timed out'}]


def run_markdownlint(file_path: str) -> list:
    """运行 markdownlint 检查，返回问题列表"""
    try:
        result = subprocess.run(
            ['markdownlint', '--json', file_path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and not result.stdout.strip():
            return []
        issues = []
        try:
            data = json.loads(result.stdout)
            # markdownlint JSON 格式: [{fileName, lineNumber, ruleNames, ruleDescription, errorDetail, errorContext}]
            for item in data:
                issues.append({
                    'tool': 'markdownlint',
                    'file': item.get('fileName', ''),
                    'line': item.get('lineNumber', 0),
                    'severity': 'error',
                    'message': item.get('ruleDescription', ''),
                    'rule': '.'.join(item.get('ruleNames', [])),
                    'detail': item.get('errorDetail', ''),
                })
        except json.JSONDecodeError:
            pass
        return issues
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return [{'tool': 'markdownlint', 'error': 'markdownlint not available or timed out'}]


def check(file_path: str) -> dict:
    """主入口：对文件做语法检查
    
    返回:
        {
            'passed': bool,
            'total_issues': int,
            'issues': [
                {'tool': str, 'line': int, 'severity': str, 'message': str, 'rule': str},
                ...
            ]
        }
    """
    issues = []
    issues.extend(run_vale(file_path))
    issues.extend(run_markdownlint(file_path))
    
    return {
        'passed': len(issues) == 0 or all(i.get('severity') == 'warning' for i in issues),
        'total_issues': len(issues),
        'issues': issues,
    }


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python3 wrapper.py <file_path>', file=sys.stderr)
        sys.exit(1)
    
    result = check(sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result['passed'] else 1)
```

### Vale 配置

`.vale.ini` 放在 `reusable-review-rules/` 目录：

```ini
# /Users/liufeng/Documents/DocProductionReview/reusable-review-rules/.vale.ini
StylesPath = .vale-styles
MinAlertLevel = suggestion

[*.md]
BasedOnStyles = Vale, Microsoft
```

### markdownlint 配置

`.markdownlint.yaml` 放在 `reusable-review-rules/` 目录：

```yaml
# /Users/liufeng/Documents/DocProductionReview/reusable-review-rules/.markdownlint.yaml
default: true

MD013:              # line-length
  line_length: 120
  
MD024: false        # 允许多个同名标题
MD033: false        # 允许内联 HTML
MD041: false        # 不要求第一行是 h1
```

---

## 9. evolution_rules.yaml

路径：`/Users/liufeng/Documents/DocProductionReview/evolution_rules.yaml`

```yaml
# 自我进化规则
# 每条规则包含 scope、pre_flight（writer 自检用）、post_flight（reviewer 审核用）

rules:

  # --- 通用规则（scope: universal，可开源） ---

  - id: R001
    scope: universal
    hit_count: 0
    total_rounds: 0
    pre_flight:
      check: "grep 所有 AI-MUTABLE 参数名，确认每个参数全文只出现一种默认值"
      severity: P1
    post_flight:
      check: "AI-MUTABLE 参数默认值是否全文唯一"
      severity: P1

  - id: R002
    scope: universal
    hit_count: 0
    total_rounds: 0
    pre_flight:
      check: "grep 信用分初始值（=50/=50/初始值=50），全文一致"
      severity: P2
    post_flight:
      check: "信用分初始值是否全文一致"
      severity: P2

  - id: R003
    scope: universal
    hit_count: 0
    total_rounds: 0
    pre_flight:
      check: "grep '待 SXX 定义' 标记，确认 SXX 已封版或有兜底策略"
      severity: P1
    post_flight:
      check: "所有 '待 SXX 定义' 标记是否有兜底策略"
      severity: P1

  - id: R004
    scope: universal
    hit_count: 0
    total_rounds: 0
    pre_flight:
      check: "grep 所有版本号引用，与目标文档头部一致"
      severity: P2
    post_flight:
      check: "版本号引用是否与目标文档头部一致"
      severity: P2

  - id: R005
    scope: universal
    hit_count: 0
    total_rounds: 0
    pre_flight:
      check: "grep 所有硬编码行号（如 L180），无残留"
      severity: P2
    post_flight:
      check: "硬编码行号残留"
      severity: P2

  # --- 项目特定规则（scope: project，不开源） ---
  
  - id: R101
    scope: project
    project: yaya-zhujiao
    hit_count: 0
    total_rounds: 0
    pre_flight:
      check: "确认已读取 NORTH_STAR.md，在自检声明中列出 '待本系统定义' 条目清单"
      severity: P2
    post_flight:
      check: "自检声明中是否包含 NORTH_STAR 待定义条目清单"
      severity: P2
```

### 进化规则新增流程

文档 approved 后触发进化总结，生成新规则建议写入 `evolution_rules.yaml`：

```yaml
# 新规则建议（示例）
  - id: R006
    scope: universal
    status: pending          # pending = 待 owner 审核
    source_round: 3          # 在第3轮迭代中产生
    hit_count: 0
    total_rounds: 0
    pre_flight:
      check: "grep 所有枚举值，确认与接口文档完全一致"
      severity: P1
    post_flight:
      check: "枚举值与接口文档一致性"
      severity: P1
```

---

## 10. 质量评分模块

### 10.1 合规分计算

```python
# /Users/liufeng/Documents/DocProductionReview/scripts/quality_score.py

def calculate_compliance_score(doc: dict) -> dict:
    """计算合规分（0 token 成本，纯自动化）"""
    score = 0
    breakdown = {}
    
    # 1. 必备章节完整度（满分20）
    required_sections = [
        '核心概念定义',
        '系统冷启动默认值',
        '新实体默认值',
        '异常恢复策略',
        '交互风险',
        '极端场景验证',
        '跨系统引用落地验证',
    ]
    present = sum(1 for s in required_sections if has_section(doc, s))
    breakdown['章节完整度'] = {'score': present / len(required_sections) * 20, 'max': 20}
    score += present / len(required_sections) * 20
    
    # 2. 跨引用准确率（满分20）
    # Sxx 引用在目标文档头部版本号一致比例
    refs = extract_cross_refs(doc)
    matched = sum(1 for r in refs if check_version_match(r))
    breakdown['跨引用准确率'] = {'score': matched / len(refs) * 20 if refs else 20, 'max': 20}
    score += matched / len(refs) * 20 if refs else 20
    
    # 3. 默认值一致性（满分20）
    # AI-MUTABLE 字段最多出现几个不同值的倒数
    values = extract_ai_mutable_values(doc)
    unique_values = len(set(values))
    breakdown['默认值一致性'] = {'score': 20 / max(unique_values, 1), 'max': 20}
    score += 20 / max(unique_values, 1)
    
    # 4. 极端场景覆盖率（满分20）
    scenarios = ['刚启动', '崩溃重启', '所有依赖同时挂']
    covered = sum(1 for s in scenarios if has_scenario(doc, s))
    breakdown['极端场景覆盖率'] = {'score': covered / len(scenarios) * 20, 'max': 20}
    score += covered / len(scenarios) * 20
    
    # 5. 变更记录合规（满分20）
    changelog_ok = check_changelog_compliance(doc)
    breakdown['变更记录合规'] = {'score': 20 if changelog_ok else 0, 'max': 20}
    score += 20 if changelog_ok else 0
    
    return {'score': round(score, 1), 'breakdown': breakdown}
```

### 10.2 AI 质量分

文档 signed_off 后触发（即 P2 清零 + 终审签字后），使用廉价模型（deepseek-chat），约 10K tokens。
# 注意：不在 approved 或 p2_clearing 时触发，确保评分反映 P2 修复后的最终质量。

```python
def calculate_ai_quality_score(file_path: str) -> dict:
    """AI 独立阅读全文，对5个维度评分（1-5分换为百分制）"""
    doc_text = open(file_path).read()
    
    # 构造 prompt 让 AI 评分
    prompt = f"""
    你是一个文档质量评估专家。请独立阅读以下技术文档全文，并对5个维度评分。
    
    文档路径：{file_path}
    
    评分标准（每个维度1-5分）：
    1. 可操作性：新工程师能否照着文档写代码？
    2. 异常覆盖度：崩溃/超时/数据丢失/格式错误是否有方案？
    3. 决策可追溯：重要设计决定是否说明了"为什么这么做"？
    4. 外部一致性：引用的其他系统信息是否对得上？
    5. 内部自洽：同一信息在不同章节说法是否一致？
    
    请输出 JSON 格式：
    {{"scores": {{"operability": 4, "exception_coverage": 3, "traceability": 5, "external_consistency": 4, "internal_consistency": 3}}, "reasoning": "..."}}
    """
    
    # 调用 AI 模型（deepseek-chat）
    # ...
    
    scores = response['scores']
    avg = sum(scores.values()) / len(scores)
    ai_score = avg * 20  # 1-5 分转 0-100 分
    
    return {'score': round(ai_score, 1), 'dimensions': scores}
```

### 10.3 缺陷趋势分

```python
def calculate_defect_trend(task_id: str, project: str) -> float:
    """追踪同一文档各版本间的 P0/P1/P2 数量变化"""
    # 从审计报告中提取各版本的缺陷数量
    versions = get_defect_counts(task_id, project)
    
    if len(versions) < 2:
        return 0.0  # 首版基线 0 分
    
    latest = versions[-1]
    previous = versions[-2]
    
    score = 0.0
    # 每下降一个 P0/P1 -> +10 分
    p0_drop = previous.get('P0', 0) - latest.get('P0', 0)
    p1_drop = previous.get('P1', 0) - latest.get('P1', 0)
    score += p0_drop * 10 + p1_drop * 10
    
    # 每上升一个 P0/P1 -> -20 分
    p0_rise = latest.get('P0', 0) - previous.get('P0', 0)
    p1_rise = latest.get('P1', 0) - previous.get('P1', 0)
    score -= p0_rise * 20 + p1_rise * 20
    
    return round(score, 1)
```

### 10.4 总分

```python
def calculate_total_score(task_id: str, project: str, file_path: str) -> dict:
    compliance = calculate_compliance_score(file_path)
    ai_quality = calculate_ai_quality_score(file_path)
    defect_trend = calculate_defect_trend(task_id, project)
    
    total = compliance['score'] * 0.4 + ai_quality['score'] * 0.4 + defect_trend * 0.2
    
    result = {
        'compliance': compliance['score'],
        'ai_quality': ai_quality['score'],
        'defect_trend': defect_trend,
        'total': round(total, 1),
    }
    
    # 分差 > 40 阻断
    has_deviation = abs(ai_quality['score'] - compliance['score']) > 40
    
    return result, has_deviation
```

---

## 11. 部署与运维

### 11.1 首次部署步骤

```bash
# 1. 创建目录结构
mkdir -p /Users/liufeng/Documents/DocProductionReview/{projects/{yaya-zhujiao,project-spark,project-spark-adult},audit-reports,.kanban/.alerts,reusable-review-rules,scripts}

# 2. 安装依赖
pip install watchdog

# 3. 配置 Hermes Profile
# 编辑 ~/.hermes/profiles/yaya/config.yaml
# 编辑 ~/.hermes/profiles/yaya-reviewer/config.yaml
# 编辑 ~/.hermes/profiles/yaya-watcher/config.yaml

# 4. 注册 cron job
# 在 yaya profile 中注册 writer agent cron job（配置参考第 3.1 节）
# 在 yaya-reviewer profile 中注册 review-yaya-zhujiao cron job

# 5. 创建 evolution_rules.yaml 初始模板
# 参考第9章内容

# 6. 启动 Watcher daemon
launchctl load ~/Library/LaunchAgents/com.docprodreview.watcher.yaya.plist

# 7. 检查 watcher 是否正常启动
cat /Users/liufeng/Documents/DocProductionReview/.kanban/watcher_started_yaya-zhujiao.json  # 按项目名称替换
```

### 11.2 日常运维

```bash
# 查看 watcher 心跳
cat /Users/liufeng/Documents/DocProductionReview/.kanban/watcher_heartbeat_yaya-zhujiao.json  # 按项目名称替换

# 查看 alert
ls -la /Users/liufeng/Documents/DocProductionReview/.kanban/.alerts/

# 重启 watcher
launchctl unload ~/Library/LaunchAgents/com.docprodreview.watcher.yaya.plist
launchctl load ~/Library/LaunchAgents/com.docprodreview.watcher.yaya.plist

# 查看 kanban 任务
python3 -c "
import sys; sys.path.insert(0, '/Users/liufeng/Documents/DocProductionReview')
from kanban_ops import get_tasks_by_status
tasks = get_tasks_by_status('yaya-zhujiao', None) # 全部任务
"

# 手动创建测试 task
python3 -c "
import sys; sys.path.insert(0, '/Users/liufeng/Documents/DocProductionReview')
from kanban_ops import create_task
tid = create_task('yaya-zhujiao', '测试：审核 S01 - 知识管理系统',
                  '/Users/liufeng/Documents/芽芽AI助教/subsystems/S01_KNOWLEDGE_MANAGEMENT_SYSTEM.md',
                  'v3.1.17')
print(f'Created task: {tid}')
"
```

### 11.3 日志查看

```bash
# Watcher 日志
tail -f /tmp/docprod_watcher_yaya.log

# Hermes Cron 日志
ls ~/.hermes/profiles/yaya/logs/
ls ~/.hermes/profiles/yaya-reviewer/logs/
```

---

## 附录：关键文件清单

| 文件 | 职责 | 实现阶段 |
|------|------|----------|
| `kanban_ops.py` | Kanban SQLite 操作封装 | Phase 1 |
| `scripts/watch.py` | （已弃用）agent cron 直接扫描 kanban | Phase 1 -> 弃用 |
| `scripts/watcher_daemon.py` | Watchdog daemon + 4个看门狗 | Phase 1 |
| `reusable-review-rules/wrapper.py` | Vale/markdownlint 语法检查 | Phase 1 |
| `evolution_rules.yaml` | 自我进化规则（初始模板） | Phase 1 |
| `scripts/quality_score.py` | 质量评分计算 | Phase 3 |
| `scripts/evolution_summary.py` | 进化总结生成 | Phase 3 |
| `launchctl plist` | Watcher 自动重启管理 | Phase 1 |
| Writer SOUL.md | Writer 人设定义 | Phase 2 |
| Reviewer SOUL.md | Reviewer 人设定义 | Phase 2 |
