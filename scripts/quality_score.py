#!/usr/bin/env python3
"""质量评分计算"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kanban_ops import (
    get_task, get_comments, save_quality_score,
    get_evolution_suggestions, PROJECT_ROOT
)


def calculate_compliance_score(task: dict, comments: list) -> float:
    """合规分：检查 7 项必备内容是否齐全"""
    required = [
        '版本号', '变更记录', '目录', '状态机定义',
        '数据模型', '接口定义', '部署步骤'
    ]
    file_path = task.get('file_path', '')
    if not file_path or not os.path.exists(file_path):
        return 0.0

    with open(file_path) as f:
        content = f.read()

    found = sum(1 for item in required if item in content)
    return (found / len(required)) * 100


def calculate_ai_quality_score(task: dict) -> float:
    """AI 质量分：基于文档行数和迭代轮次估算"""
    file_path = task.get('file_path', '')
    line_count = 0
    if file_path and os.path.exists(file_path):
        with open(file_path) as f:
            line_count = sum(1 for _ in f)

    iteration = task.get('iteration_count', 0)
    # 基础分：文档越长基础分越高（上限 80）
    base = min(line_count / 10, 80)
    # 迭代惩罚：每轮 -5
    penalty = iteration * 5
    return max(base - penalty, 0)


def calculate_defect_trend_score(project: str, task: dict) -> float:
    """缺陷趋势分：审核轮次越少越好"""
    iteration = task.get('iteration_count', 0)
    if iteration == 0:
        return 100.0
    # 每增加一轮扣 15 分
    return max(100 - iteration * 15, 0)


def calculate_total(compliance: float, ai_quality: float,
                    defect_trend: float) -> float:
    """总分 = 合规分×0.4 + AI质量分×0.4 + 缺陷趋势分×0.2"""
    return round(compliance * 0.4 + ai_quality * 0.4 + defect_trend * 0.2, 2)


def score_task(project: str, task_id: str):
    """对单个任务评分"""
    task = get_task(project, task_id)
    if not task:
        print(f"任务不存在: {task_id}")
        return

    comments = get_comments(project, task_id)
    version = task.get('version', 'unknown')

    compliance = calculate_compliance_score(task, comments)
    ai_quality = calculate_ai_quality_score(task)
    defect_trend = calculate_defect_trend_score(project, task)
    total = calculate_total(compliance, ai_quality, defect_trend)

    scores = {
        'compliance': round(compliance, 2),
        'ai_quality': round(ai_quality, 2),
        'defect_trend': round(defect_trend, 2),
        'total': total,
        'breakdown': {
            'formula': '合规分×0.4 + AI质量分×0.4 + 缺陷趋势分×0.2',
            'compliance_weight': 0.4,
            'ai_quality_weight': 0.4,
            'defect_trend_weight': 0.2,
        }
    }

    save_quality_score(project, task_id, version, scores)
    print(f"[QUALITY] {task['title']}: total={total} "
          f"(c={compliance} a={ai_quality} d={defect_trend})")

    # 偏差检测
    if abs(total - compliance) > 40:
        print(f"[QUALITY] 警告: 总分与合规分偏差 > 40 ({total} vs {compliance})")

    return scores


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True)
    parser.add_argument('--task-id', required=True)
    args = parser.parse_args()
    score_task(args.project, args.task_id)
