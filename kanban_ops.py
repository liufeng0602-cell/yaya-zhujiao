#!/usr/bin/env python3
"""Kanban 核心操作库 — SQLite 数据层 + 状态机校验 (v2.1: 加复审状态)"""

import sqlite3
import os
import json
import random
import string
from datetime import datetime

KANBAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.kanban')
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
AUDIT_REPORTS_DIR = os.path.join(PROJECT_ROOT, 'audit-reports')

# ---------- 有效状态列表 ----------
VALID_STATUSES = frozenset([
    'backlog', 'drafting', 'awaiting_review', 'reviewing',
    'revision', 're_review', 'waiting_human_review', 'finalized', 'blocked'
])

# ---------- 状态迁移白名单 ----------
VALID_TRANSITIONS = {
    'backlog':             {'drafting'},
    'drafting':            {'awaiting_review', 're_review', 'blocked'},
    'awaiting_review':     {'reviewing', 'blocked'},
    'reviewing':           {'revision', 'waiting_human_review', 'blocked'},
    'revision':            {'drafting', 're_review', 'blocked'},
    're_review':           {'revision', 'waiting_human_review', 'blocked'},
    'waiting_human_review':{'finalized', 'revision', 'blocked'},
    'finalized':           {'blocked'},
    'blocked':             {'backlog', 'drafting', 'revision', 're_review'},
}

# ---------- DB 迁移 ----------
MIGRATE_SQL = """
ALTER TABLE tasks ADD COLUMN status_entered_at TEXT;
ALTER TABLE tasks ADD COLUMN p0_count INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN p1_count INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN p2_count INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN revision_data TEXT;
"""

MIGRATE_STATUS_SQL = """
UPDATE tasks SET status = 'revision' WHERE status IN ('needs_revision', 'p2_clearing');
UPDATE tasks SET status = 'waiting_human_review' WHERE status IN ('p2_cleared', 'approved');
UPDATE tasks SET status = 'finalized' WHERE status = 'signed_off';
UPDATE tasks SET status_entered_at = datetime('now') WHERE status_entered_at IS NULL;
"""

# ---------- 内部函数 ----------

def _db_path(project: str) -> str:
    os.makedirs(KANBAN_DIR, exist_ok=True)
    return os.path.join(KANBAN_DIR, f'{project}.db')

def _conn(project: str) -> sqlite3.Connection:
    path = _db_path(project)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure_tables(conn)
    _migrate_schema(conn)
    return conn

def _ensure_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id              TEXT PRIMARY KEY,
            title           TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'backlog',
            assigned_to     TEXT,
            project         TEXT NOT NULL,
            file_path       TEXT,
            version         TEXT,
            commit_sha      TEXT,
            iteration_count INTEGER DEFAULT 0,
            tokens_budget   INTEGER,
            tokens_spent    INTEGER DEFAULT 0,
            blocked_reason  TEXT,
            blocked_recovery_target TEXT,
            previous_status TEXT,
            status_entered_at TEXT,
            p0_count        INTEGER DEFAULT 0,
            p1_count        INTEGER DEFAULT 0,
            p2_count        INTEGER DEFAULT 0,
            revision_data   TEXT,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS task_comments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id         TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            author          TEXT NOT NULL,
            content         TEXT NOT NULL,
            iteration_number INTEGER DEFAULT 0,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS quality_scores (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id             TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            version             TEXT NOT NULL,
            compliance_score    REAL,
            ai_quality_score    REAL,
            defect_trend_score  REAL,
            total_score         REAL,
            score_breakdown     TEXT,
            created_at          TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS evolution_suggestions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source          TEXT NOT NULL,
            task_id         TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            round_number    INTEGER NOT NULL,
            tech_description    TEXT NOT NULL,
            recommendation      TEXT NOT NULL,
            plain_explanation   TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'pending',
            p_level         TEXT,
            scope           TEXT NOT NULL DEFAULT 'universal',
            hit_count       INTEGER DEFAULT 0,
            total_rounds    INTEGER DEFAULT 0,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project);
        CREATE INDEX IF NOT EXISTS idx_comments_task ON task_comments(task_id);
        CREATE INDEX IF NOT EXISTS idx_scores_task ON quality_scores(task_id);
        CREATE INDEX IF NOT EXISTS idx_evo_status ON evolution_suggestions(status);
    """)
    conn.commit()

def _migrate_schema(conn: sqlite3.Connection):
    """迁移旧 schema 到 v2.0"""
    # 检查旧状态是否存在
    old_statuses = conn.execute(
        "SELECT DISTINCT status FROM tasks WHERE status IN "
        "('needs_revision','p2_clearing','p2_cleared','approved','signed_off')"
    ).fetchall()
    if not old_statuses:
        # 再检查列是否存在
        cols = [r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()]
        if 'status_entered_at' in cols:
            return  # 已经是最新 schema
    # 执行迁移
    for stmt in MIGRATE_SQL.split(';'):
        s = stmt.strip()
        if s:
            try:
                conn.execute(s)
            except sqlite3.OperationalError:
                pass  # 列已存在
    for stmt in MIGRATE_STATUS_SQL.split(';'):
        s = stmt.strip()
        if s:
            conn.execute(s)
    conn.commit()

def _validate_transition(current_status: str, new_status: str, task_id: str = ''):
    """校验状态迁移合法性"""
    if new_status not in VALID_STATUSES:
        raise ValueError(f"无效状态: {new_status}")
    allowed = VALID_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise ValueError(
            f"非法状态迁移 [{task_id}]: {current_status} -> {new_status} "
            f"(允许: {sorted(allowed)})"
        )

# ---------- 公开 API ----------

def create_task(project: str, title: str, file_path: str = None,
                version: str = None, assigned_to: str = 'writer') -> str:
    """创建新任务，返回 task_id"""
    task_id = 't_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    conn = _conn(project)
    conn.execute(
        "INSERT INTO tasks (id, title, status, assigned_to, project, file_path, version) "
        "VALUES (?,?,?,?,?,?,?)",
        (task_id, title, 'backlog', assigned_to, project, file_path, version)
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
    """按状态获取任务列表。status=None 返回该项目全部任务"""
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

def update_task_status(project: str, task_id: str, new_status: str,
                       validate: bool = True, **extra):
    """更新任务状态 + 附加字段。validate=True 时校验迁移合法性。

    extra 支持字段: assigned_to, file_path, version, commit_sha,
                   iteration_count, tokens_budget, tokens_spent,
                   blocked_reason, blocked_recovery_target, previous_status,
                   p0_count, p1_count, p2_count, revision_data
    """
    if validate:
        task = get_task(project, task_id)
        if task:
            _validate_transition(task['status'], new_status, task_id)

    conn = _conn(project)
    # Status 变化时重置 status_entered_at
    fields = ["status=?", "status_entered_at=datetime('now')", "updated_at=datetime('now')"]
    values = [new_status]

    # blocked 时自动保存 previous_status
    if new_status == 'blocked' and 'previous_status' not in extra:
        task = get_task(project, task_id)
        if task:
            extra['previous_status'] = task['status']

    for k, v in extra.items():
        fields.append(f'{k}=?')
        values.append(v)

    conn.execute(
        f"UPDATE tasks SET {', '.join(fields)} WHERE id=?",
        values + [task_id]
    )
    conn.commit()
    conn.close()

def add_comment(project: str, task_id: str, author: str, content: str,
                iteration_number: int = 0):
    """添加评论"""
    conn = _conn(project)
    conn.execute(
        "INSERT INTO task_comments (task_id, author, content, iteration_number) "
        "VALUES (?,?,?,?)",
        (task_id, author, content, iteration_number)
    )
    conn.commit()
    conn.close()

def get_comments(project: str, task_id: str, author: str = None) -> list:
    """获取任务评论。author 可选过滤"""
    conn = _conn(project)
    if author:
        rows = conn.execute(
            "SELECT * FROM task_comments WHERE task_id=? AND author=? ORDER BY created_at ASC",
            (task_id, author)
        ).fetchall()
    else:
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
        "UPDATE tasks SET iteration_count = iteration_count + 1, "
        "updated_at = datetime('now') WHERE id=?",
        (task_id,)
    )
    conn.commit()
    conn.close()

def save_quality_score(project: str, task_id: str, version: str, scores: dict):
    """保存质量评分"""
    conn = _conn(project)
    conn.execute(
        "INSERT INTO quality_scores "
        "(task_id, version, compliance_score, ai_quality_score, "
        " defect_trend_score, total_score, score_breakdown) "
        "VALUES (?,?,?,?,?,?,?)",
        (task_id, version,
         scores.get('compliance'), scores.get('ai_quality'),
         scores.get('defect_trend'), scores.get('total'),
         json.dumps(scores.get('breakdown', {})))
    )
    conn.commit()
    conn.close()

def add_alert(project: str, message: str):
    """写 alert 文件到 .kanban/.alerts/"""
    alerts_dir = os.path.join(KANBAN_DIR, '.alerts')
    os.makedirs(alerts_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    alert_file = os.path.join(alerts_dir, f'{project}_{timestamp}.alert')
    with open(alert_file, 'w') as f:
        f.write(f'{datetime.now().isoformat()}\n{message}\n')

def recover_blocked_task(project: str, task_id: str, action: str):
    """恢复 blocked 任务。

    action: 'continue'|'reset_backlog'|'adjust_budget'|'git_restore'|'manual_review'
    """
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

    update_task_status(project, task_id, target, validate=False)
    add_comment(project, task_id, 'liufeng',
                f'手动恢复: blocked_reason={task["blocked_reason"]}, '
                f'action={action}, target={target}')

def save_evolution_suggestion(source: str, task_id: str, round_number: int,
                              tech: str, recommendation: str, plain: str,
                              p_level: str = None, scope: str = 'universal'):
    """保存进化建议"""
    conn = _conn(project=None)
    conn.execute(
        "INSERT INTO evolution_suggestions "
        "(source, task_id, round_number, tech_description, recommendation, "
        " plain_explanation, p_level, scope) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (source, task_id, round_number, tech, recommendation, plain, p_level, scope)
    )
    conn.commit()
    conn.close()

def get_evolution_suggestions(status: str = None) -> list:
    """获取进化建议"""
    conn = _conn(project=None)
    if status:
        rows = conn.execute(
            "SELECT * FROM evolution_suggestions WHERE status=? ORDER BY created_at DESC",
            (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM evolution_suggestions ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_document_content(task_id: str, project: str = 'yaya-zhujiao') -> dict:
    """获取任务对应文档的内容"""
    task = get_task(project, task_id)
    if not task:
        return {'error': '任务不存在', 'found': False}
    file_path = task.get('file_path', '')
    if not file_path or not os.path.exists(file_path):
        return {'error': '文件不存在', 'found': False, 'file_path': file_path}
    with open(file_path, 'r') as f:
        content = f.read()
    return {
        'found': True,
        'title': task['title'],
        'file_path': file_path,
        'content': content,
        'total_chars': len(content),
        'truncated': False,
    }


# ====== 自检 ======
if __name__ == '__main__':
    import sys
    test_project = '__test_kanban'
    print("=== kanban_ops v2.0 自检 ===")

    # 1. 创建任务
    tid = create_task(test_project, '测试任务', file_path='/tmp/test.md', version='v1.0')
    print(f"  创建任务: {tid}")

    # 2. 获取任务
    task = get_task(test_project, tid)
    assert task and task['status'] == 'backlog'
    print(f"  初始状态: {task['status']}")

    # 3. backlog -> drafting
    update_task_status(test_project, tid, 'drafting', assigned_to='writer')
    task = get_task(test_project, tid)
    assert task['status'] == 'drafting'
    print(f"  drafting: {task['status']}")

    # 4. 非法迁移拦截
    try:
        update_task_status(test_project, tid, 'finalized')
        print("  FAIL: 应该拦截 drafting -> finalized")
        sys.exit(1)
    except ValueError as e:
        print(f"  拦截非法 ✓ ({e.args[0][:50]}...)")

    # 5. drafting -> awaiting_review
    update_task_status(test_project, tid, 'awaiting_review')
    task = get_task(test_project, tid)
    assert task['status'] == 'awaiting_review'

    # 6. awaiting_review -> reviewing (reviewer claim)
    update_task_status(test_project, tid, 'reviewing')
    task = get_task(test_project, tid)
    assert task['status'] == 'reviewing'

    # 7. reviewing -> revision (P0/P1 > 0)
    increment_iteration(test_project, tid)
    update_task_status(test_project, tid, 'revision',
                       p0_count=2, p1_count=3, p2_count=5)
    task = get_task(test_project, tid)
    assert task['status'] == 'revision'
    assert task['iteration_count'] == 1
    assert task['p0_count'] == 2
    print(f"  revision: {task['status']} (P0={task['p0_count']} P1={task['p1_count']})")

    # 8. revision -> re_review (writer submits fix)
    update_task_status(test_project, tid, 're_review',
                       p0_count=0, p1_count=0, p2_count=0)
    task = get_task(test_project, tid)
    assert task['status'] == 're_review'
    print(f"  re_review: {task['status']}")

    # 9. re_review -> waiting_human_review (re-review pass)
    update_task_status(test_project, tid, 'waiting_human_review')
    task = get_task(test_project, tid)
    assert task['status'] == 'waiting_human_review'
    print(f"  re_review pass -> waiting_human_review: {task['status']} ✓")

    # 10. human rejects -> revision
    update_task_status(test_project, tid, 'revision',
                       revision_data=json.dumps({'human_feedback': ['第3节描述不清晰']}))
    task = get_task(test_project, tid)
    assert task['status'] == 'revision'
    rev_data = json.loads(task['revision_data'] or '{}')
    assert 'human_feedback' in rev_data
    print(f"  人工打回 -> revision ✓")

    # 11. revision -> re_review (fix and submit)
    update_task_status(test_project, tid, 're_review')
    task = get_task(test_project, tid)
    assert task['status'] == 're_review'
    print(f"  fix submit -> re_review ✓")

    # 12. re_review -> revision (re-review fail)
    update_task_status(test_project, tid, 'revision',
                       p0_count=2, p1_count=1, p2_count=3,
                       revision_data=json.dumps({'re_review_result': 'fail'}))
    task = get_task(test_project, tid)
    assert task['status'] == 'revision'
    print(f"  re_review fail -> revision ✓")

    # 13. revision -> re_review -> waiting_human_review -> finalized
    update_task_status(test_project, tid, 're_review')
    update_task_status(test_project, tid, 'waiting_human_review')
    update_task_status(test_project, tid, 'finalized')
    task = get_task(test_project, tid)
    assert task['status'] == 'finalized'
    print(f"  finalized: {task['status']} ✓")

    # 12. finalized -> blocked
    update_task_status(test_project, tid, 'blocked',
                       blocked_reason='post_finalize_issue',
                       blocked_recovery_target='revision')
    task = get_task(test_project, tid)
    assert task['status'] == 'blocked'
    assert task['blocked_reason'] == 'post_finalize_issue'
    assert task['previous_status'] == 'finalized'
    print(f"  blocked: {task['status']} (from {task['previous_status']})")

    # 13. blocked 恢复
    recover_blocked_task(test_project, tid, 'continue')
    task = get_task(test_project, tid)
    assert task['status'] == 'revision'
    print(f"  blocked → revision ✓")

    # 14. status_entered_at 检查
    assert task.get('status_entered_at') is not None
    print(f"  status_entered_at: {task['status_entered_at']}")

    # 注释
    add_comment(test_project, tid, 'writer', '修改完成')
    add_comment(test_project, tid, 'reviewer', '审核通过')
    comments = get_comments(test_project, tid)
    assert len(comments) == 3  # recover_blocked_task 加了一条，writer/reviewer 各加一条
    print(f"  评论数: {len(comments)}")

    # 按作者过滤
    writer_comments = get_comments(test_project, tid, author='writer')
    assert len(writer_comments) == 1
    print(f"  writer 评论过滤 ✓")

    # 清理测试数据库
    db_path = _db_path(test_project)
    if os.path.exists(db_path):
        os.remove(db_path)
    print("\n=== 全部测试通过 ✓ ===")
