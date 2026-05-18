#!/usr/bin/env python3
"""Kanban 核心操作库 — SQLite 数据层 + 状态机校验"""

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
    'backlog', 'drafting', 'awaiting_review', 'needs_revision',
    'approved', 'p2_clearing', 'p2_cleared', 'signed_off', 'blocked'
])

# ---------- 状态迁移白名单 ----------
VALID_TRANSITIONS = {
    'backlog':          {'drafting'},
    'drafting':         {'awaiting_review', 'blocked'},
    'awaiting_review':  {'needs_revision', 'approved', 'p2_clearing', 'blocked'},
    'needs_revision':   {'drafting', 'blocked'},
    'approved':         {'p2_clearing', 'signed_off', 'blocked'},
    'p2_clearing':      {'needs_revision', 'p2_cleared', 'blocked'},
    'p2_cleared':       {'signed_off', 'blocked'},
    'signed_off':       {'blocked'},             # 封版后只进 blocked
    'blocked':          {'backlog', 'drafting', 'awaiting_review', 'needs_revision', 'approved', 'p2_cleared', 'signed_off'},
}

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
                   blocked_reason, blocked_recovery_target, previous_status
    """
    if validate:
        task = get_task(project, task_id)
        if task:
            _validate_transition(task['status'], new_status, task_id)

    conn = _conn(project)
    fields = ["status=?", "updated_at=datetime('now')"]
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


def get_comments(project: str, task_id: str) -> list:
    """获取任务所有评论"""
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


# ====== 自检 ======
if __name__ == '__main__':
    import sys
    test_project = '__test_kanban'
    print("=== kanban_ops 自检 ===")

    # 1. 创建任务
    tid = create_task(test_project, '测试任务', file_path='/tmp/test.md', version='v1.0')
    print(f"  创建任务: {tid}")

    # 2. 获取任务
    task = get_task(test_project, tid)
    assert task and task['status'] == 'backlog', "状态应为 backlog"
    print(f"  任务状态: {task['status']}")

    # 3. 状态迁移: backlog -> drafting
    update_task_status(test_project, tid, 'drafting', assigned_to='writer')
    task = get_task(test_project, tid)
    assert task['status'] == 'drafting'
    print(f"  迁移到: {task['status']}")

    # 4. 非法迁移拦截
    try:
        update_task_status(test_project, tid, 'signed_off')
        print("  FAIL: 应该拦截 drafting -> signed_off")
        sys.exit(1)
    except ValueError as e:
        print(f"  拦截非法迁移: drafting -> signed_off ✓")

    # 5. 合法迁移: drafting -> awaiting_review
    update_task_status(test_project, tid, 'awaiting_review')
    task = get_task(test_project, tid)
    assert task['status'] == 'awaiting_review'

    # 6. await_review -> needs_revision
    increment_iteration(test_project, tid)
    update_task_status(test_project, tid, 'needs_revision')
    task = get_task(test_project, tid)
    assert task['status'] == 'needs_revision'
    assert task['iteration_count'] == 1

    # 7. needs_revision -> drafting -> awaiting_review -> approved
    update_task_status(test_project, tid, 'drafting')
    update_task_status(test_project, tid, 'awaiting_review')
    update_task_status(test_project, tid, 'approved')
    task = get_task(test_project, tid)
    assert task['status'] == 'approved'

    # 8. approved -> p2_clearing
    update_task_status(test_project, tid, 'p2_clearing')
    task = get_task(test_project, tid)
    assert task['status'] == 'p2_clearing'

    # 9. p2_clearing -> p2_cleared
    add_comment(test_project, tid, 'writer', 'P2_FIXED: 所有 P2 已修复')
    update_task_status(test_project, tid, 'p2_cleared')
    task = get_task(test_project, tid)
    assert task['status'] == 'p2_cleared'

    # 10. p2_cleared -> signed_off
    update_task_status(test_project, tid, 'signed_off')
    task = get_task(test_project, tid)
    assert task['status'] == 'signed_off'

    # 11. signed_off -> blocked
    update_task_status(test_project, tid, 'blocked',
                       blocked_reason='quality_deviation',
                       blocked_recovery_target='backlog')
    task = get_task(test_project, tid)
    assert task['status'] == 'blocked'
    assert task['blocked_reason'] == 'quality_deviation'
    assert task['previous_status'] == 'signed_off'

    # 12. blocked 恢复
    recover_blocked_task(test_project, tid, 'reset_backlog')
    task = get_task(test_project, tid)
    assert task['status'] == 'backlog'

    # 13. 评论
    comments = get_comments(test_project, tid)
    assert len(comments) >= 1

    # 14. get_tasks_by_status
    tasks = get_tasks_by_status(test_project, 'backlog')
    assert any(t['id'] == tid for t in tasks)
    empty = get_tasks_by_status(test_project, 'drafting')
    assert not any(t['id'] == tid for t in empty)

    # 15. alert
    add_alert(test_project, '测试报警')
    alerts_dir = os.path.join(KANBAN_DIR, '.alerts')
    alert_files = [f for f in os.listdir(alerts_dir) if f.startswith(test_project)]
    assert len(alert_files) >= 1

    # 清理测试数据库
    db_path = _db_path(test_project)
    if os.path.exists(db_path):
        os.remove(db_path)
    print("\n=== 全部 15 项测试通过 ✓ ===")
