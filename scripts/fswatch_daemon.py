#!/usr/bin/env python3
"""fswatch 事件驱动守护进程 — 监听 .notify/ 目录，零轮询触发 Hermes 任务"""
import os
import sys
import json
import subprocess
import signal
import time
import sqlite3
from datetime import datetime

NOTIFY_DIR = "/Users/liufeng/Documents/DocProductionReview/.kanban/.notify"
CONTROL_DIR = "/Users/liufeng/Documents/DocProductionReview/.kanban/.control"
CONTROL_FILE = os.path.join(CONTROL_DIR, "automation_state.json")
HERMES = "/Users/liufeng/.hermes/hermes-agent/venv/bin/hermes"
LOG_DIR = "/Users/liufeng/.hermes/logs"
PROJECT_DIR = "/Users/liufeng/Documents/DocProductionReview"
KANBAN_DB = "/Users/liufeng/Documents/DocProductionReview/.kanban/yaya-zhujiao.db"

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(LOG_DIR, "fswatch.log"), "a") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[{ts}] {msg}", flush=True)

def read_human_feedback_for_writer():
    """读取 kanban DB，找有 human_feedback 的 revision/re_review 任务"""
    if not os.path.exists(KANBAN_DB):
        return None
    try:
        conn = sqlite3.connect(KANBAN_DB)
        c = conn.cursor()
        c.execute("SELECT id, title, file_path, revision_data, version, iteration_count FROM tasks WHERE status IN ('revision','re_review','drafting') ORDER BY updated_at ASC LIMIT 1")
        row = c.fetchone()
        conn.close()
        if not row:
            return None
        task_id, title, file_path, revision_data_json, version, iteration = row
        rev_data = json.loads(revision_data_json or '{}')
        human_feedback = rev_data.get('human_feedback', [])
        if not human_feedback:
            return None
        return {
            'task_id': task_id,
            'title': title,
            'file_path': file_path,
            'human_feedback': human_feedback,
            'version': version,
            'iteration': iteration or 0,
        }
    except Exception as e:
        log(f"read_human_feedback: 异常 {e}")
        return None

def read_task_id_and_human_feedback(task_id: str):
    """读取指定 task_id 的 human_feedback"""
    if not os.path.exists(KANBAN_DB):
        return []
    try:
        conn = sqlite3.connect(KANBAN_DB)
        c = conn.cursor()
        c.execute("SELECT revision_data FROM tasks WHERE id=?", (task_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return []
        rev_data = json.loads(row[0] or '{}')
        return rev_data.get('human_feedback', [])
    except Exception as e:
        log(f"read_task_feedback({task_id}): 异常 {e}")
        return []

def build_writer_prompt():
    """构建 Writer agent 的执行提示词"""
    feedback_info = read_human_feedback_for_writer()
    base_instruction = f"在 {PROJECT_DIR} 中运行 python3 scripts/writer.py 处理 yaya-zhujiao 项目的 Writer 工作流"

    if feedback_info:
        feedback_text = "\n".join(f"  - {fb}" for fb in feedback_info['human_feedback'])
        fp = feedback_info.get('file_path', '')
        return f"""任务：处理 {PROJECT_DIR} 的 Writer 工作流

【注意】当前有一个待处理任务（{feedback_info['title']}，文件：{fp}），包含人工审核反馈意见（human_feedback）。请你严格按以下步骤执行：

步骤一 —— 分析人工反馈：
逐条分析以下反馈意见，判断每条是否属实（在文档中有实际证据）：
{feedback_text}

对于「属实」或「半属实」的反馈：在文档中定位具体位置，给出修复方案，然后修改文档内容。
对于「不属实」的反馈：记录在 comment 中但不做修改。

步骤二 —— 修改文档：
依据步骤一的分析结果，直接修改文件 {fp}。每次修改后检查文件内容是否确实已修改（用 grep 验证）。

步骤三 —— 格式模板自查：
分析人类反馈中是否有任何点，是当前 Writer 文档格式模板中没有覆盖到的。如果有，将这些缺失的规则写入 /Users/liufeng/Documents/DocProductionReview/.kanban/writer_format_notes.md（追加，标记日期）。格式示例：
2026-05-18: [新规则] 文档必须包含当节知识点与前置知识点的关联说明（来自人类反馈：xxx）

步骤四 —— 提交：
完成上述所有修改后，执行：
python3 scripts/writer.py

当 writer.py 执行完毕后，检查输出确认流程正常。"""
    else:
        return f"{base_instruction}\n\n【注】当前无人工审核反馈，按标准流程执行。"

def build_reviewer_prompt():
    """构建 Reviewer agent 的执行提示词"""
    return f"""任务：在 {PROJECT_DIR} 中运行审核工作流，处理 yaya-zhujiao 项目

执行步骤：

步骤一 —— 运行审核脚本：
python3 scripts/reviewer.py

步骤二 —— 检查复审任务的 human_feedback（可选自我进化）：
reviewer.py 执行完毕后，检查哪些 re_review 任务被处理了。
对于每个被处理的复审任务，读取 revision_data 中的 human_feedback（如果有）。
对于每条 human_feedback，分析：
  - 这条反馈涉及的内容，是否在 Reviewer 当前审核规则（reusable-review-rules/）的覆盖范围之外？
  - 是否应将其新增为一条审核规则？（例如：人类指出了某个术语错误，但审核规则没有检查这个术语）
  - 如果应新增，分析应归到哪个审核维度（doc_completeness / term_consistency / rule_consistency / logic_self_consistency / extreme_scenario / cross_references / deliverables / changelog_standard）

如果发现审核规则需要更新：
  1. 将新规则写入 /Users/liufeng/Documents/DocProductionReview/.kanban/reviewer_scope_notes.md（追加，标记日期和来源 human_feedback task_id）
  2. 注意：这个文件只是记录，不需要修改 reusable-review-rules/wrapper.py——wrapper 负责调用外部工具，具体规则在 .vale.ini 或 markdownlint 配置中定义。

注意：步骤二是静默执行，不需要写任何 NOTIFY 或修改 kanban 状态。"""

def get_automation_state():
    """读取自动化控制状态"""
    try:
        if os.path.exists(CONTROL_FILE):
            with open(CONTROL_FILE) as f:
                data = json.load(f)
            running = data.get("running", True)
            paused = data.get("paused", False)
            return running, paused
    except:
        pass
    return True, False  # 默认运行中


def handle_notify(filepath):
    """处理单个 NOTIFY 文件"""
    if not os.path.isfile(filepath):
        return

    # 检查自动化控制状态
    running, paused = get_automation_state()
    if not running:
        log(f"自动化已停止，跳过 {os.path.basename(filepath)}")
        # 仍然清理文件
        try: os.remove(filepath)
        except: pass
        return
    if paused:
        log(f"自动化已暂停，跳过 {os.path.basename(filepath)}")
        return  # 不清除文件，恢复后继续处理

    filename = os.path.basename(filepath)
    if filename.startswith("."):
        return

    log(f"文件出现: {filename}")

    if filename.startswith("review-"):
        log("-> 触发 reviewer (profile: yaya-reviewer)")
        prompt = build_reviewer_prompt()
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
        prompt = build_writer_prompt()
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
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. 检查需要处理的状态
        c.execute("SELECT status, count(*) FROM tasks WHERE status IN ('awaiting_review', 'reviewing', 'revision', 're_review') GROUP BY status")
        rows = c.fetchall()

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
            # 2. 检查是否有废弃的 re_review 卡片（状态超过5分钟且 re_review_result='fail'）
            c.execute("SELECT id, title, revision_data, status_entered_at FROM tasks WHERE status='re_review'")
            stale_reviews = []
            for row2 in c.fetchall():
                tid, title, rd_json, entered = row2
                rev_data = json.loads(rd_json or '{}')
                if rev_data.get('re_review_result') == 'fail' and entered:
                    try:
                        et = datetime.fromisoformat(entered)
                        nt = datetime.fromisoformat(now_iso)
                        if (nt - et).total_seconds() > 300:  # >5分钟
                            stale_reviews.append((tid, title))
                    except:
                        pass
            if stale_reviews:
                for tid, title in stale_reviews:
                    # 自动迁移到 revision（而不是留在 re_review）
                    from kanban_ops import update_task_status, add_comment
                    update_task_status('yaya-zhujiao', tid, 'revision', validate=False)
                    add_comment('yaya-zhujiao', tid, 'system',
                                f'定时 bootstrap: re_review 超时(>5min)，自动迁移到 revision')
                    log(f"bootstrap: 迁移废弃 re_review -> revision: {tid} {title}")
                # 迁移后写 writer NOTIFY
                notify_path = os.path.join(NOTIFY_DIR, "writer-yaya-zhujiao")
                os.makedirs(NOTIFY_DIR, exist_ok=True)
                with open(notify_path, 'w') as f:
                    f.write('bootstrap writer for stale re_review')
                log("bootstrap: 写 NOTIFY -> writer (stale re_review migrated)")
            else:
                # 没有废弃的，正常触发 reviewer
                notify_path = os.path.join(NOTIFY_DIR, "review-yaya-zhujiao")
                os.makedirs(NOTIFY_DIR, exist_ok=True)
                with open(notify_path, 'w') as f:
                    f.write('bootstrap review for re_review')
                log("bootstrap: 写 NOTIFY -> reviewer (re_review)")

        conn.close()

    except Exception as e:
        log(f"bootstrap: 异常 {e}")


def main():
    import select as _select

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
    # 处理 bootstrap 写的 NOTIFY 文件
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

    last_bootstrap = time.time()

    try:
        while True:
            # 用 select 做 60 秒超时等待，同时支持 fswatch 事件和定时 bootstrap
            try:
                ready, _, _ = _select.select([fswatch_proc.stdout], [], [], 60)
            except ValueError:
                # stdout 已关闭
                log("fswatch stdout 关闭，退出")
                break

            if ready:
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

            # 每 60 秒执行一次定时 bootstrap
            if time.time() - last_bootstrap >= 60:
                last_bootstrap = time.time()
                # 先检查自动化状态
                running, paused = get_automation_state()
                if running and not paused:
                    log("定时 bootstrap: 扫描 kanban...")
                    bootstrap()
                else:
                    log(f"定时 bootstrap: 跳过（running={running} paused={paused}）")

    except KeyboardInterrupt:
        log("收到 SIGINT，退出")
    finally:
        fswatch_proc.terminate()
        fswatch_proc.wait()
        log("守护进程退出")


if __name__ == "__main__":
    main()
