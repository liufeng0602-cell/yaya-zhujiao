# 自动化文档生产-审核循环工作流 开发者指南 v1.6

基于 PRD v2.7 实现。本文档提供每个模块的实现细节：文件路径、接口签名、数据模型 DDL、配置文件模板、命令行参数。目标是：照着本文档就能写代码。

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.6 | 2026-05-19 10:54 | 对话框改为默认模式、VV2.0修复、停止状态stale前端抑制、卡滞任务三按钮按状态规则、版本传递修复；同步PRD v2.7 |
| v1.4 | 2026-05-19 09:53 | Dashboard 看板7列分组: 已封版/文档目录/文档撰写/审查+修改/复审+修改/人工审核/阻塞、过渡消息更新、人审不通过退回复审+修改、人审对话框Hermes Chat API模块 |
| v1.2 | 2026-05-18 14:30 | 同步PRD v2.3实现：状态机重排、fswatch守护进程、Dashboard自动化控制、NOTIFY机制、auto-repair、human_feedback闭环、Profile三态显示 |
| v1.1 | 2026-05-18 14:09 | 审核 v1.0 全量修复：P0-1 p2_clearing->needs_revision 状态机修正；P0-2 Reviewer 直接设 p2_clearing 不再等 watcher；P0-3 增加 p2_cleared 中间状态+Writer P2_FIXED 标记；P1-1 get_tasks_by_status status 参数改为可选；P1-2 blocked 恢复 fallback 修复；P1-3 心跳/启动标记文件按项目区分；P1-4 质量评分触发改到 signed_off 后；P1-5 fromisoformat 改 strptime；P1-6 移除 no_agent watch.py 改为 Writer agent cron 直接扫描 kanban；P1-7 needs_revision->drafting 遗漏（writer_revision_workflow 跳过 claim，与状态机矛盾）；P2-1 3.2 注释残留修复；P2-2 6.2 通知+暂停cron 函数修复；P2-2 git 仓库路径统一；P2-3 部署步骤修复；P2-4 Writer 新增 3.4 p2_clearing 处理流程；P3-3 check_stuck_tasks 增加 p2_clearing 超时；P3-1 PRD 质量评分触发时机同步 signed_off；补充建议：previous_status 字段/git diff 守卫/wrapper.py 强制自检/prompt 单任务锁定/PRD 同步； |

## 目录

1. [项目目录结构](#1-项目目录结构)
2. [Kanban 模块](#2-kanban-模块)
3. [Writer 模块](#3-writer-模块)
4. [Reviewer 模块](#4-reviewer-模块)
5. [fswatch 守护进程](#5-fswatch-守护进程替代旧-watcher-daemon)
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
├── PRD_AUTO_DOC_WORKFLOW.md            # PRD v2.3
├── evolution_rules.yaml                # 自我进化规则
├── reusable-review-rules/              # 可复用检测规则
│   ├── wrapper.py                      # Vale/markdownlint 调用入口
│   ├── .vale.ini                       # Vale 配置
│   └── .markdownlint.yaml              # markdownlint 配置
├── dashboard.py                        # FastAPI Web Dashboard (port 9119)
├── kanban_ops.py                       # Kanban SQLite 操作封装
├── projects/                           # 各项目的文档目录
│   ├── yaya-zhujiao/
│   ├── project-spark/
│   └── project-spark-adult/
├── audit-reports/                      # 审核报告目录
├── .kanban/                            # kanban board + 控制 + 通知
│   ├── yaya.db                         # 芽芽项目的 kanban SQLite
│   ├── project-spark.db                # Spark 项目的 kanban SQLite
│   ├── project-spark-adult.db          # Spark Adult 项目的 kanban SQLite
│   ├── .notify/                        # NOTIFY 文件目录（事件驱动触发）
│   │   ├── writer-yaya-zhujiao         # → 触发 Writer
│   │   └── review-yaya-zhujiao         # → 触发 Reviewer
│   ├── .control/                       # 自动化控制状态
│   │   └── automation_state.json       # {running, paused, message, updated_at}
│   ├── .alerts/                        # Alert 文件目录
│   ├── writer_format_notes.md          # Writer 格式模板自查记录
│   └── reviewer_scope_notes.md         # Reviewer 审核范围自查记录
└── scripts/                            # 辅助脚本
    ├── fswatch_daemon.py               # fswatch 事件驱动守护进程（替换旧 watcher_daemon.py）
    ├── writer.py                       # Writer 主脚本（扫描 kanban + 自检 + commit + NOTIFY）
    ├── reviewer.py                     # Reviewer 主脚本（审核 + re_review + 审计报告）
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
    status          TEXT NOT NULL DEFAULT 'backlog',  -- 状态值: backlog|drafting|awaiting_review|reviewing|revision|re_review|re_reviewing|waiting_human_review|signed_off|blocked
    assigned_to     TEXT,                     -- 分配给哪个 profile: writer|reviewer|liufeng
    project         TEXT NOT NULL,            -- 项目标识: yaya-zhujiao|project-spark|project-spark-adult
    file_path       TEXT,                     -- 被审核文档的绝对路径
    version         TEXT,                     -- 文档当前版本号, 如 v3.1.17
    commit_sha      TEXT,                     -- 当前版本对应的 git commit SHA
    iteration_count INTEGER DEFAULT 0,        -- 迭代轮次, 从0开始。reviewer 判定 revision 时 +1
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
    """iteration_count +1（reviewer 判定 revision 时调用）"""
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
| awaiting_review -> reviewing | reviewer | reviewer claim task |
| reviewing -> revision | reviewer | P0>0 或 P1>0（有 P0/P1 问题） |
| reviewing -> revision | reviewer | P0=P1=0 但 P2>0（仅有 P2 清零） |
| reviewing -> waiting_human_review | reviewer | P0=P1=0 且 P2=0（全部通过） |
| revision -> drafting | writer | writer 接手修改（claim） |
| revision -> re_review | writer | 修改完成 + 自检通过 + commit |
| drafting (auto-repair) -> drafting | writer | 自检/commit 失败，auto_repair_attempts < 3 时重试 |
| drafting (auto-repair) -> awaiting_review | writer | 自检/commit 失败达到 3 次上限（backlog 任务送审） |
| drafting (auto-repair) -> revision | writer | 自检/commit 失败达到 3 次上限（revision 任务继续重试） |
| re_review -> re_reviewing | reviewer | reviewer claim task |
| re_reviewing -> revision | reviewer | 复审不通过（P0>0 或 P1>0） |
| re_reviewing -> waiting_human_review | reviewer | 复审通过（P0=P1=0，P2 不限） |
| waiting_human_review -> signed_off | liufeng | 人工评审通过 + 终审签字 |
| 任意状态 -> blocked | fswatch/liufeng | 异常/6轮上限/token超支

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

### 2.6 Dashboard 过渡消息机制

每次状态变更时，`update_task_extra` 会自动记录 `previous_status` 到 `extra` 字段（JSON）。Dashboard 读取任务时，如果 `status_entered_at` 在 10 秒内，则根据 `(previous_status, current_status)` 拼接过渡消息。

**过渡消息映射表（dashboard.py /api/board）：**

| previous_status | current_status | 过渡消息 |
|-----------------|---------------|---------|
| drafting | awaiting_review | 撰写已完成，5秒后进入审查+修改环节 |
| reviewing | revision | 审查不通过，5秒钟后进入修改阶段 |
| reviewing | waiting_human_review | 审查通过，5秒钟后进入人工审核环节 |
| re_reviewing | revision | 复审不通过，5秒钟后进入修改阶段 |
| re_reviewing | waiting_human_review | 复审通过，5秒钟后进入人工审核环节 |
| waiting_human_review | finalized | 人工审核通过，5秒钟后封版 |
| waiting_human_review | re_review | 人工审核不通过，5秒钟后进入复审+修改环节 |

**倒计时实现（前端 JS）：**
- `startTransitionCountdowns()` 在每次 `render()` 后调用
- 扫描所有 `.transition-banner` 元素，为每个启动 5 秒 `setInterval`
- 倒计时到 0 时自动移除 DOM 元素
- 使用独立的定时器 key（按元素 id），互不干扰

**自动化停止覆盖（/api/board）：**
- 读取 `automation_state.json`，若 `running=false`，对所有非 finalized/blocked/backlog 的卡片注入 `stale=true, stale_reason="修改已停止，如果想要继续修改，请点击「开始」按钮"`

**已封版不报错（calc_elapsed）：**
- 接收到 `finalized` 状态的任务直接返回 `stale=False`，跳过所有超时和中断检测逻辑。
- stale_reason 为空字符串。

### 2.7 Dashboard 看板 7 列布局

从 v1.4 起，Dashboard 看板从 10 列合并为 7 列。**DB 状态不动，只改 dashboard 层列分组映射。**

KANBAN_LAYOUT 定义（dashboard.py 第 26 行）：
```python
KANBAN_LAYOUT = [
    ("finalized",        "已封版",    False, ("finalized",), ...),
    ("backlog",          "文档目录",  False, ("backlog",), ...),
    ("drafting",         "文档撰写",  False, ("drafting",), ...),
    # 审查+修改（组合列）：上栏=审查中，下栏=待审查+修改中
    ("review_modify",    "审查+修改", True,  ("reviewing", "awaiting_review", "revision"), ...),
    # 复审+修改（组合列）：上栏=复审中，下栏=复审不通过，等待修改
    ("re_review_modify", "复审+修改", True,  ("re_reviewing", "re_review"), ...),
    ("human_review",     "人工审核",  False, ("waiting_human_review",), ...),
    ("blocked",          "阻塞",      False, ("blocked",), ...),
]
```

组合列（combined）在 HTML 中渲染为上下两个分区，各带独立 sub-header 标签。Section labels 通过 `section_labels` 字典映射：
- review_modify: 上栏="审查中"，下栏="待审查 / 修改中"
- re_review_modify: 上栏="复审中"，下栏="复审不通过，等待修改"

### 2.8 人工审核对话框模块（Hermes Chat API）

当 liufeng 对等待人工审核（`waiting_human_review`）的文档打开详情页时，**直接进入对话框评审模式**，不再显示简单文本框。用户输入意见后，评审P实时对话，直到达成共识后点击「提交」确认。

**核心流程变化（v1.6 起）：**

- 旧方案：详情页显示文本框 → 点击「对话评审」按钮 → 进入对话框
- 新方案：详情页直接进入对话框模式，用户输入意见即开始对话
- 达成共识后点击「确认并触发 Writer」→ 任务状态变成 `re_review`（复审已完成，直接进入修改环节）
- 生产P（Writer）拿到达成一致的修改建议直接改，不再经过 Reviewer 复审

**后端 API（dashboard.py）：**

| 端点 | 方法 | 功能 |
|------|------|------|
| /api/human-review-dialog/{task_id} | POST | liufeng 输入意见，Dashboard 调 Hermes Chat API 模拟 Reviewer 回复 |
| /api/human-review-consensus/{task_id} | POST | 双方达成共识后，状态转为 re_review 并写 NOTIFY 触发 Writer |

**对话流程（v1.6 起）：**
1. liufeng 打开 `waiting_human_review` 文档详情 → 直接进入对话框模式
2. 对话框自动显示「请描述您的评审意见或修改要求」提示
3. liufeng 在对话框中输入意见，点击「发送」
4. Dashboard 调用 `hermes chat -q "prompt" --profile yaya` 评审P上下文中包含文档原文 + 用户意见
5. 评审P回复展示在对话框中（审核分析 + 修改建议）
6. 可多轮对话（继续输入新意见 → 评审P继续回复），直到达成共识
7. liufeng 修改共识区的文本后点击「确认并触发 Writer」

**API 调用方式：** 使用 subprocess 调用 Hermes Chat CLI（2 秒响应）
- CLI: `/Users/liufeng/.hermes/hermes-agent/venv/bin/hermes chat -q "prompt" --profile yaya`
- 注意：不加 `--accept-hooks`（会导致挂起）
- 输出解析：取最后一条 `╭─ Hermes` 框内的正文

**共识达成后：**
- 生成修改指令 JSON 文件写到 `.kanban/.notify/instructions-{project}/{task_id}.json`
- 写 NOTIFY 文件触发 Writer（`writer-{project}`）
- 更新任务状态为 revision（退回复审+修改流程）
- human_feedback 截断：max 500 chars × 3 items

### 2.9 Dashboard UI 交互细节

基于 PRD v2.6 的 14.7-14.10 实现。

**卡片状态徽标：**

API 返回的 `workflow_status` 字段控制每张卡片的顶部徽标。字段值：
- `"running"` — 显示 ▶ 进行中（绿色 `#3fb950`，背景 `#3fb95022`）
- `"stopped"` — 显示 ⏹ 已停止（红色 `#f85149`，背景 `#f8514933`）

设置逻辑（dashboard.py `build_task` 两处，line 1124-1126 和 1213-1215）：
```python
workflow_status = "stopped" if (auto_stopped and status not in ('finalized', 'blocked', 'backlog')) else "running"
```
仅当 `automation_state.running=False` 且状态不为 finalized/blocked/backlog 时设为 "stopped"。不修改 stale 或 stale_reason，不干扰原有的 timer 超时机制。

**停止状态 stale 抑制（v1.6 起）：**

后端 `build_task()` 两处在设置 `workflow_status` 后立即检查：
```python
if workflow_status == "stopped":
    stale = False
    stale_reason = ""
```
前端 `openDoc()` 在判断是否展示「任务处理建议」模块时，额外检查 `d.workflow_status !== 'stopped'`：
```javascript
if (d.timer_stale && statusList.includes(status) && d.workflow_status !== 'stopped') {
```
停止状态下，「⏹ 已停止」徽标已传达状态，底部不再出现任何 ⚠ 报错。

**文档版本号显示（修复 VV2.0 bug，v1.6 起）：**

```javascript
// 旧：${t.version ? '<span>v'+t.version+'</span>' : ''}    → 显示 vv2.0
// 新：${t.version ? '<span>'+t.version+'</span>' : ''}     → 显示 v2.0
```
DB 中 version 字段已包含 `v` 前缀（如 `v2.0`），模板直接展示不再额外加 "v"。

**卡滞任务处理：三按钮按状态规则（v1.6 起）：**

文档详情页的「任务处理建议」模块（#stuckActions）展示三按钮，按状态规则隐藏不可用的选项：

| 状态 | 显示按钮 | 逻辑 |
|------|---------|------|
| drafting | 全部（重新触发 / 退回待领取 / 标记阻塞） | Writer 停滞有多种处置方式 |
| awaiting_review | 仅「重新触发」 | Reviewer 未认领，只有重触发有意义 |
| reviewing | 重新触发 + 标记阻塞 | Reviewer 审核中停滞，可重试或阻塞 |
| revision | 重新触发 + 标记阻塞 | Writer 修改停滞 |
| re_review | 仅「重新触发」 | 复审等待 Reviewer，只有重触发 |
| re_reviewing | 重新触发 + 标记阻塞 | 复审中停滞 |
| waiting_human_review | 不展示（等人审） | 等待用户操作 |

JS 实现（`openDoc()` 内）：
```javascript
const retriggerBtn = document.querySelector('#stuckActions .ctrl-btn[onclick*="retriggerTask"]');
const resetBtn = document.querySelector('#stuckActions .ctrl-btn[onclick*="resetTaskToBacklog"]');
const blockBtn = document.querySelector('#stuckActions .ctrl-btn[onclick*="markTaskBlocked"]');
// 默认全部显示
// 按状态规则隐藏
if (status === 'awaiting_review' || status === 're_review') {
    resetBtn.style.display = 'none';
    blockBtn.style.display = 'none';
} else if (status === 'reviewing' || status === 'revision' || status === 're_reviewing') {
    resetBtn.style.display = 'none';
}
```

卡片徽标 CSS：
```css
.card-workflow-status{font-size:10px;font-weight:600;margin-bottom:4px;padding:1px 6px;border-radius:4px;display:inline-block}
.card-running{color:var(--green);background:#3fb95022}
.card-stopped{color:var(--red);background:#f8514933}
```

**停止提示 stopHint：**

HTML 结构（section-title 内，停止按钮下方）：
```html
<div id="stopHint" style="display:none;margin-top:4px;font-size:12px;color:var(--yellow)">
  修改已停止，如果想继续修改，请点击「开始」按钮
</div>
```

JS 控制（render() 内，控制按钮样式更新时）：
```javascript
const stopHint = document.getElementById('stopHint');
if (stopHint) stopHint.style.display = (!d.running) ? 'block' : 'none';
```

自动化运行中 hidden（display:none），停止时 block。

**暂停按钮移除：**

- HTML 中删除 `<button id="ctrlPause">` 元素
- JS 中删除 `document.getElementById('ctrlPause').className = ...` 行
- 后端 API `/api/automation/control?action=pause` 保留不动（向后兼容）

**空状态与组合列子标移除：**

dashboard.py JS render() 中的三段改动：

1. 单列空状态：`'<div class="empty">空</div>'` → `''`（line 458）
2. 组合列上栏空状态：`'<div class="empty">' + col.upper_label + ': 0</div>'` → `''`（line 450）
3. 组合列上栏 sub-header：`'<div class="sub-header">↑ ' + col.upper_label + ' (' + col.upper_count + ')</div>'` → `''`（line 449）
4. 组合列下栏 sub-header：`'<div class="sub-header">↓ ' + col.lower_label + ' (' + col.lower_count + ')</div>'` → `''`（line 451）

组合列保留上下分区结构（`.combined-section` div 容器），只去掉标签文本。上栏空时整个分组不渲染。下栏空时也不渲染任何内容。

**卡片宽度与文件路径截断：**

CSS 改动（dashboard.py `<style>` 区域）：

```css
/* 防 flex 溢出 */
.card-meta{...;min-width:0;max-width:100%}

/* 文件路径用省略号截断 */
.file-path{display:inline-block;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:bottom}
```

---

## 3. Writer 模块

### 3.1 Writer 触发机制（NOTIFY 文件驱动）

Writer 不由 cron job 触发，而是由 fswatch 守护进程在检测到 NOTIFY 文件（`.kanban/.notify/writer-<project>`）后调用 `hermes chat` 启动。

fswatch 守护进程中的 prompt_builder 会检查 kanban 中的 human_feedback，如果有则生成包含分析步骤的详细提示词，否则生成标准提示词。

Writer 主脚本（`scripts/writer.py`）扫描 kanban，按优先级处理 backlog → revision → re_review → drafting（auto-repair）。每次只处理 1 个任务。

扫描优先级定义在 `SCAN_ORDER`：
```python
SCAN_ORDER = ['backlog', 'revision', 're_review', 'drafting']
```

### 3.2 Writer 写作流程

```python
# 关键函数：process_backlog
def process_backlog(task: dict):
    # 1. claim task: backlog -> drafting
    update_task_status(PROJECT, task_id, 'drafting', assigned_to='writer')
    
    # 2. 读需求、写文档（由 agent 在 prompt 执行，writer.py 仅创建占位文件）
    
    # 3. 自检：wrapper.py 语法检查
    if not run_self_check(file_path):
        # 自检失败 -> 自动修复重试
        attempts = increment_auto_repair(PROJECT, task_id, 'self_check_failed')
        handle_auto_repair_result(PROJECT, task_id, attempts, max_attempts=3,
                                   target_on_exhaust='awaiting_review')
        return
    
    # 4. git commit
    sha = do_git_commit(file_path, msg)
    if sha:
        update_task_status(PROJECT, task_id, 'awaiting_review', commit_sha=sha)
    else:
        # commit 失败 -> 自动修复重试
        attempts = increment_auto_repair(PROJECT, task_id, 'commit_failed')
        handle_auto_repair_result(PROJECT, task_id, attempts, max_attempts=3,
                                   target_on_exhaust='awaiting_review')
        return
    
    # 5. 写 NOTIFY 触发 reviewer
    trigger_reviewer()  # 写入 .kanban/.notify/review-<project>
```

### 3.3 revision 修改规则（合并旧 needs_revision 和 p2_clearing）

revision 状态统一处理 P0/P1 修复和 P2 清零，不再区分 needs_revision 和 p2_clearing。

```python
def process_revision(task: dict):
    # 1. claim task: revision/drafting -> drafting（re_review 时 claim）
    if current_status != 'drafting':
        claim_task(task_id, current_status)
    
    # 2. 读取审核报告和人工反馈
    comments = get_comments(PROJECT, task_id)
    review_comments = [c for c in comments if c['author'] == 'reviewer']
    
    # 3. 读取 revision_data（含 P 级分布和修理状态）
    revision_data = json.loads(task.get('revision_data') or '{}')
    
    # 4. 修改文档（由 agent 在 prompt 中执行）
    
    # 5. 自检 + wrapper.py 语法检查
    if not run_self_check(file_path):
        attempts = increment_auto_repair(PROJECT, task_id, 'self_check_failed')
        handle_auto_repair_result(PROJECT, task_id, attempts, max_attempts=3,
                                   target_on_exhaust='revision')
        return
    
    # 6. git commit
    sha = do_git_commit(file_path, msg)
    if sha:
        update_task_status(PROJECT, task_id, 're_review', commit_sha=sha)
    else:
        attempts = increment_auto_repair(PROJECT, task_id, 'commit_failed')
        handle_auto_repair_result(PROJECT, task_id, attempts, max_attempts=3,
                                   target_on_exhaust='revision')
        return
    
    # 7. 写 NOTIFY 触发 reviewer（复审）
    trigger_reviewer()
```

### 3.4 自动修复机制 (auto-repair)

Writer 自检或 git commit 失败时不再直接 blocked，而是进入自动修复重试循环：

```python
def handle_auto_repair_result(project, task_id, attempts,
                               max_attempts=3,
                               target_on_exhaust='awaiting_review'):
    if attempts < max_attempts:
        # 写 writer NOTIFY 触发重试（不改变看板状态）
        write_notify(f'writer-{project}')
    else:
        # 已达上限
        should_retry_writer = target_on_exhaust in ('revision', 're_review')
        update_task_status(project, task_id, target_on_exhaust)
        if should_retry_writer:
            # revision 任务继续重试（写 writer NOTIFY）
            write_notify(f'writer-{project}')
        else:
            # backlog 任务送审（写 reviewer NOTIFY）
            write_notify(f'review-{project}')
```

设计原则：Writer 自己的 bug 自己修，修不好就交给 Reviewer 挑问题。Revision 任务的自检/commit 失败即使达到 3 次上限也继续重试（避免死循环），backlog 任务则送审。

### 3.5 人工反馈闭环 (human_feedback)

当 revision/re_review 任务包含 human_feedback（来自 liufeng 在 Dashboard 上的评审意见）时，fswatch 守护进程的 `build_writer_prompt()` 生成包含 4 步的详细提示词：

1. **分析反馈**：逐条判断属实/半属实/不属实
2. **修改文档**：根据分析结果修改
3. **格式模板自查**：分析反馈中是否有 Writer 格式模板未覆盖的规则 → 写入 `.kanban/writer_format_notes.md`
4. **提交**：执行 writer.py

human_feedback 截断规则：最多 3 条，每条 500 字符，超额截断并注明「共 N 字符，已截断」。防止 Writer agent 因过长反馈超时。

## 4. Reviewer 模块

### 4.1 触发机制（NOTIFY 文件驱动）

Reviewer 不由 cron job 触发，而是由 fswatch 守护进程在检测到 NOTIFY 文件（`.kanban/.notify/review-<project>`）后调用 `hermes chat` 启动。

Reviewer 主脚本（`scripts/reviewer.py`）执行逻辑：
1. 优先处理 `re_review` 任务（复审），按 updated_at 最旧优先
2. 如果没有复审任务，处理 `awaiting_review` 任务（首次审核）
3. 每次只处理 1 个任务

```python
def main():
    # 1. 优先复审
    re_review_tasks = get_tasks_by_status(PROJECT, 're_review')
    if re_review_tasks:
        re_review_tasks.sort(key=lambda t: t.get('updated_at', ''))
        task = re_review_tasks[0]
        process_re_review(task)
        return
    
    # 2. 首次审核
    tasks = get_tasks_by_status(PROJECT, 'awaiting_review')
    if not tasks:
        print("[REVIEWER] 无待审核任务")
        return
    task = tasks[0]
    process_review(task)
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
    
    # 4. 判定（三项分流）
    if p0_count > 0 or p1_count > 0:
        # 有 P0/P1 问题 -> revision
        increment_iteration(project, task['id'])
        update_task_status(project, task['id'], 'revision')
        add_comment(project, task['id'], 'reviewer',
                    f'审核不通过 (P0={p0_count} P1={p1_count})。审计报告：{report_path}')
    elif p2_count > 0:
        # 只有 P2 问题 -> revision（P2 清零，不增加 iteration_count）
        update_task_status(project, task['id'], 'revision',
                           revision_data='{"is_p2_clear": true}')
        add_comment(project, task['id'], 'reviewer',
                    f'P0=P1=0 但 P2={p2_count}，进入 revision (P2 清零)。审计报告：{report_path}')
    else:
        # 全通过 -> waiting_human_review
        update_task_status(project, task['id'], 'waiting_human_review')
        add_comment(project, task['id'], 'reviewer', f'审核通过，等待人工评审。审计报告：{report_path}')
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

## 5. fswatch 守护进程（替代旧 Watcher Daemon）

### 5.1 架构

路径：`/Users/liufeng/Documents/DocProductionReview/scripts/fswatch_daemon.py`

旧 Python watchdog watcher 已被完全替换为 fswatch 守护进程。核心架构：

```python
# fswatch_daemon.py — 381 行
#!/usr/bin/env python3
"""fswatch 事件驱动守护进程 — 监听 .notify/ 目录，零轮询触发 Hermes 任务"""

NOTIFY_DIR = "/Users/liufeng/Documents/DocProductionReview/.kanban/.notify"
CONTROL_DIR = "/Users/liufeng/Documents/DocProductionReview/.kanban/.control"
CONTROL_FILE = os.path.join(CONTROL_DIR, "automation_state.json")
HERMES = "/Users/liufeng/.hermes/hermes-agent/venv/bin/hermes"
KANBAN_DB = "/Users/liufeng/Documents/DocProductionReview/.kanban/yaya-zhujiao.db"
```

核心组件：
| 函数 | 职责 |
|------|------|
| `get_automation_state()` | 读取自动化控制状态（running/paused/stopped） |
| `handle_notify(filepath)` | 处理单个 NOTIFY 文件：检查状态→按前缀路由→触发 Writer/Reviewer→清除 |
| `bootstrap()` | 定时自愈：扫描 kanban→发现待处理任务→写 NOTIFY→处理 stale re_review→补发 |
| `build_writer_prompt()` | 构建 Writer agent 提示词（含 human_feedback 分析步骤） |
| `build_reviewer_prompt()` | 构建 Reviewer agent 提示词（含 scope 自查步骤） |
| `main()` | 启动循环：遗留 NOTIFY→bootstrap→fswatch select() 循环→60s 定时 bootstrap |

### 5.2 fswatch 守护进程流程

```
启动:
  └─ 处理遗留 NOTIFY 文件（启动时残存的）
  └─ bootstrap() 扫描 kanban，写 NOTIFY
  └─ 处理 bootstrap 写的 NOTIFY
  └─ 启动 fswatch 二进制监听 .kanban/.notify/
  └─ select() 循环:
       ├─ 收到事件 → handle_notify()
       ├─ 每60s超时 → 检查自动化状态，如运行中则 bootstrap()
       └─ fswatch stdout 关闭 → 退出
```

### 5.3 自动化控制状态

Dashboard 控制按钮写入 `.kanban/.control/automation_state.json`。fswatch daemon 在 `handle_notify()` 和定时 bootstrap 时读取此文件：

```json
{
  "running": false,
  "paused": false,
  "message": "已停止",
  "updated_at": "2026-05-18T23:20:23.477766"
}
```

| 状态 | handle_notify 行为 | bootstrap 行为 |
|------|-------------------|----------------|
| running=true, paused=false | 正常处理 NOTIFY | 正常执行 bootstrap |
| running=true, paused=true | 跳过处理，保留 NOTIFY | 跳过 bootstrap |
| running=false, paused=false | 跳过处理，清理 NOTIFY | 跳过 bootstrap |

### 5.4 定时 Bootstrap（60 秒自愈）

`bootstrap()` 每 60 秒执行一次，自动检测：
- `awaiting_review` → 写 reviewer NOTIFY
- `reviewing` → 写 reviewer NOTIFY（补触发）
- `revision` → 写 writer NOTIFY（补触发）
- `re_review` → 先检查 stale 卡片（>5min + re_review_result='fail'）→ 自动迁移到 revision → 写 writer NOTIFY。非 stale → 正常写 reviewer NOTIFY

### 5.5 human_feedback 截断

`build_writer_prompt()` 在读取 human_feedback 时自动截断：
```python
truncated = []
for i, fb in enumerate(raw_feedback[:3]):     # 最多 3 条
    txt = str(fb)
    if len(txt) > 500:                          # 每条最多 500 字符
        txt = txt[:500] + '\n...（共 N 字符，已截断）'
    truncated.append(f'  - {txt}')
if len(raw_feedback) > 3:
    truncated.append('...（还有 M 条反馈被省略）')
```

### 5.6 启动与维护

```bash
# 启动（nohup 后台）
cd /Users/liufeng/Documents/DocProductionReview
nohup /Users/liufeng/.hermes/hermes-agent/venv/bin/python3 scripts/fswatch_daemon.py \
  > /tmp/fswatch_out.log 2>&1 &

# 查看日志
tail -f /tmp/fswatch_out.log
tail -f /Users/liufeng/.hermes/logs/fswatch.log

# 查看正在运行的 Writer/Reviewer 进程
ps aux | grep 'hermes chat'

# 停止 fswatch 守护进程
pkill -f fswatch_daemon.py
pkill -f 'fswatch -0'
```

---

## 6. 通知机制

### 6.1 NOTIFY 文件系统

Writer/Reviewer 完成工作后写 NOTIFY 文件到 `.kanban/.notify/` 目录。fswatch 二进制检测文件创建事件后触发守护进程执行 `handle_notify()`。

```python
# Writer → Reviewer 通知
def trigger_reviewer():
    notify_dir = os.path.join(KANBAN_DIR, '.notify')
    os.makedirs(notify_dir, exist_ok=True)
    notify_path = os.path.join(notify_dir, f'review-{PROJECT}')
    with open(notify_path, 'w') as f:
        f.write(f'NOTIFY by writer at {datetime.now().isoformat()}')

# Reviewer → Writer 通知
def trigger_writer():
    notify_dir = os.path.join(KANBAN_DIR, '.notify')
    os.makedirs(notify_dir, exist_ok=True)
    notify_path = os.path.join(notify_dir, f'writer-{PROJECT}')
    with open(notify_path, 'w') as f:
        f.write(f'NOTIFY by reviewer at {datetime.now().isoformat()}')
```

### 6.2 fswatch 守护进程路由

```python
# fswatch_daemon.py handle_notify()
if filename.startswith("review-"):
    # 触发 Reviewer
    prompt = build_reviewer_prompt()
    subprocess.run([HERMES, "chat", "-q", prompt, "--profile", "yaya-reviewer"],
                   cwd=PROJECT_DIR, timeout=600)
elif filename.startswith("writer-"):
    # 触发 Writer
    prompt = build_writer_prompt()
    subprocess.run([HERMES, "chat", "-q", prompt, "--profile", "yaya"],
                   cwd=PROJECT_DIR, timeout=600)
```

### 6.3 启动时 Prompt 构建

`build_writer_prompt()` 检查 kanban 中是否有 human_feedback：
- **有反馈**：生成包含 4 步的详细提示词（分析反馈→修改→格式自查→执行 writer.py）
- **无反馈**：生成标准提示词「在 PROJECT_DIR 中运行 python3 scripts/writer.py」

`build_reviewer_prompt()` 包含两部分：
1. 运行 reviewer.py
2. 检查复审任务的 human_feedback，分析是否超出审核规则范围 → 写 `reviewer_scope_notes.md`

---

## 7. Profile 配置

每个项目需要 2 个 Hermes Profile（Writer + Reviewer）+ 全局 Dashboard + fswatch 守护进程。不再使用 Hermes cron job 模式——WRiter 和 Reviewer 由 fswatch 守护进程通过 `hermes chat` 调用。

### 7.1 Writer Profile（生产P）

示例：`yaya` profile（芽芽项目的 Writer）

配置文件：`~/.hermes/profiles/yaya/config.yaml`

```yaml
model: deepseek-reasoner
provider: deepseek

# 不再需要 cron job。Writer 由 fswatch 守护进程通过 NOTIFY 文件触发。
# cron 配置留空即可。

# SOUL.md 内容（在 ~/.hermes/profiles/yaya/SOUL.md）
# 职责：文档生产者，负责按规范写出可通过审核的详细设计文档
```

### 7.2 Reviewer Profile（审核P）

示例：`yaya-reviewer` profile

配置文件：`~/.hermes/profiles/yaya-reviewer/config.yaml`

```yaml
model: deepseek-chat
provider: deepseek

# 不再需要 cron job。Reviewer 由 fswatch 守护进程通过 NOTIFY 文件触发。
# cron 配置留空即可。

# SOUL.md 内容
# 职责：文档质量把关人，负责对等待审核和复审的文档执行全量检查
```

### 7.3 Watcher Profile（yaya-watcher）

不再使用独立 watcher profile。fswatch 守护进程（`scripts/fswatch_daemon.py`）承担所有监控职责。如果需要，Watcher profile 仅用于 launchctl 日志归属。

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
# 注意：在 waiting_human_review 后触发（即全部审核通过+人工签字后），确保评分反映最终质量。

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
mkdir -p /Users/liufeng/Documents/DocProductionReview/{projects/{yaya-zhujiao,project-spark,project-spark-adult},audit-reports,.kanban/{.notify,.control,.alerts},reusable-review-rules,scripts}

# 2. 配置 Hermes Profile
# 编辑 ~/.hermes/profiles/yaya/config.yaml（Writer）
# 编辑 ~/.hermes/profiles/yaya-reviewer/config.yaml（Reviewer）
# Writer/Reviewer 都不需要 cron job 配置

# 3. 启动 Dashboard（FastAPI, port 9119）
cd /Users/liufeng/Documents/DocProductionReview
/Users/liufeng/.hermes/hermes-agent/venv/bin/python3 -m uvicorn dashboard:app \
  --host 127.0.0.1 --port 9119 &

# 4. 启动 fswatch 守护进程
nohup /Users/liufeng/.hermes/hermes-agent/venv/bin/python3 \
  scripts/fswatch_daemon.py > /tmp/fswatch_out.log 2>&1 &

# 5. 检查是否正常启动
# Dashboard: 浏览器打开 http://127.0.0.1:9119
# fswatch 日志: tail -f /tmp/fswatch_out.log
```

### 11.2 日常运维

```bash
# 查看 Dashboard
open http://127.0.0.1:9119

# 通过 Dashboard 控制自动化（▶ 运行 / ⏸ 暂停 / ⏹ 停止）

# 查看 fswatch 守护进程日志
tail -f /tmp/fswatch_out.log

# 查看 Hermes 日志
ls ~/.hermes/profiles/yaya/logs/
ls ~/.hermes/profiles/yaya-reviewer/logs/

# 重启 fswatch 守护进程
pkill -f fswatch_daemon.py
pkill -f 'fswatch -0'
nohup /Users/liufeng/.hermes/hermes-agent/venv/bin/python3 \
  scripts/fswatch_daemon.py > /tmp/fswatch_out.log 2>&1 &

# 重启 Dashboard
pkill -f 'uvicorn dashboard:app'
/Users/liufeng/.hermes/hermes-agent/venv/bin/python3 -m uvicorn dashboard:app \
  --host 127.0.0.1 --port 9119 &

# 查看 kanban 任务
python3 -c "
import sys; sys.path.insert(0, '/Users/liufeng/Documents/DocProductionReview')
from kanban_ops import get_tasks_by_status
tasks = get_tasks_by_status('yaya-zhujiao', None)
for t in tasks:
    print(f'{t[\"id\"]} {t[\"title\"]} status={t[\"status\"]} iter={t[\"iteration_count\"]}')
"

# 查看 automation 控制状态
cat /Users/liufeng/Documents/DocProductionReview/.kanban/.control/automation_state.json

# 手动创建测试 task
python3 -c "
import sys; sys.path.insert(0, '/Users/liufeng/Documents/DocProductionReview')
from kanban_ops import create_task
tid = create_task('yaya-zhujiao', '测试：S01 知识管理系统',
                  '/Users/liufeng/Documents/DocProductionReview/projects/yaya-zhujiao/S01_test.md',
                  'v0.1')
print(f'Created task: {tid}')
"
```

### 11.3 日志查看

```bash
# fswatch 守护进程
tail -f /tmp/fswatch_out.log

# Hermes 日志
ls ~/.hermes/profiles/yaya/logs/
ls ~/.hermes/profiles/yaya-reviewer/logs/

# fswatch 守护进程内部日志
tail -f /Users/liufeng/.hermes/logs/fswatch.log
```

---

## 附录：关键文件清单

| 文件 | 职责 | 实现阶段 |
|------|------|----------|
| `kanban_ops.py` | Kanban SQLite 操作封装（含 re_reviewing 状态、revision_data） | Phase 1 |
| `dashboard.py` | FastAPI Web Dashboard，port 9119：看板可视化、自动化控制、Profiles 状态、卡片详情与操作 | Phase 1 |
| `scripts/fswatch_daemon.py` | fswatch 事件驱动守护进程：NOTIFY 监听、automation 控制、定时 bootstrap、human_feedback 截断 | Phase 1 |
| `scripts/writer.py` | Writer 主脚本：扫描 kanban、自检、auto-repair、NOTIFY | Phase 1 → 重写 |
| `scripts/reviewer.py` | Reviewer 主脚本：审核/复审、审计报告、re_reviewing | Phase 1 → 重写 |
| `reusable-review-rules/wrapper.py` | Vale/markdownlint 语法检查 | Phase 1 |
| `evolution_rules.yaml` | 自我进化规则（初始模板） | Phase 1 |
| `.kanban/.control/automation_state.json` | 自动化控制状态文件 | Phase 1 |
| `.kanban/.notify/` | NOTIFY 文件目录（事件驱动触发） | Phase 1 |
| `scripts/quality_score.py` | 质量评分计算 | Phase 3 |
| `scripts/evolution_summary.py` | 进化总结生成 | Phase 3 |
