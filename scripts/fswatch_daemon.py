#!/usr/bin/env python3
"""fswatch 事件驱动守护进程 — 监听 .notify/ 目录，零轮询触发 Hermes 任务"""
import os
import sys
import subprocess
import signal
import time

NOTIFY_DIR = "/Users/liufeng/Documents/DocProductionReview/.kanban/.notify"
HERMES = "/Users/liufeng/.hermes/hermes-agent/venv/bin/hermes"
LOG_DIR = "/Users/liufeng/.hermes/logs"
PROJECT_DIR = "/Users/liufeng/Documents/DocProductionReview"

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(LOG_DIR, "fswatch.log"), "a") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[{ts}] {msg}", flush=True)

def handle_notify(filepath):
    """处理单个 NOTIFY 文件"""
    if not os.path.isfile(filepath):
        return
    filename = os.path.basename(filepath)
    if filename.startswith("."):
        return

    log(f"文件出现: {filename}")

    if filename.startswith("review-"):
        log("-> 触发 reviewer (profile: yaya-reviewer)")
        prompt = f"在 {PROJECT_DIR} 中运行 python3 scripts/reviewer.py 处理 yaya-zhujiao 项目的审核工作流"
        r = subprocess.run(
            [HERMES, "chat", "-q", prompt, "--profile", "yaya-reviewer"],
            cwd=PROJECT_DIR,
            capture_output=True, text=True, timeout=600
        )
        log(f"-> reviewer 完成 (exit={r.returncode})")
        out = (r.stdout or "")[:500]
        if out:
            log(f"   stdout: {out}")
        if r.stderr:
            log(f"   stderr: {r.stderr[:200]}")

    elif filename.startswith("writer-"):
        log("-> 触发 writer (profile: yaya)")
        prompt = f"在 {PROJECT_DIR} 中运行 python3 scripts/writer.py 处理 yaya-zhujiao 项目的 Writer 工作流"
        r = subprocess.run(
            [HERMES, "chat", "-q", prompt, "--profile", "yaya"],
            cwd=PROJECT_DIR,
            capture_output=True, text=True, timeout=600
        )
        log(f"-> writer 完成 (exit={r.returncode})")
        out = (r.stdout or "")[:500]
        if out:
            log(f"   stdout: {out}")
        if r.stderr:
            log(f"   stderr: {r.stderr[:200]}")

    else:
        log(f"-> 未知类型: {filename}，跳过")

    # 清理 NOTIFY 文件
    try:
        os.remove(filepath)
        log(f"已清除 {filepath}")
    except OSError as e:
        log(f"清除失败: {e}")


def bootstrap():
    """启动自愈：扫描 kanban 看板，有待处理任务则写 NOTIFY 触发循环"""
    kanban_db = "/Users/liufeng/Documents/DocProductionReview/.kanban/yaya-zhujiao.db"
    if not os.path.exists(kanban_db):
        log("bootstrap: kanban 数据库不存在，跳过")
        return

    import sqlite3
    try:
        conn = sqlite3.connect(kanban_db)
        c = conn.cursor()
        # 检查所有需要处理的状态
        c.execute("SELECT status, count(*) FROM tasks WHERE status IN ('awaiting_review', 'reviewing', 'revision', 're_review') GROUP BY status")
        rows = c.fetchall()
        conn.close()

        if not rows:
            log("bootstrap: 无待处理任务，跳过")
            return

        pending = {s: n for s, n in rows}
        log(f"bootstrap: 发现待处理任务 {pending}")

        if 'awaiting_review' in pending:
            notify_path = os.path.join(NOTIFY_DIR, "review-yaya-zhujiao")
            os.makedirs(NOTIFY_DIR, exist_ok=True)
            with open(notify_path, 'w') as f:
                f.write('bootstrap review')
            log("bootstrap: 写 NOTIFY -> reviewer (awaiting_review)")

        if 'reviewing' in pending:
            notify_path = os.path.join(NOTIFY_DIR, "review-yaya-zhujiao")
            os.makedirs(NOTIFY_DIR, exist_ok=True)
            with open(notify_path, 'w') as f:
                f.write('bootstrap review (reviewing)')
            log("bootstrap: 写 NOTIFY -> reviewer (reviewing)")

        if 'revision' in pending:
            notify_path = os.path.join(NOTIFY_DIR, "writer-yaya-zhujiao")
            os.makedirs(NOTIFY_DIR, exist_ok=True)
            with open(notify_path, 'w') as f:
                f.write('bootstrap writer for revision')
            log("bootstrap: 写 NOTIFY -> writer (revision)")

        if 're_review' in pending:
            notify_path = os.path.join(NOTIFY_DIR, "review-yaya-zhujiao")
            os.makedirs(NOTIFY_DIR, exist_ok=True)
            with open(notify_path, 'w') as f:
                f.write('bootstrap review for re_review')
            log("bootstrap: 写 NOTIFY -> reviewer (re_review)")

    except Exception as e:
        log(f"bootstrap: 异常 {e}")


def main():
    log("守护进程启动")
    os.makedirs(NOTIFY_DIR, exist_ok=True)
    log(f"监听目录: {NOTIFY_DIR}")

    # 先处理启动时已有的 NOTIFY 文件（可能上次退出时遗留）
    for f in sorted(os.listdir(NOTIFY_DIR)):
        fp = os.path.join(NOTIFY_DIR, f)
        if os.path.isfile(fp) and not f.startswith("."):
            log(f"处理遗留文件: {f}")
            handle_notify(fp)

    # 启动自愈：有待处理任务就写 NOTIFY 触发循环
    bootstrap()

    # 处理 bootstrap 写的 NOTIFY 文件（fswatch 还未开始，手动触发）
    for f in sorted(os.listdir(NOTIFY_DIR)):
        fp = os.path.join(NOTIFY_DIR, f)
        if os.path.isfile(fp) and not f.startswith("."):
            log(f"bootstrap 后处理: {f}")
            handle_notify(fp)

    # 启动 fswatch
    fswatch_proc = subprocess.Popen(
        ["fswatch", "-0", NOTIFY_DIR],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        bufsize=0
    )
    log(f"fswatch PID: {fswatch_proc.pid}")

    try:
        while True:
            # 读取 null 分隔的事件
            chunk = b""
            while True:
                byte = fswatch_proc.stdout.read(1)
                if not byte:
                    log("fswatch stdout 关闭，退出")
                    return
                if byte == b"\x00":
                    break
                chunk += byte

            event_path = chunk.decode("utf-8", errors="replace").strip()
            if event_path:
                handle_notify(event_path)

    except KeyboardInterrupt:
        log("收到 SIGINT，退出")
    finally:
        fswatch_proc.terminate()
        fswatch_proc.wait()
        log("守护进程退出")


if __name__ == "__main__":
    main()
