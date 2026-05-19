#!/usr/bin/env python3
"""Reviewer 主脚本 — 由 fswatch 触发，执行全量文档审核 (v3.0)

基于开源框架 AuditEngine + Judge 的刚性审核管线。
旧版（v2.x）的 "全量读文档 + 靠 LLM 一次性出报告" 逻辑已退役。

审核流程
--------
1. 加载文档，运行 HardcodedValueTracker 提取标记
2. AuditEngine.run() — 逐条执行所有注册的 BaseChecker
3. Judge.evaluate(report, iteration) — 裁决卡片状态
4. 根据 Decision 驱动 Git 状态变更 + 生成审计报告
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kanban_ops import (
    get_tasks_by_status, get_task,
    update_task_status, add_comment, increment_iteration,
    PROJECT_ROOT, KANBAN_DIR, AUDIT_REPORTS_DIR,
)

from reusable_review_rules.audit_engine import AuditEngine, print_report
from reusable_review_rules.judge import Judge
from reusable_review_rules.builtin_checkers import get_default_checkers

PROJECT = 'yaya-zhujiao'

# ── 全局 AuditEngine（注册所有生效的检查器） ─────────────────────
_engine = AuditEngine()
_engine.register_list(get_default_checkers(max_layer=1))


# ══════════════════════════════════════════════════════════════════════
# 审核执行
# ══════════════════════════════════════════════════════════════════════


def read_document(file_path: str) -> str:
    """读取文档全文"""
    if not file_path or not os.path.exists(file_path):
        return ''
    with open(file_path, 'r') as f:
        return f.read()


def run_audit(file_path: str, version: str) -> dict:
    """执行全量审核，返回 AuditEngine 格式报告。

    Returns
    -------
    dict with keys: P0, P1, P2, tracker, checkers, skipped, duration_ms
    (matching AuditEngine.run() output format).
    空文档 / 不可读时返回 cleaned-down dict 兼容下游。
    """
    content = read_document(file_path)
    if not content:
        return {
            'P0': [], 'P1': [], 'P2': [],
            'tracker': {'params': [], 'configs': [], 'errors': []},
            'checkers': [], 'skipped': [], 'duration_ms': 0,
        }

    return _engine.run(content)


# ══════════════════════════════════════════════════════════════════════
# 审计报告生成
# ══════════════════════════════════════════════════════════════════════


def generate_report(project: str, task: dict, audit_result: dict,
                    decision) -> str:
    """生成 Markdown 审计报告。"""
    os.makedirs(os.path.join(AUDIT_REPORTS_DIR, project), exist_ok=True)

    file_name = os.path.basename(task.get('file_path', 'unknown.md'))
    base = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
    version = task.get('version', 'unknown')
    report_name = f'{base}_audit_report_{version}.md'
    report_path = os.path.join(AUDIT_REPORTS_DIR, project, report_name)

    p0s = audit_result.get('P0', [])
    p1s = audit_result.get('P1', [])
    p2s = audit_result.get('P2', [])

    with open(report_path, 'w') as f:
        f.write(f'# 审计报告：{task["title"]}\n')
        f.write(f'审核版本：{version}\n')
        f.write(f'审核日期：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'审核引擎：AuditEngine v3.0\n\n')

        for level, issues, label in [
            ('P0', p0s, '阻断问题 — 必须修复后才能提交'),
            ('P1', p1s, '审核问题 — 提交前必须审查'),
            ('P2', p2s, '建议项 — 不阻断，推荐修复'),
        ]:
            f.write(f'### {level}（{label}）\n')
            if issues:
                f.write('| 检查器 | 行号 | 问题描述 |\n')
                f.write('|--------|------|----------|\n')
                for iss in issues:
                    loc = iss.get('location', '-')
                    loc = str(loc) if loc else '-'
                    ev = iss.get('evidence', '')
                    msg = iss['msg']
                    if ev:
                        msg = f'{msg}\n（证据：{ev}）'
                    f.write(f'| {iss["check_id"]} | {loc} | {msg} |\n')
            else:
                f.write('无\n')
            f.write('\n')

        f.write('## 审核结论\n')
        f.write(f'- P0: {len(p0s)} 个\n')
        f.write(f'- P1: {len(p1s)} 个\n')
        f.write(f'- P2: {len(p2s)} 个\n')
        f.write(f'- 决策：{decision.state}\n')
        f.write(f'- 原因：{decision.reason}\n')

    print(f"[REVIEWER] 审计报告: {report_path}")
    return report_path


# ══════════════════════════════════════════════════════════════════════
# 状态驱动
# ══════════════════════════════════════════════════════════════════════


def trigger_writer():
    """写 NOTIFY 文件触发 writer"""
    notify_dir = os.path.join(KANBAN_DIR, '.notify')
    os.makedirs(notify_dir, exist_ok=True)
    notify_path = os.path.join(notify_dir, f'writer-{PROJECT}')
    print(f"[REVIEWER] 触发 writer (NOTIFY: {notify_path})...")
    with open(notify_path, 'w') as f:
        f.write(f'NOTIFY by reviewer at {datetime.now().isoformat()}')


def _save_report_and_comment(project: str, task_id: str, task: dict,
                              audit_result: dict, decision) -> str:
    """生成报告 + 写评论，返回报告路径。"""
    report_path = generate_report(project, task, audit_result, decision)
    p0c = len(audit_result['P0'])
    p1c = len(audit_result['P1'])
    p2c = len(audit_result['P2'])
    add_comment(project, task_id, 'reviewer',
                f'审核完成 — 决策: {decision.state} '
                f'(P0={p0c} P1={p1c} P2={p2c})。'
                f'审计报告：{report_path}')
    return report_path


# ══════════════════════════════════════════════════════════════════════
# 首次审核
# ══════════════════════════════════════════════════════════════════════


def process_review(task: dict):
    """审核单个任务（首次审核）。"""
    task_id = task['id']
    file_path = task.get('file_path', '')
    version = task.get('version', 'unknown')
    iteration = task.get('iteration_count', 0)
    print(f"[REVIEWER] 审核: {task['title']} ({file_path}) "
          f"[iteration={iteration}]")

    # Claim: awaiting_review -> reviewing
    update_task_status(PROJECT, task_id, 'reviewing')
    add_comment(PROJECT, task_id, 'reviewer',
                'Reviewer 开始审核（AuditEngine v3.0 — 多层防御管线）')

    # 执行审核
    audit = run_audit(file_path, version)
    decision = Judge.evaluate(audit, iteration=iteration)

    # 生成报告 + 写评论
    _save_report_and_comment(PROJECT, task_id, task, audit, decision)

    # 根据 Decision 驱动卡片状态
    if decision.state == 'needs_revision':
        # P0 > 0 或 P1 > 0 — 必须修改
        increment_iteration(PROJECT, task_id)
        task = get_task(PROJECT, task_id)  # 刷新 iteration
        cur_iter = task['iteration_count'] if task else iteration + 1

        # 封顶检查（Judge 已判断，但需要再次检查以留出下钻空间）
        if cur_iter >= 6:
            update_task_status(PROJECT, task_id, 'blocked',
                               blocked_reason='max_iterations_exceeded',
                               blocked_recovery_target='backlog')
            add_comment(PROJECT, task_id, 'reviewer',
                        f'iteration_count={cur_iter} >= 6，自动 blocked。')
            print(f"[REVIEWER] -> blocked (iteration={cur_iter})")
            return

        revision_data = {
            'p0_count': len(audit['P0']),
            'p1_count': len(audit['P1']),
            'p2_count': len(audit['P2']),
            'decision': decision.state,
            'decision_reason': decision.reason,
        }
        update_task_status(PROJECT, task_id, 'revision',
                           p0_count=revision_data['p0_count'],
                           p1_count=revision_data['p1_count'],
                           p2_count=revision_data['p2_count'],
                           revision_data=json.dumps(revision_data))
        print(f"[REVIEWER] -> revision ({decision.reason})")
        trigger_writer()

    elif decision.state == 'p2_clearing':
        # P0=0, P1=0, P2>0 — P2 清零
        revision_data = {
            'p0_count': 0,
            'p1_count': 0,
            'p2_count': len(audit['P2']),
            'decision': decision.state,
            'decision_reason': decision.reason,
        }
        update_task_status(PROJECT, task_id, 'p2_clearing',
                           p0_count=0, p1_count=0,
                           p2_count=len(audit['P2']),
                           revision_data=json.dumps(revision_data))
        print(f"[REVIEWER] -> p2_clearing ({decision.reason})")
        # P2 清零需要 Writer 处理，触发通知
        trigger_writer()

    elif decision.state == 'blocked':
        # 迭代封顶
        update_task_status(PROJECT, task_id, 'blocked',
                           blocked_reason=decision.reason,
                           blocked_recovery_target='backlog')
        print(f"[REVIEWER] -> blocked ({decision.reason})")

    else:  # waiting_human_review
        # 全通过
        update_task_status(PROJECT, task_id, 'waiting_human_review',
                           p0_count=0, p1_count=0, p2_count=0)
        print(f"[REVIEWER] -> waiting_human_review")


# ══════════════════════════════════════════════════════════════════════
# 复审
# ══════════════════════════════════════════════════════════════════════


def process_re_review(task: dict):
    """复审单个任务（修订后的文档）。"""
    task_id = task['id']
    file_path = task.get('file_path', '')
    version = task.get('version', 'unknown')
    iteration = task.get('iteration_count', 0)
    print(f"[REVIEWER] 复审: {task['title']} ({file_path}) "
          f"[iteration={iteration}]")

    # Claim: re_review -> re_reviewing
    update_task_status(PROJECT, task_id, 're_reviewing')
    add_comment(PROJECT, task_id, 'reviewer',
                'Reviewer 开始复审（修订后检查）')

    # 全量审核（复用同一套逻辑）
    audit = run_audit(file_path, version)
    decision = Judge.evaluate(audit, iteration=iteration)

    # 生成报告
    _save_report_and_comment(PROJECT, task_id, task, audit, decision)

    if decision.state == 'needs_revision':
        # 复审不通过 — 回 revision 让 writer 修改（避免 re_review 自环）
        increment_iteration(PROJECT, task_id)
        task = get_task(PROJECT, task_id)
        cur_iter = task['iteration_count'] if task else iteration + 1

        if cur_iter >= 6:
            update_task_status(PROJECT, task_id, 'blocked',
                               blocked_reason='max_iterations_exceeded',
                               blocked_recovery_target='backlog')
            add_comment(PROJECT, task_id, 'reviewer',
                        f'iteration_count={cur_iter} >= 6，自动 blocked。')
            print(f"[REVIEWER] 复审不通过 -> blocked (iteration={cur_iter})")
            return

        revision_data = {
            'p0_count': len(audit['P0']),
            'p1_count': len(audit['P1']),
            'p2_count': len(audit['P2']),
            're_review_result': 'fail',
            'decision': decision.state,
            'decision_reason': decision.reason,
        }
        update_task_status(PROJECT, task_id, 'revision',
                           p0_count=revision_data['p0_count'],
                           p1_count=revision_data['p1_count'],
                           p2_count=revision_data['p2_count'],
                           revision_data=json.dumps(revision_data))
        print(f"[REVIEWER] 复审不通过 -> revision ({decision.reason})")
        trigger_writer()

    elif decision.state == 'p2_clearing':
        # 复审中仍有 P2 问题 — P2 清零
        revision_data = {
            'p0_count': 0,
            'p1_count': 0,
            'p2_count': len(audit['P2']),
            're_review_result': 'fail_p2',
            'decision': decision.state,
            'decision_reason': decision.reason,
        }
        update_task_status(PROJECT, task_id, 'p2_clearing',
                           p0_count=0, p1_count=0,
                           p2_count=len(audit['P2']),
                           revision_data=json.dumps(revision_data))
        print(f"[REVIEWER] 复审 -> p2_clearing ({decision.reason})")
        trigger_writer()

    else:
        # 复审通过
        update_task_status(PROJECT, task_id, 'waiting_human_review',
                           p0_count=0, p1_count=0, p2_count=0,
                           revision_data=json.dumps({
                               're_review_result': 'pass',
                               'p0_count': 0,
                               'p1_count': 0,
                               'p2_count': 0,
                           }))
        print(f"[REVIEWER] 复审通过 -> waiting_human_review")


# ══════════════════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════════════════


def main():
    print(f"[REVIEWER] ═══ ═══ ═══ AuditEngine v3.0 ═══ ═══ ═══")
    print(f"[REVIEWER] 扫描项目: {PROJECT}")

    # 优先处理复审（队列较短，应该立即处理）
    re_review_tasks = get_tasks_by_status(PROJECT, 're_review')
    if re_review_tasks:
        re_review_tasks.sort(key=lambda t: t.get('updated_at', ''))
        task = re_review_tasks[0]
        print(f"[REVIEWER] 发现复审任务: {task['id']} {task['title']}")
        process_re_review(task)
        return

    # 再处理首次审核
    tasks = get_tasks_by_status(PROJECT, 'awaiting_review')
    if not tasks:
        print("[REVIEWER] 无 awaiting_review 任务")
        return

    task = tasks[0]
    print(f"[REVIEWER] 发现任务: {task['id']} {task['title']}")
    process_review(task)


if __name__ == '__main__':
    main()
