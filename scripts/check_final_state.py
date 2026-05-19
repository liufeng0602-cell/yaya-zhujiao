#!/usr/bin/env python3
import sys, os
sys.path.insert(0, '/Users/liufeng/Documents/DocProductionReview')
from kanban_ops import get_task, get_tasks_by_status

project = 'yaya-zhujiao'

# S12 final state
task = get_task(project, 't_lym7hvdc')
printable = {k: v for k, v in task.items() if not isinstance(v, bytes)}
print("=== S12 Final State ===")
for k, v in sorted(printable.items()):
    print(f"  {k}: {v}")

# NOTIFY files
notify_dir = os.path.join('/Users/liufeng/Documents/DocProductionReview/.kanban', '.notify')
notify_files = os.listdir(notify_dir) if os.path.isdir(notify_dir) else []
print(f"\n=== NOTIFY files: {notify_files} ===")

# All tasks
print("\n=== All tasks by status ===")
for s in ['backlog', 'revision', 're_review', 'drafting', 'blocked', 'awaiting_review', 'approved', 'waiting_human_review']:
    tasks = get_tasks_by_status(project, s)
    if tasks:
        for t in tasks:
            print(f"  [{s}] {t['id']}: {t['title']}")
