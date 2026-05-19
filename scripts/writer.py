#!/usr/bin/env python3
"""Writer 主脚本 — 由 fswatch 触发，扫描 kanban 处理任务 (v3.0 并发版)"""

import os
import sys
import json
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kanban_ops import (
    get_tasks_by_status, get_task, get_comments,
    update_task_status, add_comment, try_claim_task,
    PROJECT_ROOT, KANBAN_DIR, AUDIT_REPORTS_DIR
)

PROJECT = 'yaya-zhujiao'

# ===== 并发控制 =====
# 目标=3，架构最高=5，扩量只改此常量
MAX_CONCURRENCY = 3

# Writer 处理优先级: backlog > revision > re_review
# revision 包含旧 needs_revision（P0/P1 修复）和旧 p2_clearing（P2 清零）
# re_review 是复审不通过的任务（等待进入修改区）
SCAN_ORDER = ['backlog', 'revision', 're_review', 'drafting']


def run_self_check(file_path: str) -> bool:
    """自检: 运行 wrapper.py 语法检查"""
    wrapper = os.path.join(PROJECT_ROOT, 'reusable-review-rules', 'wrapper.py')
    if not os.path.exists(wrapper):
        print("[WRITER] wrapper.py 不存在，跳过语法检查")
        return True

    result = subprocess.run(
        ['python3', wrapper, file_path],
        capture_output=True, text=True, timeout=120,
        cwd=PROJECT_ROOT
    )
    if result.returncode != 0:
        print(f"[WRITER] wrapper.py 语法检查失败:\n{result.stderr}")
        return False
    print(f"[WRITER] wrapper.py 语法检查通过: {file_path}")
    return True


def do_git_commit(file_path: str, message: str) -> bool | str:
    """git commit 并验证 — 按文件隔离（git commit -- <file> 防并行交叉）

    返回 False 表示真正失败（非 no-change），返回 SHA 表示成功，
    返回 True 表示文件无变动无需新提交。
    """
    repo = PROJECT_ROOT

    # 先检查是否有未提交变更
    r = subprocess.run(
        ['git', 'diff', '--cached', '--stat', '--', file_path],
        capture_output=True, text=True, cwd=repo,
    )
    has_staged = bool(r.stdout.strip())

    r = subprocess.run(
        ['git', 'diff', '--stat', '--', file_path],
        capture_output=True, text=True, cwd=repo,
    )
    has_unstaged = bool(r.stdout.strip())

    if not has_staged and not has_unstaged:
        print(f"[WRITER] {file_path} 无变更，跳过 git commit")
        r = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True, text=True, cwd=repo,
        )
        return r.stdout.strip()[:8] or True

    # 有变更 → add + commit（-- <file> 确保只提交当前文件，防并行交叉）
    r = subprocess.run(['git', 'add', file_path], capture_output=True,
                       text=True, cwd=repo)
    r = subprocess.run(['git', 'commit', '-m', message, '--', file_path],
                       capture_output=True, text=True, cwd=repo)
    if r.returncode != 0:
        print(f"[WRITER] git commit 失败: {r.stderr}")
        return False

    # 获取 commit SHA
    r = subprocess.run(['git', 'rev-parse', 'HEAD'],
                       capture_output=True, text=True, cwd=repo)
    commit_sha = r.stdout.strip()[:8]
    return commit_sha


def process_backlog(task: dict):
    """处理 backlog 任务: 写作（已 claim 成功，不重复 claim）"""
    task_id = task['id']
    file_path = task.get('file_path', '')
    title = task.get('title', 'Unknown')

    print(f"[WRITER] 写作任务: {title} -> {file_path}")
    print(f"[WRITER] 请 agent 在此处执行文档生成逻辑")

    # 如果 file_path 不存在，占位创建
    if file_path and not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(f'# {title}\n\n<!-- 待 agent 填充内容 -->\n')
        print(f"[WRITER] 创建占位文件: {file_path}")

    # 自检
    if file_path and os.path.exists(file_path):
        if not run_self_check(file_path):
            attempts = increment_auto_repair(PROJECT, task_id, 'self_check_failed')
            handle_auto_repair_result(
                PROJECT, task_id, attempts, max_attempts=3,
                target_on_exhaust='awaiting_review',
                task_title=title, task_version=task.get('version', ''))
            return

    # commit
    msg = f'[Writer] {title} v{task.get("version", "0.1")}'
    if file_path:
        sha = do_git_commit(file_path, msg)
        if sha:
            update_task_status(PROJECT, task_id, 'awaiting_review',
                               commit_sha=sha)
        else:
            attempts = increment_auto_repair(PROJECT, task_id, 'commit_failed')
            handle_auto_repair_result(
                PROJECT, task_id, attempts, max_attempts=3,
                target_on_exhaust='awaiting_review',
                task_title=title, task_version=task.get('version', ''))
            return
    else:
        update_task_status(PROJECT, task_id, 'awaiting_review')

    # 自检声明
    add_comment(PROJECT, task_id, 'writer', f'''自检声明：
- 本轮写作完成
- 自检通过项：wrapper.py 语法检查
- 文件路径：{file_path}
- 提交 SHA：{sha if file_path else "N/A"}''')

    # 触发 reviewer（按 task 独立 NOTIFY）
    trigger_reviewer(task_id)


def process_revision(task: dict):
    """处理 revision/re_review 任务: 修复 P0/P1/P2（已 claim 成功，不重复 claim）"""
    task_id = task['id']

    # 读取最近的审核报告和人工反馈
    comments = get_comments(PROJECT, task_id)
    review_comments = [c for c in comments if c['author'] == 'reviewer']
    human_feedback = [c for c in comments if c['author'] == 'liufeng']
    if review_comments:
        latest = review_comments[-1]
        print(f"[WRITER] 上次审核: {latest['content'][:200]}...")
    if human_feedback:
        latest_h = human_feedback[-1]
        print(f"[WRITER] 人工反馈: {latest_h['content'][:200]}...")

    # 读取 revision_data（含 P 级分布和修理状态）
    revision_data = json.loads(task.get('revision_data') or '{}')
    print(f"[WRITER] 修改任务: {task['title']}")
    print(f"[WRITER] revision_data: {revision_data}")

    file_path = task.get('file_path', '')
    # 自检
    if file_path and os.path.exists(file_path):
        if not run_self_check(file_path):
            attempts = increment_auto_repair(PROJECT, task_id, 'self_check_failed')
            handle_auto_repair_result(
                PROJECT, task_id, attempts, max_attempts=3,
                target_on_exhaust='revision',
                task_title=task['title'], task_version=task.get('version', ''))
            return

    # commit
    msg = f'[Writer] fix: {task["title"]} v{task.get("version", "0.1")} round {task.get("iteration_count", 0)+1}'
    if file_path:
        sha = do_git_commit(file_path, msg)
        if sha:
            update_task_status(PROJECT, task_id, 're_review',
                               commit_sha=sha)
        else:
            attempts = increment_auto_repair(PROJECT, task_id, 'commit_failed')
            handle_auto_repair_result(
                PROJECT, task_id, attempts, max_attempts=3,
                target_on_exhaust='revision',
                task_title=task['title'], task_version=task.get('version', ''))
            return
    else:
        update_task_status(PROJECT, task_id, 're_review')

    add_comment(PROJECT, task_id, 'writer', f'''自检声明：
- 本轮修改完成（来自 revision, 第 {task.get("iteration_count", 0)+1} 轮，送复审）
- 文件路径：{file_path}
- 提交 SHA：{sha if file_path else "N/A"}''')

    # 触发 reviewer（按 task 独立 NOTIFY）
    trigger_reviewer(task_id)


def get_auto_repair_attempts(task: dict) -> int:
    """从 revision_data 读取 auto_repair_attempts"""
    try:
        rev_data = json.loads(task.get('revision_data') or '{}')
        return rev_data.get('auto_repair_attempts', 0)
    except (json.JSONDecodeError, TypeError):
        return 0

def increment_auto_repair(project: str, task_id: str, failure_reason: str) -> int:
    """auto_repair_attempts +1，返回新的尝试次数"""
    task = get_task(project, task_id)
    if not task:
        return 0
    rev_data = {}
    try:
        rev_data = json.loads(task.get('revision_data') or '{}')
    except (json.JSONDecodeError, TypeError):
        rev_data = {}
    attempts = rev_data.get('auto_repair_attempts', 0) + 1
    rev_data['auto_repair_attempts'] = attempts
    rev_data['last_auto_repair_failure'] = failure_reason
    rev_data['last_auto_repair_time'] = datetime.now().isoformat()
    update_task_status(project, task_id, task['status'],
                       revision_data=json.dumps(rev_data),
                       validate=False)
    add_comment(project, task_id, 'writer',
                f'自动修复 #{attempts} 失败: {failure_reason}')
    return attempts


def handle_auto_repair_result(project: str, task_id: str, attempts: int,
                               max_attempts: int = 3,
                               target_on_exhaust: str = 'awaiting_review',
                               task_title: str = '', task_version: str = ''):
    """根据重试次数决定下一步"""
    notify_dir = os.path.join(KANBAN_DIR, '.notify')
    os.makedirs(notify_dir, exist_ok=True)

    if attempts < max_attempts:
        # 继续重试 — 写 writer NOTIFY（带 task_id）
        notify_path = os.path.join(notify_dir, f'writer-{PROJECT}-{task_id}')
        with open(notify_path, 'w') as f:
            f.write(f'auto-repair retry #{attempts} at {datetime.now().isoformat()}')
        add_comment(project, task_id, 'writer',
                    f'自动修复 {attempts}/{max_attempts} 次失败，即将重试第 {attempts+1} 次')
        print(f'[WRITER] auto-repair #{attempts} failed, retrying...')
    else:
        should_retry_writer = target_on_exhaust in ('revision', 're_review')
        update_task_status(project, task_id, target_on_exhaust,
                           commit_sha=None, validate=False)
        if should_retry_writer:
            add_comment(project, task_id, 'writer',
                        f'自动修复已达 {max_attempts} 次上限，继续重试'
                        f'（目标：{target_on_exhaust}）')
            notify_path = os.path.join(notify_dir, f'writer-{PROJECT}-{task_id}')
        else:
            add_comment(project, task_id, 'writer',
                        f'自动修复已达 {max_attempts} 次上限，已送审，'
                        f'由 Reviewer 检查问题')
            notify_path = os.path.join(notify_dir, f'review-{PROJECT}-{task_id}')
        with open(notify_path, 'w') as f:
            f.write(f'auto-repair exhausted at {datetime.now().isoformat()}'
                    f' target={target_on_exhaust}')
        print(f'[WRITER] auto-repair exhausted ({max_attempts}/{max_attempts}), '
              f'pushed to {target_on_exhaust}, '
              f'notify={"writer" if should_retry_writer else "reviewer"}')


def trigger_reviewer(task_id: str = ''):
    """写 NOTIFY 文件触发 reviewer（带 task_id，支持并行独立触发）"""
    notify_dir = os.path.join(KANBAN_DIR, '.notify')
    os.makedirs(notify_dir, exist_ok=True)
    suffix = f'-{task_id}' if task_id else ''
    notify_path = os.path.join(notify_dir, f'review-{PROJECT}{suffix}')
    print(f"[WRITER] 触发 reviewer (NOTIFY: {notify_path})...")
    with open(notify_path, 'w') as f:
        f.write(f'NOTIFY by writer at {datetime.now().isoformat()}')


def main():
    print(f"[WRITER] ========== {datetime.now().isoformat()} ==========")
    print(f"[WRITER] 扫描项目: {PROJECT}, 最大并行: {MAX_CONCURRENCY}")

    processed = 0
    for status in SCAN_ORDER:
        if processed >= MAX_CONCURRENCY:
            break

        tasks = get_tasks_by_status(PROJECT, status)
        if not tasks:
            continue

        for task in tasks:
            if processed >= MAX_CONCURRENCY:
                break

            task_id = task['id']
            current_status = task.get('status', '')

            # drafting 任务：仅处理有 auto_repair 记录的（无记录说明是正常工作中，跳过）
            if status == 'drafting':
                attempts = get_auto_repair_attempts(task)
                if attempts == 0:
                    print(f"[WRITER] drafting 任务 {task_id} {task.get('title','')} 无 auto_repair 记录，跳过")
                    continue

            # 原子 claim：仅当任务仍处于当前状态时才 claim，防止并行冲突
            if current_status != 'drafting':
                if not try_claim_task(PROJECT, task_id, current_status):
                    print(f"[WRITER] claim 失败（已被其他进程抢占）: {task_id} {task.get('title','')}")
                    continue

            # claim 成功后 task 状态已变为 drafting，重新读取获取最新数据
            task = get_task(PROJECT, task_id)
            if not task:
                print(f"[WRITER] 任务不存在: {task_id}")
                continue

            print(f"[WRITER] claim 成功: {task_id} ({current_status} -> drafting)")

            if status == 'backlog':
                process_backlog(task)
            elif status in ('revision', 're_review'):
                process_revision(task)
            elif status == 'drafting':
                process_revision(task)  # auto-repair 重试也走 process_revision
            else:
                print(f"[WRITER] 跳过未知状态: {status}")
                continue

            processed += 1
            print(f"[WRITER] 任务完成: {task_id} ({processed}/{MAX_CONCURRENCY})")

    if processed == 0:
        print("[WRITER] 无待处理任务，退出")
    else:
        print(f"[WRITER] 本轮共处理 {processed} 个任务，退出")


if __name__ == '__main__':
    main()
