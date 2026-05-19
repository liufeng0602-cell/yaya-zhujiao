#!/usr/bin/env python3
"""Writer 主脚本 — 由 fswatch 触发，扫描 kanban 处理任务 (v3.1 自检门禁版)"""

import os
import sys
import json
import subprocess
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kanban_ops import (
    get_tasks_by_status, get_task, get_comments,
    update_task_status, add_comment, try_claim_task,
    PROJECT_ROOT, KANBAN_DIR, AUDIT_REPORTS_DIR
)
from reusable_review_rules.hardcoded_tracker import scan as tracker_scan
from reusable_review_rules.self_check_validator import SelfCheckReportValidator

PROJECT = 'yaya-zhujiao'

# ===== 并发控制 =====
# 目标=3，架构最高=5，扩量只改此常量
MAX_CONCURRENCY = 2

# Writer 处理优先级: backlog > revision > re_review
# revision 包含旧 needs_revision（P0/P1 修复）和旧 p2_clearing（P2 清零）
# re_review 是复审不通过的任务（等待进入修改区）
SCAN_ORDER = ['backlog', 'revision', 're_review', 'drafting']

# ── 自检门禁 ────────────────────────────────────────────────────────

_REPORT_CLOSE_RE = re.compile(r'</self_check_report>\s*$', re.MULTILINE)


def _auto_repair_self_check(doc_text: str, issues: list) -> str | None:
    """尝试自动修复 P1 类格式问题（缺键、类型错误）。返回修复后的文档，失败返回 None。"""
    repaired = doc_text

    # 提取 YAML 块区域
    start_m = re.search(r'<self_check_report>', repaired)
    end_m = re.search(r'</self_check_report>', repaired)
    if not start_m or not end_m:
        return None  # 无块，无法修复

    block_start = start_m.end()
    block_end = end_m.start()
    yaml_block = repaired[block_start:block_end].strip()

    # --- 修复类型错误 ---
    # version: int -> version: 'int'
    ver_fix = re.search(r'^version\s*:\s*(\d+)\s*$', yaml_block, re.MULTILINE)
    if ver_fix:
        old = ver_fix.group(0)
        new = f"version: '{ver_fix.group(1)}'"
        repaired = repaired.replace(old, new, 1)
        # 重新定位块
        start_m = re.search(r'<self_check_report>', repaired)
        end_m = re.search(r'</self_check_report>', repaired)
        block_start = start_m.end()
        block_end = end_m.start()
        yaml_block = repaired[block_start:block_end].strip()

    # checks 条目中 result 不是 bool -> 尝试转
    # "result: yes" -> "result: true"
    for iss in issues:
        msg = iss.get('msg', '')
        if 'result' in msg and 'bool' in msg:
            # 找到具体 check 名和 result 行
            # msg 格式: "check 'value_audit'.result must be bool, got str"
            m = re.match(r"check '(\w[\w_]*)'\.result must be bool", msg)
            if m:
                check_name = m.group(1)
                # 在 yaml 块中找该 check 下的 result 行
                # 格式:  check_name:\n    result: <value>
                pat = re.compile(
                    rf'({re.escape(check_name)}:\s*\n(?:[ \t]+\w[\w_]*:[^\n]*\n)*?[ \t]+result\s*:\s*)(\S+)',
                    re.MULTILINE
                )
                def _bool_fix(m2):
                    prefix = m2.group(1)
                    val = m2.group(2).strip().lower()
                    if val in ('true', 'false'):
                        return prefix + val  # 保持原值
                    elif val in ('yes', 'y', '1', '"yes"', "'yes'"):
                        return prefix + 'true'
                    elif val in ('no', 'n', '0', '"no"', "'no'"):
                        return prefix + 'false'
                    else:
                        return prefix + 'true'  # 兜底
                repaired = pat.sub(_bool_fix, repaired)

    # --- 修复缺失的必需键 ---
    insertions = []
    for iss in issues:
        msg = iss.get('msg', '')
        m = re.match(r"Missing required key '(\w+)'", msg)
        if m:
            key = m.group(1)
            defaults = {
                'version': "version: '1.0'",
                'checks': 'checks: {}',
                'reported_params': 'reported_params: []',
                'reported_configs': 'reported_configs: []',
            }
            if key in defaults:
                insertions.append(defaults[key])

    if insertions:
        # 在 </self_check_report> 前插入缺失的键
        close_tag = '</self_check_report>'
        idx = repaired.rfind(close_tag)
        if idx != -1:
            insert_text = '\n' + '\n'.join(insertions) + '\n'
            repaired = repaired[:idx] + insert_text + repaired[idx:]

    return repaired if repaired != doc_text else doc_text


def self_check_commit_gate(file_path: str, task_id: str, task_title: str) -> bool:
    """
    在 git commit 前强制执行 SelfCheckReportValidator 门禁。

    Returns:
        True  — 门禁通过，可以 commit
        False — 门禁未通过，Writer 已回退到 drafting 等待人工处理

    行为:
        - P0（缺自检报告块）→ 直接阻断，回退到 drafting
        - P1（格式/类型错误）→ 自动修复，修复后再验证
            - 修复成功 → 通过（P2 警告仅日志）
            - 修复失败 → 回退到 drafting
        - P2 仅警告 → 通过
    """
    try:
        with open(file_path, 'r') as f:
            doc_text = f.read()
    except FileNotFoundError:
        print(f"[WRITER-GATE] 文件不存在: {file_path}，跳过门禁")
        return True
    except Exception as e:
        print(f"[WRITER-GATE] 读取文件失败: {e}，跳过门禁")
        return True

    # 运行 tracker scan + validator
    tracker_out = tracker_scan(doc_text)
    report, issues = SelfCheckReportValidator.validate(doc_text, tracker_out)

    if not issues:
        print(f"[WRITER-GATE] 自检报告验证通过 (0 问题)")
        return True

    p0 = [i for i in issues if i['severity'] == 'P0']
    p1 = [i for i in issues if i['severity'] == 'P1']
    p2 = [i for i in issues if i['severity'] == 'P2']

    # 打印所有问题
    for iss in issues:
        print(f"[WRITER-GATE]  {iss['severity']}: {iss['msg']}")

    # ---- P0: 阻断 ----
    if p0:
        print(f"[WRITER-GATE] P0 问题 {len(p0)} 个，阻断 commit")
        _log_gate_failure(task_id, f"P0 门禁阻断: {[i['msg'] for i in p0]}")
        _fallback_to_drafting(task_id, f"自检门禁阻断：P0 级问题 {len(p0)} 个，需人工处理")
        return False

    # ---- P1: 自动修复（最多 MAX_REPAIR_ATTEMPTS 轮）----
    if p1:
        MAX_REPAIR_ATTEMPTS = 3
        current_text = doc_text
        all_p1_fixed = False

        for attempt in range(1, MAX_REPAIR_ATTEMPTS + 1):
            print(f"[WRITER-GATE] P1 修复尝试 #{attempt}/{MAX_REPAIR_ATTEMPTS}")
            repaired = _auto_repair_self_check(current_text, issues)

            if repaired is None or repaired == current_text:
                print(f"[WRITER-GATE] 第 #{attempt} 轮自动修复无变化")
                break

            # 写回修复后的文档（覆盖同一文件）
            with open(file_path, 'w') as f:
                f.write(repaired)

            # 重新验证
            tracker_out2 = tracker_scan(repaired)
            report2, issues2 = SelfCheckReportValidator.validate(repaired, tracker_out2)
            p1_remaining = [i for i in issues2 if i['severity'] == 'P1']
            p0_new = [i for i in issues2 if i['severity'] == 'P0']

            if not p0_new and not p1_remaining:
                all_p1_fixed = True
                issues = issues2  # 供后续 P2 提取
                print(f"[WRITER-GATE] P1 自动修复成功（第 #{attempt} 轮）")
                break
            else:
                print(f"[WRITER-GATE] 第 #{attempt} 轮后仍剩 {len(p0_new)} P0 + {len(p1_remaining)} P1")
                current_text = repaired
                issues = issues2  # 供下一轮使用最新 issues

        if not all_p1_fixed:
            print(f"[WRITER-GATE] 自动修复已达上限，回退到 drafting")
            _log_gate_failure(task_id,
                f"P1 自动修复 {MAX_REPAIR_ATTEMPTS} 轮后仍有问题: "
                f"{[i['msg'] for i in issues if i['severity'] in ('P0','P1')]}")
            _fallback_to_drafting(task_id,
                f"自检门禁自动修复 {MAX_REPAIR_ATTEMPTS} 轮后仍有 P0/P1 问题，需人工处理")
            return False

        # P2 警告（最终验证后的）
        p2_final = [i for i in issues if i['severity'] == 'P2']
        if p2_final:
            print(f"[WRITER-GATE]  P2 警告 {len(p2_final)} 个（不阻断）:")
            for i in p2_final:
                print(f"    {i['msg']}")

        p1_count = len(p1)
        add_comment(PROJECT, task_id, 'writer',
                    f'自检门禁：自动修复 {p1_count} 个 P1 问题通过')
        return True

    # ---- P2 仅警告 ----
    if p2:
        print(f"[WRITER-GATE] P2 警告 {len(p2)} 个（不阻断）:")
        for i in p2:
            print(f"    {i['msg']}")

    return True


def _log_gate_failure(task_id: str, reason: str):
    """记录门禁失败到日志文件。"""
    log_dir = os.path.join(KANBAN_DIR, '.gate-logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f'{PROJECT}-{task_id}.log')
    with open(log_path, 'a') as f:
        f.write(f'[{datetime.now().isoformat()}] GATE BLOCKED: {reason}\n')


def _fallback_to_drafting(task_id: str, reason: str):
    """回退任务到 drafting，附加失败报告。"""
    add_comment(PROJECT, task_id, 'writer', f'【自检门禁阻断】{reason}')
    update_task_status(PROJECT, task_id, 'drafting',
                       blocked_reason=reason, validate=False)


# ── 原有函数 ────────────────────────────────────────────────────────


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

        # 自检门禁 — 在 git commit 前强制执行
        if not self_check_commit_gate(file_path, task_id, title):
            print(f"[WRITER] 自检门禁阻断 {title}，已回退至 drafting")
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
- 自检通过项：wrapper.py 语法检查 + SelfCheckReportValidator 门禁
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

        # 自检门禁 — 在 git commit 前强制执行
        if not self_check_commit_gate(file_path, task_id, task['title']):
            print(f"[WRITER] 自检门禁阻断 {task['title']}，已回退至 drafting")
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
- 自检通过项：wrapper.py 语法检查 + SelfCheckReportValidator 门禁
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
