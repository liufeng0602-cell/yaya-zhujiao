#!/usr/bin/env python3
"""Watcher 守护进程 — 监控文档生产审核循环健康状态

使用 watchdog 监听文件事件，执行 4 个看门狗检测。
每个项目独立运行一个 watcher 实例，通过 launchctl 管理。
无 watchdog 时自动降级为轮询模式。
"""

import os
import sys
import json
import time
import argparse
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HAS_WATCHDOG = False
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    pass

from kanban_ops import (
    get_tasks_by_status, get_task, update_task_status, add_comment, add_alert,
    PROJECT_ROOT, KANBAN_DIR
)

ALERTS_DIR = os.path.join(KANBAN_DIR, '.alerts')
HEARTBEAT_INTERVAL = 1800  # 30 分钟


class DocProductionHandler:
    """文件事件处理器 / 轮询处理器"""

    def __init__(self, project: str):
        self.project = project
        self.last_heartbeat = 0

    def on_any_event(self, event):
        if event.is_directory:
            return
        self.run_watchdogs()

    def run_watchdogs(self):
        self.check_stuck_tasks()
        self.check_dead_loop()
        self.check_data_loss()
        self.update_heartbeat()

    def check_stuck_tasks(self):
        for status in ['drafting', 'awaiting_review', 'p2_clearing']:
            tasks = get_tasks_by_status(self.project, status)
            for task in tasks:
                try:
                    updated = datetime.strptime(task['updated_at'], '%Y-%m-%d %H:%M:%S')
                except (ValueError, KeyError):
                    continue
                elapsed = (datetime.now() - updated).total_seconds()
                file_path = task.get('file_path', '')
                line_count = 0
                if file_path and os.path.exists(file_path):
                    try:
                        with open(file_path) as f:
                            line_count = sum(1 for _ in f)
                    except Exception:
                        pass
                if line_count < 500:
                    timeout = 2700
                elif line_count < 800:
                    timeout = 5400
                else:
                    timeout = 9000
                if elapsed > timeout:
                    self.alert(f'STUCK: task {task["id"]} in {status} '
                               f'for {int(elapsed)}s (limit {timeout}s)')

    def check_dead_loop(self):
        tasks = get_tasks_by_status(self.project, 'needs_revision')
        for task in tasks:
            if task.get('iteration_count', 0) >= 6:
                update_task_status(self.project, task['id'], 'blocked',
                                   blocked_reason='max_iterations_exceeded',
                                   blocked_recovery_target='backlog')
                add_comment(self.project, task['id'], 'watcher',
                            f'死循环：iteration={task["iteration_count"]} >= 6')
                self.alert(f'DEAD_LOOP: task {task["id"]} '
                           f'iteration={task["iteration_count"]}')

    def check_data_loss(self):
        for task in get_tasks_by_status(self.project, 'drafting'):
            fp = task.get('file_path', '')
            if fp and not os.path.exists(fp):
                self.alert(f'DATA_LOSS: {task["id"]} in drafting, file missing (不恢复)')

        for status in ['awaiting_review', 'needs_revision', 'approved',
                       'p2_clearing', 'p2_cleared', 'signed_off']:
            for task in get_tasks_by_status(self.project, status):
                fp = task.get('file_path', '')
                if fp and not os.path.exists(fp):
                    self.alert(f'DATA_LOSS: {task["id"]} file missing, git checkout')
                    subprocess.run(['git', 'checkout', '--', fp],
                                   capture_output=True, cwd=PROJECT_ROOT)
                    if not os.path.exists(fp):
                        update_task_status(self.project, task['id'], 'blocked',
                                           blocked_reason='data_loss',
                                           blocked_recovery_target='drafting')
                        self.alert(f'DATA_LOSS: restore failed, {task["id"]} blocked')

    def update_heartbeat(self):
        now = time.time()
        if now - self.last_heartbeat < HEARTBEAT_INTERVAL:
            return
        self.last_heartbeat = now
        heartbeat = {
            'project': self.project,
            'timestamp': datetime.now().isoformat(),
            'pid': os.getpid()
        }
        path = os.path.join(KANBAN_DIR, f'watcher_heartbeat_{self.project}.json')
        os.makedirs(KANBAN_DIR, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(heartbeat, f)

    def alert(self, message: str):
        add_alert(self.project, message)
        print(f'[WATCHER][{self.project}] {message}', file=sys.stderr, flush=True)


def write_started_marker(project: str):
    marker = {'project': project, 'started_at': datetime.now().isoformat(), 'pid': os.getpid()}
    path = os.path.join(KANBAN_DIR, f'watcher_started_{project}.json')
    os.makedirs(KANBAN_DIR, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(marker, f)


def run_polling_mode(project: str):
    print(f'[WATCHER] 轮询模式 (project={project})', file=sys.stderr)
    handler = DocProductionHandler(project)
    write_started_marker(project)
    while True:
        try:
            handler.run_watchdogs()
        except Exception as e:
            print(f'[WATCHER] 轮询异常: {e}', file=sys.stderr)
        time.sleep(30)


def main():
    parser = argparse.ArgumentParser(description='DocProductionReview Watcher')
    parser.add_argument('--project', required=True)
    args = parser.parse_args()

    print(f'[WATCHER] 启动 (project={args.project}, pid={os.getpid()})', file=sys.stderr)

    if not HAS_WATCHDOG:
        run_polling_mode(args.project)
        return

    write_started_marker(args.project)
    handler = DocProductionHandler(args.project)
    observer = Observer()

    class WatchdogHandler(FileSystemEventHandler):
        def on_any_event(self, event):
            handler.on_any_event(event)

    wd_handler = WatchdogHandler()

    for path in [
        os.path.join(PROJECT_ROOT, '.kanban'),
        os.path.join(PROJECT_ROOT, 'projects', args.project),
        os.path.join(PROJECT_ROOT, 'audit-reports'),
    ]:
        if os.path.exists(path):
            observer.schedule(wd_handler, path, recursive=True)
            print(f'[WATCHER] 监听: {path}', file=sys.stderr)

    observer.start()
    print('[WATCHER] 运行中...', file=sys.stderr)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == '__main__':
    main()
