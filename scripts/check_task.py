#!/usr/bin/env python3
"""Check task status in kanban"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kanban_ops import get_task, get_tasks_by_status

project = 'yaya-zhujiao'

task = get_task(project, 't_05tbojin')
if task:
    print("=== Task t_05tbojin ===")
    for k, v in task.items():
        print(f"  {k}: {v}")
else:
    print("Task not found")

print()
print("=== Current kanban summary ===")
for s in ['backlog', 'drafting', 'revision', 're_review', 'awaiting_review', 'blocked', 'approved']:
    tasks = get_tasks_by_status(project, s)
    if tasks:
        for t in tasks:
            print(f"  [{s}] {t['id']}: {t.get('title', '?')}")
