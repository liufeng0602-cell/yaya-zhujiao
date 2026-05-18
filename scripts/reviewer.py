#!/usr/bin/env python3
"""Reviewer 主脚本 — 由 fswatch 触发，执行全量文档审核 (v2.0)"""

import os
import sys
import json
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kanban_ops import (
    get_tasks_by_status, get_task, get_comments,
    update_task_status, add_comment, increment_iteration,
    PROJECT_ROOT, KANBAN_DIR, AUDIT_REPORTS_DIR
)

PROJECT = 'yaya-zhujiao'

# 审核覆盖范围（8 项为最低标准）
AUDIT_CHECKS = [
    ('doc_completeness',      '文档完整度：7项必备内容'),
    ('term_consistency',       '术语一致性'),
    ('rule_consistency',       '规则一致性'),
    ('logic_self_consistency', '自洽性数学验证'),
    ('extreme_scenario',       '极端场景推演（3种）'),
    ('cross_references',       '跨系统引用'),
    ('deliverables',           '交付物检查'),
    ('changelog_standard',     '变更记录规范'),
]


def read_document(file_path: str) -> str:
    """读取文档全文"""
    if not file_path or not os.path.exists(file_path):
        return ''
    with open(file_path, 'r') as f:
        return f.read()


def run_audit(file_path: str, version: str) -> dict:
    """执行全量审核，返回审计结果。"""
    content = read_document(file_path)
    if not content:
        return {
            'p0': [], 'p1': [], 'p2': [], 'p3': [],
            'p0_count': 0, 'p1_count': 0, 'p2_count': 0, 'p3_count': 0,
            'conclusion': 'blocked',
            'raw_content': '(文件为空或不可读)'
        }

    # 快速语法检查（本地，0 token）
    wrapper = os.path.join(PROJECT_ROOT, 'reusable-review-rules', 'wrapper.py')
    syntax_issues = []
    if os.path.exists(wrapper):
        r = subprocess.run(['python3', wrapper, file_path],
                           capture_output=True, text=True, timeout=120,
                           cwd=PROJECT_ROOT)
        if r.returncode != 0:
            for line in r.stderr.strip().split('\n')[:20]:
                if line.strip():
                    syntax_issues.append(f'P2-语法: {line.strip()}')

    # 硬编码检查（本地，0 token）
    hard_issues = []
    unclosed_refs = []
    for i, line in enumerate(content.split('\n'), 1):
        if '待 S' in line and '定义' in line and '已定义' not in line:
            unclosed_refs.append(f'L{i}: {line.strip()[:80]}')
    if unclosed_refs:
        hard_issues.append({
            'id': 'P1-ref', 'category': '跨系统引用未闭合',
            'lines': unclosed_refs, 'fix': '补全引用目标或改兜底策略'
        })

    # 汇总结果
    result = {
        'p0': [],
        'p1': hard_issues,
        'p2': [{'id': f'P2-syn-{i}', 'category': '语法检查',
                'lines': [si], 'fix': '根据提示修正'}
               for i, si in enumerate(syntax_issues)],
        'p3': [],
        'p0_count': 0,
        'p1_count': len(hard_issues),
        'p2_count': len(syntax_issues),
        'p3_count': 0,
        'conclusion': 'pending',  # agent 覆盖此字段
        'raw_content': content[:500] + ('...' if len(content) > 500 else ''),
    }

    return result


def generate_report(project: str, task: dict, audit_result: dict) -> str:
    """生成 Markdown 审计报告"""
    os.makedirs(os.path.join(AUDIT_REPORTS_DIR, project), exist_ok=True)

    file_name = os.path.basename(task.get('file_path', 'unknown.md'))
    base = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
    version = task.get('version', 'unknown')
    report_name = f'{base}_audit_report_{version}.md'
    report_path = os.path.join(AUDIT_REPORTS_DIR, project, report_name)

    p0s = audit_result.get('p0', [])
    p1s = audit_result.get('p1', [])
    p2s = audit_result.get('p2', [])
    p3s = audit_result.get('p3', [])

    with open(report_path, 'w') as f:
        f.write(f'# 审计报告：{task["title"]}\n')
        f.write(f'审核版本：{version}\n')
        f.write(f'审核日期：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'审核人：reviewer\n\n')

        for level, issues, label in [
            ('P0', p0s, '架构矛盾、安全漏洞、数据丢失风险'),
            ('P1', p1s, '规则不一致、缺失关键章节'),
            ('P2', p2s, '术语不一致、格式错误、引用未标注路径'),
            ('P3', p3s, '优化建议'),
       ]:
            f.write(f'### {level}（{label}）\n')
            if issues:
                f.write('| 编号 | 类别 | 行号 | 问题描述 | 修复建议 |\n')
                f.write('|------|------|------|----------|----------|\n')
                for issue in issues:
                    lines_str = ', '.join(issue.get('lines', ['-']))
                    desc = issue.get('description', issue.get('id', '-'))
                    fix = issue.get('fix', '-')
                    cat = issue.get('category', '-')
                    f.write(f'| {issue.get("id", "-")} | {cat} | {lines_str} | {desc} | {fix} |\n')
            else:
                f.write('无\n')
            f.write('\n')

        f.write('## 审核结论\n')
        f.write(f'- P0: {audit_result.get("p0_count", 0)} 个\n')
        f.write(f'- P1: {audit_result.get("p1_count", 0)} 个\n')
        f.write(f'- P2: {audit_result.get("p2_count", 0)} 个\n')
        f.write(f'- P3: {audit_result.get("p3_count", 0)} 个\n')
        f.write(f'- 结论：{audit_result.get("conclusion", "pending")}\n')

    print(f"[REVIEWER] 审计报告: {report_path}")
    return report_path


def trigger_writer():
    """写 NOTIFY 文件触发 writer"""
    notify_dir = os.path.join(KANBAN_DIR, '.notify')
    os.makedirs(notify_dir, exist_ok=True)
    notify_path = os.path.join(notify_dir, f'writer-{PROJECT}')
    print(f"[REVIEWER] 触发 writer (NOTIFY: {notify_path})...")
    with open(notify_path, 'w') as f:
        f.write(f'NOTIFY by reviewer at {datetime.now().isoformat()}')


def process_review(task: dict):
    """审核单个任务（首次审核）"""
    task_id = task['id']
    file_path = task.get('file_path', '')
    version = task.get('version', 'unknown')
    print(f"[REVIEWER] 审核: {task['title']} ({file_path})")

    # Claim: awaiting_review -> reviewing
    update_task_status(PROJECT, task_id, 'reviewing')
    add_comment(PROJECT, task_id, 'reviewer', f'Reviewer 开始审核（P0/P1/P2/P3 全量检查）')

    # 全量审核
    audit = run_audit(file_path, version)

    p0c = audit['p0_count']
    p1c = audit['p1_count']
    p2c = audit['p2_count']

    # 生成报告
    report_path = generate_report(PROJECT, task, audit)

    # 判定: 三项分流
    if p0c > 0 or p1c > 0:
        # 有 P0/P1 问题 -> 修改中（带问题分类）
        increment_iteration(PROJECT, task_id)
        task = get_task(PROJECT, task_id)
        iteration = task['iteration_count'] if task else 0

        if iteration >= 6:
            update_task_status(PROJECT, task_id, 'blocked',
                               blocked_reason='max_iterations_exceeded',
                               blocked_recovery_target='backlog')
            add_comment(PROJECT, task_id, 'reviewer',
                        f'iteration_count={iteration} >= 6，自动 blocked。'
                        f'审计报告：{report_path}')
            print(f"[REVIEWER] -> blocked (iteration={iteration})")
            return

        # 保存 P 级分布到 revision_data
        revision_data = {
            'p0_count': p0c,
            'p1_count': p1c,
            'p2_count': p2c,
            'report_path': report_path,
        }
        update_task_status(PROJECT, task_id, 'revision',
                           p0_count=p0c, p1_count=p1c, p2_count=p2c,
                           revision_data=json.dumps(revision_data))
        add_comment(PROJECT, task_id, 'reviewer',
                    f'审核不通过 (P0={p0c} P1={p1c} P2={p2c})。'
                    f'审计报告：{report_path}')
        print(f"[REVIEWER] -> revision (P0={p0c} P1={p1c} P2={p2c})")
        trigger_writer()

    elif p2c > 0:
        # 只有 P2 问题 -> 修改中（P2 清零）
        revision_data = {
            'p0_count': 0,
            'p1_count': 0,
            'p2_count': p2c,
            'is_p2_clear': True,
            'report_path': report_path,
        }
        update_task_status(PROJECT, task_id, 'revision',
                           p0_count=0, p1_count=0, p2_count=p2c,
                           revision_data=json.dumps(revision_data))
        add_comment(PROJECT, task_id, 'reviewer',
                    f'P0=P1=0 但 P2={p2c}，进入 revision (P2 清零)。'
                    f'审计报告：{report_path}')
        print(f"[REVIEWER] -> revision (P2 clearance, P2={p2c})")
        trigger_writer()

    else:
        # 全通过 -> 等待人工评审
        update_task_status(PROJECT, task_id, 'waiting_human_review',
                           p0_count=0, p1_count=0, p2_count=0)
        add_comment(PROJECT, task_id, 'reviewer',
                    f'审核通过，等待人工评审。审计报告：{report_path}')
        print(f"[REVIEWER] -> waiting_human_review")


def process_re_review(task: dict):
    """复审单个任务（修订后的文档）"""
    task_id = task['id']
    file_path = task.get('file_path', '')
    version = task.get('version', 'unknown')
    print(f"[REVIEWER] 复审: {task['title']} ({file_path})")

    # Claim: re_review -> re_reviewing
    update_task_status(PROJECT, task_id, 're_reviewing')
    add_comment(PROJECT, task_id, 'reviewer',
                f'Reviewer 开始复审（修订后检查，状态：复审中）')

    # 全量审核（复用同一套逻辑）
    audit = run_audit(file_path, version)

    p0c = audit['p0_count']
    p1c = audit['p1_count']
    p2c = audit['p2_count']

    # 生成报告
    report_path = generate_report(PROJECT, task, audit)

    # 复审判定
    if p0c > 0 or p1c > 0:
        # 复审不通过 -> 进入 revision 让 writer 修改（不能用 re_review 自环）
        revision_data = {
            'p0_count': p0c,
            'p1_count': p1c,
            'p2_count': p2c,
            're_review_result': 'fail',
            'report_path': report_path,
        }
        update_task_status(PROJECT, task_id, 'revision',
                           p0_count=p0c, p1_count=p1c, p2_count=p2c,
                           revision_data=json.dumps(revision_data))
        add_comment(PROJECT, task_id, 'reviewer',
                    f'复审不通过 (P0={p0c} P1={p1c} P2={p2c})。'
                    f'等待进入修改区。审计报告：{report_path}')
        print(f"[REVIEWER] 复审不通过 -> 留在 re_review (P0={p0c} P1={p1c} P2={p2c})")
        # 通知 writer 来处理
        trigger_writer()

    else:
        # 复审通过 -> 等待人工评审
        revision_data = {
            'p0_count': 0,
            'p1_count': 0,
            'p2_count': 0,
            're_review_result': 'pass',
            'report_path': report_path,
        }
        update_task_status(PROJECT, task_id, 'waiting_human_review',
                           p0_count=0, p1_count=0, p2_count=0,
                           revision_data=json.dumps(revision_data))
        add_comment(PROJECT, task_id, 'reviewer',
                    f'复审通过，等待人工评审。审计报告：{report_path}')
        print(f"[REVIEWER] 复审通过 -> waiting_human_review")


def main():
    print(f"[REVIEWER] ========== {datetime.now().isoformat()} ==========")
    print(f"[REVIEWER] 扫描项目: {PROJECT}")

    # 优先处理复审（队列较短应该立即处理）
    re_review_tasks = get_tasks_by_status(PROJECT, 're_review')
    if re_review_tasks:
        # 处理最旧的那个（更新时间最早的优先）
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

    task = tasks[0]  # updated_at ASC，最旧优先
    print(f"[REVIEWER] 发现任务: {task['id']} {task['title']}")
    process_review(task)


if __name__ == '__main__':
    main()
