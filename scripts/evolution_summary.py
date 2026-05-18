#!/usr/bin/env python3
"""进化总结生成 — 从 audit 报告中收集模式，生成进化建议"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kanban_ops import (
    get_tasks_by_status, get_comments, save_evolution_suggestion,
    get_evolution_suggestions, PROJECT_ROOT
)


def collect_patterns(project: str):
    """从已完成的任务中收集可进化模式"""
    signed_off = get_tasks_by_status(project, 'signed_off')
    approved = get_tasks_by_status(project, 'approved')
    all_done = signed_off + approved

    if not all_done:
        print("[EVO] 无已完成任务")
        return

    patterns = []
    for task in all_done:
        comments = get_comments(project, task['id'])
        reviewer_comments = [c for c in comments if c['author'] == 'reviewer']

        for c in reviewer_comments:
            content = c.get('content', '')
            # 检测 P0/P1 模式
            if 'P0' in content or 'P1' in content:
                patterns.append({
                    'task_id': task['id'],
                    'iteration': task.get('iteration_count', 0),
                    'content': content[:300]
                })

    print(f"[EVO] 发现 {len(patterns)} 个潜在模式 (from {len(all_done)} tasks)")

    # 生成进化建议（简化版）
    for i, p in enumerate(patterns[:5]):  # 最多 5 条
        save_evolution_suggestion(
            source='reviewer',
            task_id=p['task_id'],
            round_number=p['iteration'],
            tech=f'审计模式 #{i+1}: {p["content"][:100]}',
            recommendation='建议将此类问题加入 reusable-review-rules',
            plain=f'审核时反复出现类似问题，可以做个自动检查规则',
            p_level='P1',
            scope='universal'
        )

    print("[EVO] 进化建议已保存")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', default='yaya-zhujiao')
    args = parser.parse_args()
    collect_patterns(args.project)
