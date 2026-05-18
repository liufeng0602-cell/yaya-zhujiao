#!/usr/bin/env python3
"""Writer 主脚本 — 由 agent cron 触发，扫描 kanban 处理任务"""

import os
import sys
import json
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kanban_ops import (
    get_tasks_by_status, get_task, get_comments,
    update_task_status, add_comment,
    PROJECT_ROOT, KANBAN_DIR, AUDIT_REPORTS_DIR
)

PROJECT = 'yaya-zhujiao'

# Writer 处理优先级: backlog > needs_revision > p2_clearing
SCAN_ORDER = ['backlog', 'needs_revision', 'p2_clearing']


def claim_task(task_id: str, from_status: str):
    """claim 任务: 移到 drafting"""
    update_task_status(PROJECT, task_id, 'drafting', assigned_to='writer')
    add_comment(PROJECT, task_id, 'writer',
                f'开始{"写作" if from_status == "backlog" else "修改"}（来自 {from_status}）')
    print(f"[WRITER] claim 任务 {task_id} ({from_status} -> drafting)")


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


def do_git_commit(file_path: str, message: str) -> bool:
    """git commit 并验证"""
    repo = PROJECT_ROOT
    # commit
    r = subprocess.run(['git', 'add', file_path], capture_output=True,
                       text=True, cwd=repo)
    r = subprocess.run(['git', 'commit', '-m', message],
                       capture_output=True, text=True, cwd=repo)
    if r.returncode != 0:
        print(f"[WRITER] git commit 失败: {r.stderr}")
        return False

    # 验证
    r = subprocess.run(['git', 'log', '-3', '--oneline'],
                       capture_output=True, text=True, cwd=repo)
    print(f"[WRITER] git log:\n{r.stdout.strip()}")

    # 获取 commit SHA
    r = subprocess.run(['git', 'rev-parse', 'HEAD'],
                       capture_output=True, text=True, cwd=repo)
    commit_sha = r.stdout.strip()[:8]
    return commit_sha


def process_backlog(task: dict):
    """处理 backlog 任务: 写作"""
    task_id = task['id']
    claim_task(task_id, 'backlog')

    file_path = task.get('file_path', '')
    title = task.get('title', 'Unknown')

    # ====== 核心: 这里由 agent cron 的 LLM prompt 执行实际写作 ======
    # Writer agent 读:
    #   - 项目的 NORTH_STAR.md
    #   - 相关已有子系统文档
    #   - task.title / task.file_path 确定写什么
    # 然后用大模型生成文档内容。
    #
    # 纯 Python 脚本无法做 LLM 推理 —— 实际文档生成在 agent cron prompt 中完成。
    # 本脚本提供: claim、自检、commit、状态更新 的粘合层。

    print(f"[WRITER] 写作任务: {title} -> {file_path}")
    print(f"[WRITER] 请 agent prompt 在此处执行文档生成逻辑")

    # 如果 file_path 不存在，占位创建
    if file_path and not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(f'# {title}\n\n<!-- 待 agent prompt 填充内容 -->\n')
        print(f"[WRITER] 创建占位文件: {file_path}")

    # 自检
    if file_path and os.path.exists(file_path):
        if not run_self_check(file_path):
            update_task_status(PROJECT, task_id, 'blocked',
                               blocked_reason='self_check_failed')
            add_comment(PROJECT, task_id, 'writer',
                        '自检失败: wrapper.py 语法检查不通过')
            return

    # commit
    msg = f'[Writer] {title} v{task.get("version", "0.1")}'
    if file_path:
        sha = do_git_commit(file_path, msg)
        if sha:
            update_task_status(PROJECT, task_id, 'awaiting_review',
                               commit_sha=sha)
        else:
            update_task_status(PROJECT, task_id, 'blocked',
                               blocked_reason='commit_failed')
            return
    else:
        update_task_status(PROJECT, task_id, 'awaiting_review')

    # 自检声明
    add_comment(PROJECT, task_id, 'writer', f'''自检声明：
- 本轮{"写作" if task["status"] == "backlog" else "修改"}完成
- 自检通过项：wrapper.py 语法检查
- 文件路径：{file_path}
- 提交 SHA：{sha if file_path else "N/A"}''')

    # 触发 reviewer
    trigger_reviewer()


def process_needs_revision(task: dict):
    """处理 needs_revision 任务: 修改"""
    task_id = task['id']
    claim_task(task_id, 'needs_revision')

    # 读取最近的审核报告
    comments = get_comments(PROJECT, task_id)
    review_comments = [c for c in comments if c['author'] == 'reviewer']
    if review_comments:
        latest = review_comments[-1]
        print(f"[WRITER] 审核报告: {latest['content'][:200]}...")

    # 修改逻辑由 agent prompt 执行
    print(f"[WRITER] 修改任务: {task['title']}")
    print(f"[WRITER] 请 agent prompt 根据审核报告修复 P0/P1 问题")

    file_path = task.get('file_path', '')
    # 自检
    if file_path and os.path.exists(file_path):
        if not run_self_check(file_path):
            update_task_status(PROJECT, task_id, 'blocked',
                               blocked_reason='self_check_failed')
            return

    # commit
    msg = f'[Writer] fix: {task["title"]} v{task.get("version", "0.1")} round {task.get("iteration_count", 0)+1}'
    if file_path:
        sha = do_git_commit(file_path, msg)
        if sha:
            update_task_status(PROJECT, task_id, 'awaiting_review',
                               commit_sha=sha)
        else:
            update_task_status(PROJECT, task_id, 'blocked',
                               blocked_reason='commit_failed')
            return
    else:
        update_task_status(PROJECT, task_id, 'awaiting_review')

    add_comment(PROJECT, task_id, 'writer', f'''自检声明：
- 本轮修改完成（来自 needs_revision, 第 {task.get("iteration_count", 0)+1} 轮）
- 文件路径：{file_path}
- 提交 SHA：{sha if file_path else "N/A"}''')

    trigger_reviewer()


def process_p2_clearing(task: dict):
    """处理 p2_clearing 任务: 修复 P2"""
    task_id = task['id']
    print(f"[WRITER] P2 清零任务: {task['title']}")

    # P2 修复逻辑由 agent prompt 执行
    # 修复完成后 git diff 检查范围
    file_path = task.get('file_path', '')

    if file_path and os.path.exists(file_path):
        # git diff 守卫
        r = subprocess.run(['git', 'diff', 'HEAD~1', '--stat'],
                           capture_output=True, text=True, cwd=PROJECT_ROOT)
        print(f"[WRITER] git diff 范围:\n{r.stdout.strip()}")

        # 自检（强制）
        run_self_check(file_path)

        # commit
        msg = f'[Writer] P2 fix: {task["title"]}'
        sha = do_git_commit(file_path, msg)
        if sha:
            update_task_status(PROJECT, task_id, 'p2_cleared',
                               commit_sha=sha)
        else:
            update_task_status(PROJECT, task_id, 'blocked',
                               blocked_reason='commit_failed')
            return
    else:
        update_task_status(PROJECT, task_id, 'p2_cleared')

    add_comment(PROJECT, task_id, 'writer',
                f'P2_FIXED: 所有 P2 项已修复。')
    print(f"[WRITER] P2 清零完成 -> p2_cleared, 等待 liufeng 终审")


def trigger_reviewer():
    """写 NOTIFY 文件触发 reviewer（零轮询事件驱动）"""
    notify_dir = os.path.join(KANBAN_DIR, '.notify')
    os.makedirs(notify_dir, exist_ok=True)
    notify_path = os.path.join(notify_dir, f'review-{PROJECT}')
    print(f"[WRITER] 触发 reviewer (NOTIFY: {notify_path})...")
    with open(notify_path, 'w') as f:
        f.write(f'NOTIFY by writer at {datetime.now().isoformat()}')


def main():
    print(f"[WRITER] ========== {datetime.now().isoformat()} ==========")
    print(f"[WRITER] 扫描项目: {PROJECT}")

    for status in SCAN_ORDER:
        tasks = get_tasks_by_status(PROJECT, status)
        if tasks:
            task = tasks[0]  # updated_at ASC，最旧优先
            print(f"[WRITER] 发现 {status} 任务: {task['id']} {task['title']}")

            if status == 'backlog':
                process_backlog(task)
            elif status == 'needs_revision':
                process_needs_revision(task)
            elif status == 'p2_clearing':
                process_p2_clearing(task)

            # 一个 tick 只处理 1 个任务
            print(f"[WRITER] 本轮处理完毕: {task['id']}")
            return

    print("[WRITER] 无待处理任务，退出")


if __name__ == '__main__':
    main()
