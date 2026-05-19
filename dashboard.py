#!/usr/bin/env python3
"""DocProductionReview Dashboard v3.0 — 全量文档 / 质量评分 / 人工审核 / 控制按钮"""
import json, os, re, sqlite3, subprocess, sys, shutil
from datetime import datetime, timezone
from pathlib import Path
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="DocProductionReview Dashboard v3")
PROJECT_ROOT = Path(__file__).parent
KANBAN_DIR = PROJECT_ROOT / ".kanban"
ALERTS_DIR = KANBAN_DIR / ".alerts"
AUDIT_DIR = PROJECT_ROOT / "audit-reports"
CONTROL_DIR = KANBAN_DIR / ".control"
CONTROL_FILE = CONTROL_DIR / "automation_state.json"
NOTIFY_DIR = KANBAN_DIR / ".notify"
HERMES_HOME = Path.home() / ".hermes" / "profiles"
SUBSYSTEMS_DIR = PROJECT_ROOT / "subsystems"
sys.path.insert(0, str(PROJECT_ROOT))
from kanban_ops import get_document_content, get_task, update_task_status, add_comment

default_project = "yaya-zhujiao"

# 列布局：(key, label, is_combined, (upper_status, lower_status), tooltip)
KANBAN_LAYOUT = [
    ("finalized",        "已封版",    False, ("finalized",),
     "人工确认通过，文档已完成并封版。"),
    ("backlog",          "文档目录",  False, ("backlog",),
     "尚未分配的文档任务，等待 Writer 认领后开始撰写。"),
    ("drafting",         "文档撰写",  False, ("drafting",),
     "Writer 正在撰写文档中。"),
    # 审查+修改（组合列）：上栏=审查中，下栏=待审查+修改中
    ("review_modify",    "审查+修改", True,  ("reviewing", "awaiting_review", "revision"),
     "上栏：Reviewer 正在审查文档。下栏：待审查或 Writer 正在修改中。"),
    # 复审+修改（组合列）：上栏=复审中，下栏=复审不通过等待修改
    ("re_review_modify", "复审+修改", True,  ("re_reviewing", "re_review"),
     "上栏：Reviewer 正在复审。下栏：复审不通过，需要 Writer 修改后再次提交。"),
    ("waiting_human_review", "人工审核", False, ("waiting_human_review",),
     "复审通过，等待您（liufeng）人工审核确认。"),
    ("blocked",          "阻塞",      False, ("blocked",),
     "环境问题导致流程无法继续（如工具缺失、git 失败、超过最大迭代次数）。需要您手动处理恢复。"),
]

ALERT_SECONDS = {
    "drafting": 3600, "awaiting_review": 1800, "reviewing": 1800,
    "revision": 7200, "waiting_human_review": 86400, "re_review": 7200,
    "re_reviewing": 1800, "blocked": 3600,
}

def get_automation_state():
    """读取自动化控制状态"""
    state = {"running": True, "paused": False, "message": "运行中"}
    if CONTROL_FILE.exists():
        try:
            data = json.loads(CONTROL_FILE.read_text())
            state.update(data)
        except:
            pass
    return state

def set_automation_state(**updates):
    """写入自动化控制状态"""
    CONTROL_DIR.mkdir(parents=True, exist_ok=True)
    current = get_automation_state()
    current.update(updates)
    current["updated_at"] = datetime.now().isoformat()
    CONTROL_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2))
    # 如果 stopped，清理 NOTIFY 目录
    if current.get("running") == False:
        if NOTIFY_DIR.exists():
            for f in NOTIFY_DIR.iterdir():
                if f.is_file() and not f.name.startswith("."):
                    try: f.unlink()
                    except: pass
    return current

def discover_projects():
    """发现所有 kanban 项目（.kanban/*.db）"""
    projects = []
    if KANBAN_DIR.exists():
        for f in sorted(KANBAN_DIR.iterdir()):
            if f.suffix == ".db":
                projects.append({"name": f.stem, "path": str(f)})
    if not projects:
        projects = [{"name": default_project, "path": str(KANBAN_DIR / f"{default_project}.db")}]
    return projects

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DocProductionReview 看板</title>
<style>
:root{--bg:#0d1117;--card:#161b22;--border:#30363d;--text:#e6edf3;--dim:#8b949e;--green:#3fb950;--red:#f85149;--yellow:#d29922;--blue:#58a6ff;--purple:#bc8cff;--orange:#d4760a;--pink:#f778ba}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:14px;padding:20px}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;gap:16px;flex-wrap:wrap}
.header h1{font-size:22px}
.header-controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.header-controls select,.ctrl-btn{background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:6px 10px;font-size:13px;cursor:pointer}
.ctrl-btn:hover{border-color:var(--blue)}
.ctrl-btn.active{background:var(--green);border-color:var(--green);color:#fff}
.ctrl-btn.paused{background:var(--yellow);border-color:var(--yellow)}
.ctrl-btn.stopped{background:var(--red);border-color:var(--red)}
.updated{font-size:12px;color:var(--dim)}
/* 告警 -> 放在看板上面 */
.alerts-section{margin-bottom:16px}
.alerts-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.alerts-header span{font-size:14px;font-weight:600}
.alerts-header button{background:none;border:1px solid var(--border);color:var(--dim);padding:2px 8px;border-radius:4px;font-size:11px;cursor:pointer}
.alerts-header button:hover{color:var(--text)}
.alerts{display:flex;flex-wrap:wrap;gap:6px}
.alert-item{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--yellow);padding:6px 10px;border-radius:4px;font-size:12px;flex:1;min-width:200px}
.alert-item .time{color:var(--dim);margin-right:8px}
/* 看板 */
.board{display:flex;gap:12px;overflow-x:auto;padding-bottom:12px;margin-bottom:16px}
.column{min-width:200px;max-width:280px;flex-shrink:0;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px}
.column-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;font-size:12px;color:var(--dim);text-transform:uppercase;letter-spacing:0.5px}
.column-header .help-icon{display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:var(--border);color:var(--dim);font-size:10px;font-weight:700;cursor:pointer;margin-left:4px;flex-shrink:0;line-height:16px}
.column-header .help-icon:hover{background:var(--blue);color:#fff}
.column-count{background:var(--border);padding:1px 8px;border-radius:10px;font-size:11px}
/* 组合列上下分区 */
.combined-section{margin-bottom:8px}
.combined-section:last-child{margin-bottom:0}
/* 卡片 */
.card{background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:10px;margin-bottom:8px;cursor:pointer;transition:border-color .2s;position:relative}
.card-title{font-size:13px;font-weight:500;margin-bottom:6px}
.file-path{display:inline-block;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:bottom}
.card-meta{font-size:11px;color:var(--dim);display:flex;gap:8px;flex-wrap:wrap;word-break:break-all;overflow-wrap:break-word;min-width:0;max-width:100%}
.tag{display:inline-block;padding:1px 6px;border-radius:4px;font-size:10px;font-weight:600}
.tag-writer{background:#1f6feb33;color:#58a6ff}
.tag-reviewer{background:#bc8cff33;color:#bc8cff}
.tag-liufeng{background:#f778ba33;color:#f778ba}
.tag-dim{background:#30363d33;color:#8b949e;opacity:0.6}
.badges{margin-top:4px;display:flex;gap:4px;flex-wrap:wrap}
.iteration-badge{display:inline-block;padding:1px 6px;border-radius:4px;font-size:10px;background:var(--orange);color:#fff}
.level-row{display:flex;gap:12px;margin-top:6px;font-size:11px;flex-wrap:wrap}
.level-item{display:flex;align-items:center;gap:4px}
.level-dot{display:inline-block;width:6px;height:6px;border-radius:50%}
.level-dot-done{background:var(--green)}
.level-dot-working{background:var(--orange)}
.level-dot-queued{background:var(--dim)}
/* 质量评分 */
.score-row{display:flex;gap:8px;margin-top:4px;font-size:10px;flex-wrap:wrap}
.score-item{background:var(--card);padding:1px 5px;border-radius:3px}
.score-good{color:var(--green)}
.score-warn{color:var(--yellow)}
.score-bad{color:var(--red)}
/* 计时器 */
.timer{font-size:11px;margin-top:6px;display:flex;flex-direction:column;align-items:flex-start;gap:2px}
.timer-row{display:flex;justify-content:space-between;align-items:center;width:100%}
.timer-stale{color:var(--yellow);font-weight:600}
.card-workflow-status{font-size:10px;font-weight:600;margin-bottom:4px;padding:1px 6px;border-radius:4px;display:inline-block}
.card-running{color:var(--green);background:#3fb95022}
.card-stopped{color:var(--red);background:#f8514933}
.transition-banner{background:#1f6feb33;border:1px solid #1f6feb66;border-radius:4px;color:#58a6ff;font-size:11px;padding:4px 8px;margin-top:6px;text-align:center;animation:pulse-blue 1s ease-in-out infinite}
.transition-banner .transition-countdown{display:inline-block;background:#1f6feb;color:#fff;border-radius:50%;width:18px;height:18px;line-height:18px;text-align:center;font-size:11px;font-weight:700;margin-left:4px}
@keyframes pulse-blue{0%,100%{opacity:1}50%{opacity:0.6}}
.timer-ok{color:var(--dim)}
.timer-reason{font-size:10px;color:var(--red);line-height:1.3}
/* Modal */
.modal-overlay{display:none;position:fixed;z-index:1000;left:0;top:0;width:100%;height:100%;background:rgba(0,0,0,0.7);overflow-y:auto}
.modal-content{background:var(--card);margin:5% auto;padding:24px;width:85%;max-width:1000px;border-radius:8px;border:1px solid var(--border);position:relative}
.modal-close{position:absolute;right:16px;top:12px;font-size:24px;cursor:pointer;color:var(--dim)}
.modal-close:hover{color:var(--text)}
.modal-title{font-size:16px;font-weight:600;margin-bottom:8px;padding-right:40px}
.modal-path{font-size:11px;color:var(--dim);margin-bottom:12px;word-break:break-all}
.modal-body{background:var(--bg);padding:16px;border-radius:6px;font-family:'SF Mono','Consolas',monospace;font-size:12px;white-space:pre-wrap;word-break:break-all;max-height:50vh;overflow-y:auto;line-height:1.6}
/* 人工审核操作栏 */
.human-actions{border-top:1px solid var(--border);margin-top:16px;padding-top:16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.human-actions button{padding:6px 16px;border-radius:6px;border:none;font-size:13px;font-weight:600;cursor:pointer}
.btn-pass{background:var(--green);color:#fff}
.btn-fail{background:var(--red);color:#fff}
.btn-fail:hover{opacity:.9}
.btn-pass:hover{opacity:.9}
.human-input{flex:1;min-width:200px}
.human-input textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:4px;padding:8px;color:var(--text);font-size:12px;resize:vertical;min-height:50px}
.human-input textarea:focus{outline:none;border-color:var(--blue)}
/* 已阻塞 */
.blocked-actions{margin-top:12px;display:flex;gap:8px;flex-wrap:wrap}
.blocked-actions button{padding:6px 12px;border:1px solid var(--border);border-radius:6px;background:var(--card);color:var(--text);cursor:pointer;font-size:12px}
.blocked-actions button:hover{background:var(--green);color:#000}
/* 空状态 */
.empty{color:var(--dim);font-size:13px;padding:20px;text-align:center}
.profiles{display:flex;gap:12px;margin-bottom:16px}
.profile-card{flex:1;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px}
.profile-card h3{font-size:14px;margin-bottom:4px}
.profile-card .model{font-size:11px;color:var(--dim);margin-bottom:4px}
.profile-card .status{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600}
.status-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.section-title{font-size:15px;font-weight:600;margin:16px 0 10px;color:var(--text)}
.reports{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:8px;margin-bottom:16px}
.report-item{background:var(--card);border:1px solid var(--border);padding:8px 10px;border-radius:6px;font-size:12px}
.report-item .name{font-weight:500}
.report-item .time{color:var(--dim);font-size:11px}
.watcher-section{margin-bottom:16px}
.watcher-row{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:10px 12px;margin-bottom:4px;display:flex;align-items:center;gap:16px;font-size:13px}
.watcher-row .label{color:var(--dim);min-width:100px}
.stale{color:var(--red);font-weight:600}
.ok{color:var(--green)}
</style>
</head>
<body>

<div class="header">
  <h1>DocProductionReview 看板</h1>
  <div class="header-controls">
    <span class="updated" id="updated">加载中...</span>
    <label>
      <span style="font-size:12px;color:var(--dim);margin-right:4px">项目</span>
      <select id="projectSelect" onchange="switchProject(this.value)"></select>
    </label>

  </div>
</div>

<div class="profiles" id="profiles">
  <div class="profile-card"><h3>Writer (yaya)</h3><div class="model">—</div><div class="status">检查中...</div></div>
  <div class="profile-card"><h3>Reviewer (yaya-reviewer)</h3><div class="model">—</div><div class="status">检查中...</div></div>
  <div class="profile-card"><h3>Watcher (yaya-watcher)</h3><div class="model">—</div><div class="status">检查中...</div></div>
</div>

<div class="watcher-section" id="watcher">
  <div class="watcher-row"><span class="label">fswatch 心跳</span><span>检查中...</span></div>
  <div class="watcher-row"><span class="label">自动化状态</span><span id="autoState">检查中...</span></div>
</div>



<div class="section-title" style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
  <span>看板</span>
  <span style="font-size:12px;font-weight:400;color:var(--dim)">
    <button class="ctrl-btn" id="ctrlStart" onclick="controlAutomation('start')" title="开始">▶ 开始</button>
    <button class="ctrl-btn" id="ctrlStop" onclick="controlAutomation('stop')" title="停止">⏹ 停止</button>
  </span>
  <div id="stopHint" style="display:none;margin-top:4px;font-size:12px;color:var(--yellow)">修改已停止，如果想继续修改，请点击「开始」按钮</div>
</div>
<div class="board" id="board"></div>

<!-- 告警移看板下面 -->
<div class="alerts-section">
  <div class="alerts-header">
    <span>⚠ 告警日志</span>
    <button onclick="document.getElementById('alerts').innerHTML='<div class=empty>暂无告警</div>'">清空</button>
  </div>
  <div class="alerts" id="alerts"></div>
</div>

<div class="section-title">审查报告</div>
<div class="reports" id="reports"></div>

<!-- 文档预览 Modal -->
<div id="docModal" class="modal-overlay">
  <div class="modal-content">
    <span class="modal-close" onclick="closeDocModal()">&times;</span>
    <div class="modal-title" id="modalTitle" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
      <span id="modalTitleText"></span>
      <button class="ctrl-btn" onclick="copyDocContent()" title="一键复制全文" style="font-size:11px;padding:2px 8px">📋 复制</button>
      <button class="ctrl-btn" onclick="plainLanguage()" id="plainLangBtn" title="用大白话重新描述文档" style="font-size:11px;padding:2px 8px">🗣 大白话</button>
    </div>
    <div class="modal-path" id="modalPath"></div>
    <div class="modal-body" id="modalBody"></div>
    <!-- 大白话结果区域 -->
    <div id="plainLangSection" style="display:none;border-top:1px solid var(--border);margin-top:12px;padding-top:12px">
      <div style="font-size:13px;font-weight:600;color:var(--blue);margin-bottom:8px">🗣 大白话版本</div>
      <div class="modal-body" id="plainLangBody" style="max-height:40vh;background:var(--card);border:1px solid var(--border)"></div>
      <div style="margin-top:8px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <button class="btn-pass" onclick="plainLangFeedback('understood')" id="understoodBtn">😊 看懂了</button>
        <button class="btn-fail" onclick="plainLangFeedback('confused')" id="confusedBtn">🤔 还是没看懂</button>
        <span id="plainLangFeedback" style="font-size:12px;color:var(--dim);display:none"></span>
      </div>
    </div>
    <div id="modalActions" class="human-actions" style="display:none">
      <div id="humanReviewSimple" style="width:100%">
        <div style="margin-bottom:10px;font-size:13px;font-weight:600;color:var(--blue)">人工审核</div>
        <div style="display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap;margin-bottom:10px">
          <div class="human-input" style="flex:1">
            <textarea id="reviewComment" placeholder="输入您的评审意见或修改要求..." style="width:100%;min-height:60px"></textarea>
          </div>
        </div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <button class="btn-pass" onclick="humanReview('pass')">✔ 通过</button>
          <button class="btn-fail" onclick="humanReview('fail')">✘ 不通过</button>
          <button class="ctrl-btn" onclick="startHumanDialog()" style="color:var(--blue);border-color:var(--blue)">💬 对话评审</button>
        </div>
      </div>
      <div id="humanReviewDialog" style="width:100%;display:none">
        <div style="font-size:13px;font-weight:600;color:var(--purple);margin-bottom:10px">💬 与评审助手对话 — 沟通您的意见，达成共识后触发 Writer</div>
        <!-- 对话气泡区域 -->
        <div id="dialogHistory" style="margin-bottom:10px;max-height:320px;overflow-y:auto;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px;display:flex;flex-direction:column;gap:10px"></div>
        <!-- 输入区 -->
        <div style="display:flex;gap:8px;align-items:flex-start">
          <textarea id="dialogInput" placeholder="在此输入您的评审意见或问题..." style="flex:1;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px;color:var(--text);font-size:12px;resize:none;min-height:40px;max-height:80px"></textarea>
          <button onclick="sendDialogMessage()" style="height:40px;padding:0 16px;background:var(--purple);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600">发送</button>
        </div>
        <span id="dialogStatus" style="font-size:12px;color:var(--dim);display:none;margin-top:4px"></span>
        <!-- 确认操作区 -->
        <div id="consensusSection" style="display:none;margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
          <div style="font-size:13px;font-weight:600;color:var(--green);margin-bottom:8px">✅ 修改说明（可编辑）</div>
          <textarea id="consensusInstructions" placeholder="修改说明将发送给 Writer..." style="width:100%;min-height:60px;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px;color:var(--text);font-size:12px"></textarea>
          <div style="margin-top:8px;display:flex;gap:8px;align-items:center">
            <button class="btn-pass" onclick="confirmConsensus()">确认并触发 Writer</button>
            <button class="ctrl-btn" onclick="document.getElementById('consensusSection').style.display='none'" style="color:var(--dim)">继续对话</button>
          </div>
        </div>
      </div>
    </div>
    <div id="blockedActions" class="blocked-actions" style="display:none">
      <div id="blockedReasonText" style="margin-bottom:10px;padding:8px 10px;background:var(--bg);border:1px solid var(--border);border-radius:6px;font-size:13px;line-height:1.6;color:var(--text)"><strong>⚠️ 阻塞原因：</strong> <span id="blockedReasonValue">无</span></div>
      <div id="blockedAnalysis" style="margin-bottom:10px;padding:8px 10px;background:var(--card);border:1px solid var(--yellow);border-radius:6px;font-size:13px;line-height:1.6;color:var(--text)"><strong>📋 分析：</strong> <span id="blockedAnalysisText">加载中...</span></div>
      <div id="autoRecoveryStatus" style="margin-bottom:10px;padding:8px 10px;background:var(--bg);border:1px solid var(--green);border-radius:6px;font-size:13px;line-height:1.6;color:var(--green)"><strong>⚙️ 系统自动处理：</strong> <span id="autoRecoveryText">正在自动恢复...</span></div>
    </div>
    <div id="reviewerFeedback" class="reviewer-feedback" style="display:none;border-top:1px solid var(--border);margin-top:12px;padding-top:12px">
      <div style="font-size:13px;font-weight:600;color:var(--red);margin-bottom:8px">📋 复审不通过 — 需要修复的问题</div>
      <div id="reviewerFeedbackPcounts" style="margin-bottom:8px;font-size:12px"></div>
      <div id="reviewerFeedbackIssues" style="margin-bottom:8px"></div>
      <div id="reviewerFeedbackReport" style="font-size:12px;color:var(--dim)"></div>
    </div>
    <div id="autoRepairInfo" class="auto-repair-info" style="display:none;border-top:1px solid var(--border);margin-top:12px;padding-top:12px">
      <div style="padding:8px 10px;background:var(--card);border:1px solid var(--yellow);border-radius:6px;font-size:13px;line-height:1.6;color:var(--text)">
        <strong>自动修复状态：</strong>
        <span id="autoRepairAttemptsText">加载中...</span>
        <span id="autoRepairFailureText" style="display:none"><br/>最后一次失败原因：<span id="autoRepairFailureValue"></span></span>
      </div>
    </div>
    <!-- 用户操作区：滞卡任务处理 -->
    <div id="stuckActions" style="display:none;border-top:1px solid var(--border);margin-top:12px;padding-top:12px">
      <div style="font-size:13px;font-weight:600;color:var(--yellow);margin-bottom:8px">⚠️ 任务处理建议</div>
      <div id="stuckReasonDisplay" style="margin-bottom:10px;padding:8px 10px;background:var(--bg);border:1px solid var(--yellow);border-radius:6px;font-size:13px;line-height:1.6;color:var(--text)">
        <span id="stuckReasonText">加载中...</span>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
        <button class="ctrl-btn" onclick="retriggerTask()" style="background:var(--green);color:#fff;border-color:var(--green)" title="重新触发当前流程">↻ 重新触发</button>
        <button class="ctrl-btn" onclick="resetTaskToBacklog()" style="background:var(--orange);color:#fff;border-color:var(--orange)" title="退回待领取状态，Writer 将重新撰写">⏮ 退回待领取</button>
        <button class="ctrl-btn" onclick="markTaskBlocked()" style="background:var(--red);color:#fff;border-color:var(--red)" title="标记为阻塞，由系统自动恢复">⛔ 标记阻塞</button>
        <span id="stuckActionFeedback" style="font-size:12px;color:var(--dim);display:none"></span>
      </div>
    </div>
  </div>
</div>

<!-- 问号帮助 Modal -->
<div id="helpModal" class="modal-overlay">
  <div class="modal-content" style="max-width:600px">
    <span class="modal-close" onclick="closeHelpModal()">&times;</span>
    <div class="modal-title" id="helpModalTitle" style="font-size:16px;font-weight:600;margin-bottom:12px"></div>
    <div class="modal-body" id="helpModalBody" style="font-size:14px;font-family:inherit;white-space:normal;line-height:1.7;background:var(--card)"></div>
  </div>
</div>

<script>
let currentProject = "yaya-zhujiao";
let currentTaskId = null;

async function fetchJSON(url) {
  try { const r = await fetch(url); if (!r.ok) return null; return await r.json(); } catch { return null; }
}

function elapsedStr(iso) {
  if (!iso) return '';
  const t = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'));
  const secs = Math.floor((Date.now() - t.getTime()) / 1000);
  if (secs < 60) return secs + 's';
  if (secs < 3600) return Math.floor(secs/60) + 'm ' + (secs%60) + 's';
  const h = Math.floor(secs/3600);
  const m = Math.floor((secs%3600)/60);
  return h + 'h ' + m + 'm';
}

function scoreClass(s) { if (s===null||s===undefined) return ''; return s >= 80 ? 'score-good' : s >= 50 ? 'score-warn' : 'score-bad'; }
function translateReason(r) {
  const m = {
    'commit_failed': 'git 提交失败，可能是文件没有变化或 git 仓库异常',
    'self_check_failed': '文档自检未通过，存在 P0/P1 问题未修复',
    'max_iterations_exceeded': '超过最大修改迭代次数，需要人工判断是否继续',
    'unknown': '未知原因，需查看日志确认'
  };
  return m[r] || r;
}

function render() {
  document.getElementById('updated').textContent = '更新于 ' + new Date().toLocaleTimeString();
  // 项目列表
  fetchJSON('/api/projects').then(d => {
    const sel = document.getElementById('projectSelect');
    if (!d || !d.length) return;
    sel.innerHTML = d.map(p => `<option value="${p.name}" ${p.name===currentProject?'selected':''}>${p.name}</option>`).join('');
  });
  // 自动化状态
  fetchJSON('/api/automation/state').then(d => {
    const el = document.getElementById('autoState');
    if (!d) { el.textContent = '无法获取'; return; }
    let cls = d.running && !d.paused ? 'ok' : 'stale';
    let text = d.running ? (d.paused ? '已暂停' : '运行中') : '已停止';
    el.innerHTML = `<span class="${cls}">${text}</span>${d.message ? ' — '+d.message : ''}`;
  });
  // 控制按钮样式
  fetchJSON('/api/automation/state').then(d => {
    if (!d) return;
    document.getElementById('ctrlStart').className = 'ctrl-btn' + (d.running && !d.paused ? ' active' : '');
    document.getElementById('ctrlStop').className = 'ctrl-btn' + (!d.running ? ' stopped' : '');
    const stopHint = document.getElementById('stopHint');
    if (stopHint) stopHint.style.display = (!d.running) ? 'block' : 'none';
  });
  // profiles
  fetchJSON('/api/profiles').then(d => {
    if (!d) return;
    document.getElementById('profiles').innerHTML = d.map(p => {
      const st = p.workflow_state || (p.running ? 'running' : 'stopped');
      const colors = {running: 'var(--green)', paused: 'var(--yellow)', stopped: 'var(--red)'};
      const labels = {running: '运行中', paused: '已暂停', stopped: '已停止'};
      const c = colors[st] || 'var(--red)';
      return `<div class="profile-card"><h3>${p.role} (${p.name})</h3><div class="model">${p.model}</div><div class="status" style="color:${c}"><span class="status-dot" style="background:${c}"></span>${labels[st]||'已停止'}</div></div>`;
    }).join('');
  });
  // watcher
  fetchJSON('/api/watcher').then(d => {
    if (!d) return;
    const hb = d.heartbeat, st = d.started;
    let hbEl = '<span>未检测到心跳</span>';
    if (hb) {
      const secs = (Date.now() - new Date(hb.timestamp).getTime())/1000;
      const cls = secs>180 ? 'stale' : 'ok';
      hbEl = `<span class="${cls}">${hb.timestamp} (PID ${hb.pid}, ${Math.round(secs)}s 前)</span>`;
    }
    document.getElementById('watcher').innerHTML =
      `<div class="watcher-row"><span class="label">fswatch 心跳</span>${hbEl}</div>` +
      `<div class="watcher-row"><span class="label">自动化状态</span><span id="autoState2">检查中...</span></div>`;
  });
  // alerts
  fetchJSON('/api/alerts').then(d => {
    const el = document.getElementById('alerts');
    if (!d || d.length===0) { el.innerHTML = '<div class="empty">暂无告警</div>'; return; }
    el.innerHTML = d.map(a => `<div class="alert-item"><span class="time">${a.time}</span>${a.message}</div>`).join('');
  });
  // board
  fetchJSON('/api/board?project='+currentProject).then(d => {
    if (!d) return;
    document.getElementById('board').innerHTML = d.map(col => {
      if (col.type === 'combined') {
        return `<div class="column combined">
          <div class="column-header"><span>${col.label}<span class="help-icon" onclick="showHelp('${col.label}','${col.tooltip}')">?</span></span><span class="column-count">${col.total_count}</span></div>
          ${col.upper_count>0 ? '<div class="combined-section">' +
            col.upper_tasks.map(t => renderCard(t, col.upper_status)).join('') + '</div>' : ''}
          ${col.lower_count>0 ? '<div class="combined-section">' +
            col.lower_tasks.map(t => renderCard(t, col.lower_status)).join('') + '</div>' : ''}
        </div>`;
      }
      let css = col.extra_css||'';
      return `<div class="column${css}" style="${col.combined?'max-width:300px':''}">
        <div class="column-header"><span>${col.label}<span class="help-icon" onclick="showHelp('${col.label}','${col.tooltip}')">?</span></span><span class="column-count">${col.count}</span></div>
        ${col.count>0 ? col.tasks.map(t => renderCard(t, col.status)).join('') : ''}
      </div>`;
    }).join('');
  });
  // reports
  fetchJSON('/api/reports').then(d => {
    const el = document.getElementById('reports');
    if (!d || d.length===0) { el.innerHTML = '<div class="empty">暂无审查报告</div>'; return; }
    el.innerHTML = d.map(r => `<div class="report-item"><div class="name">${r.name}</div><div class="time">${r.time} · ${r.size} bytes</div></div>`).join('');
  });
}

function renderCard(t, status) {
  // P dots
  let pdots = '';
  if (t.p0_count !== undefined) {
    pdots = `<div class="level-row">
      <span class="level-item"><span class="level-dot level-dot-${t.p0_dot}"></span>P0:${t.p0_count}</span>
      <span class="level-item"><span class="level-dot level-dot-${t.p1_dot}"></span>P1:${t.p1_count}</span>
      <span class="level-item"><span class="level-dot level-dot-${t.p2_dot}"></span>P2:${t.p2_count}</span>
    </div>`;
  }
  // Quality score
  let scores = '';
  if (t.scores && t.scores.total != null && t.scores.total !== undefined) {
    scores = `<div class="score-row">
      <span class="score-item ${scoreClass(t.scores.compliance)}">合规:${t.scores.compliance??'-'}</span>
      <span class="score-item ${scoreClass(t.scores.ai_quality)}">AI质量:${t.scores.ai_quality??'-'}</span>
      <span class="score-item ${scoreClass(t.scores.defect_trend)}">缺陷:${t.scores.defect_trend??'-'}</span>
      <span class="score-item ${scoreClass(t.scores.total)}">总分:${t.scores.total??'-'}</span>
    </div>`;
  } else {
    scores = `<div class="score-row"><span class="score-item" style="color:var(--dim)">暂无评分</span></div>`;
  }
  // Auto-repair badge
  let repairBadge = '';
  if (t.auto_repair_attempts && t.auto_repair_attempts > 0) {
    const color = t.auto_repair_attempts >= 3 ? '#f0883e' : '#d29922';
    const bg = t.auto_repair_attempts >= 3 ? '#f0883e33' : '#d2992233';
    repairBadge = `<span class="tag" style="background:${bg};color:${color}">🔧 自动修复 ${t.auto_repair_attempts}/3</span>`;
  }
  return `<div class="card" onclick="openDoc('${t.id}','${status}' )">
    <div class="card-title">${t.title}</div>
    <div class="card-meta">
      <span class="file-path">${t.file_path||'—'}</span>
      ${(t.doc_version || t.version) ? '<span>'+(t.doc_version || t.version)+'</span>' : ''}
      ${['reviewing','awaiting_review','revision','re_reviewing','re_review'].includes(status)
        ? ('<span class="tag ' + (['awaiting_review','revision','re_review'].includes(status) ? 'tag-writer' : 'tag-dim') + '">writer</span>' +
           '<span class="tag ' + (['reviewing','re_reviewing'].includes(status) ? 'tag-reviewer' : 'tag-dim') + '">reviewer</span>')
        : (t.assigned_to ? '<span class="tag tag-'+t.assigned_to+'">'+t.assigned_to+'</span>' : '')}
    </div>
    <div class="badges">
      ${t.iteration>0 ? '<span class="iteration-badge">迭代'+t.iteration+'</span>' : ''}
      ${t.commit_sha ? '<span class="tag" style="background:#1f6feb33;color:#58a6ff">'+t.commit_sha.slice(0,7)+'</span>' : ''}
      ${repairBadge}
    </div>
    ${pdots}
    ${t.workflow_status === 'stopped' ? '<div class="card-workflow-status card-stopped">⏹ 已停止</div>' : '<div class="card-workflow-status card-running">▶ 进行中</div>'}
    ${scores}
    <div class="timer ${t.timer_stale?'timer-stale':'timer-ok'}">
      <div class="timer-row"><span>${t.elapsed ? '\u23f1 '+t.elapsed : ''}</span></div>
      ${t.stale ? `<div class="timer-reason">\u26a0 ${t.stale_reason}</div>` : ''}
      ${t.blocked_reason ? `<div class="timer-reason">\u26a0 ${translateReason(t.blocked_reason)}</div>` : ''}
    </div>
    ${t.transition_message ? `<div class="transition-banner" id="transition-${t.id}">\u25b6 ${t.transition_message} <span class="transition-countdown">5</span></div>` : ''}
  </div>`;
}

// human review dialog functions (top-level, called from openDoc)
function startHumanDialog() {
  document.getElementById('humanReviewSimple').style.display = 'none';
  document.getElementById('humanReviewDialog').style.display = 'block';
  document.getElementById('dialogHistory').innerHTML = '';
  document.getElementById('consensusSection').style.display = 'none';
  document.getElementById('dialogInput').value = '';
  addDialogMessage('system', 'Describe your review opinion, reviewer-P will analyze.', 'var(--dim)');
}

function closeHumanDialog() {
  document.getElementById('humanReviewSimple').style.display = 'block';
  document.getElementById('humanReviewDialog').style.display = 'none';
}

function addDialogMessage(sender, text, senderLabel) {
  const history = document.getElementById('dialogHistory');
  const msgDiv = document.createElement('div');
  if (sender === 'user') {
    msgDiv.style.cssText = 'display:flex;flex-direction:column;align-items:flex-end';
    const bubble = document.createElement('div');
    bubble.style.cssText = 'max-width:80%;background:#1f6feb;color:#fff;border-radius:12px 12px 4px 12px;padding:8px 12px;font-size:13px;line-height:1.5;white-space:pre-wrap;word-break:break-word';
    bubble.textContent = text;
    msgDiv.appendChild(bubble);
  } else if (sender === 'assistant') {
    msgDiv.style.cssText = 'display:flex;flex-direction:column;align-items:flex-start';
    const label = document.createElement('div');
    label.style.cssText = 'font-size:11px;color:var(--purple);font-weight:600;margin-bottom:2px;margin-left:4px';
    label.textContent = senderLabel || '评审助手';
    msgDiv.appendChild(label);
    const bubble = document.createElement('div');
    bubble.style.cssText = 'max-width:80%;background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:12px 12px 12px 4px;padding:8px 12px;font-size:13px;line-height:1.5;white-space:pre-wrap;word-break:break-word';
    bubble.textContent = text;
    msgDiv.appendChild(bubble);
  } else {
    // system messages — centered, muted
    msgDiv.style.cssText = 'display:flex;flex-direction:column;align-items:center';
    const bubble = document.createElement('div');
    bubble.style.cssText = 'max-width:90%;background:transparent;color:var(--dim);font-size:12px;padding:4px 8px;text-align:center;font-style:italic';
    bubble.textContent = text;
    msgDiv.appendChild(bubble);
  }
  history.appendChild(msgDiv);
  history.scrollTop = history.scrollHeight;
}

async function sendDialogMessage() {
  if (!currentTaskId) return;
  const input = document.getElementById('dialogInput');
  const opinion = input.value.trim();
  if (!opinion) return;

  addDialogMessage('user', opinion);
  input.value = '';
  input.style.height = '40px';

  const statusEl = document.getElementById('dialogStatus');
  statusEl.style.display = 'inline';
  statusEl.textContent = '⏳ 评审助手正在分析...';

  try {
    const r = await fetch('/api/human-review-dialog/' + currentTaskId, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({opinion: opinion, project: currentProject})
    });
    const data = await r.json();
    statusEl.style.display = 'none';

    if (data.success && data.content) {
      addDialogMessage('assistant', data.content);
      // Store latest analysis for consensus
      window._lastDialogAnalysis = data.content;
      if (!window._consensusAsked) {
        // Show the "confirm consensus" hint after first AI reply
        window._consensusAsked = true;
        const hint = document.createElement('div');
        hint.id = 'consensusHint';
        hint.style.cssText = 'text-align:center;margin-top:8px;font-size:12px;color:var(--dim)';
        hint.innerHTML = '如果您对分析满意，点击 <button class="ctrl-btn" onclick="showConsensusSection()" style="font-size:11px;padding:2px 8px">确认评审结果</button> 触发 Writer 修改';
        document.getElementById('humanReviewDialog').appendChild(hint);
      }
    } else {
      addDialogMessage('assistant', '分析失败: ' + (data.error || '未知错误'));
    }
  } catch(e) {
    statusEl.style.display = 'none';
    addDialogMessage('assistant', '请求失败: ' + e.message);
  }
}

function showConsensusSection() {
  document.getElementById('consensusSection').style.display = 'block';
  document.getElementById('consensusInstructions').value = window._lastDialogAnalysis || '';
  const hint = document.getElementById('consensusHint');
  if (hint) hint.style.display = 'none';
}

async function confirmConsensus() {
  if (!currentTaskId) return;
  const instructions = document.getElementById('consensusInstructions').value.trim();
  if (!instructions) { alert('Fill in modification instructions'); return; }

  const r = await fetch('/api/human-review-consensus/' + currentTaskId, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({instructions: instructions, project: currentProject})
  });
  const data = await r.json();
  if (data.success) {
    closeDocModal();
    render();
  } else {
    alert('Confirmation failed: ' + (data.error || 'unknown'));
  }
}



function openDoc(taskId, status) {
  currentTaskId = taskId;
  fetchJSON('/api/document/'+taskId+'?project='+currentProject).then(d => {
    if (!d || !d.found) { alert('文档不可用'); return; }
    document.getElementById('modalTitleText').textContent = d.title;
    document.getElementById('plainLangSection').style.display = 'none';
    document.getElementById('plainLangBtn').disabled = false;
    document.getElementById('plainLangBtn').textContent = '\uD83D\uDDE3 \u5927\u767d\u8bdd';
    document.getElementById('plainLangFeedback').style.display = 'none';
    document.getElementById('understoodBtn').style.display = 'inline-block';
    document.getElementById('confusedBtn').style.display = 'inline-block';
    document.getElementById('modalPath').textContent = d.file_path;
    document.getElementById('modalBody').textContent = d.content + (d.truncated ? '\n\n[文档截断]' : '');
    document.getElementById('docModal').style.display = 'block';
    // Show human review actions only for waiting_human_review
    const actionsEl = document.getElementById('modalActions');
    const blockedEl = document.getElementById('blockedActions');
    if (status === 'waiting_human_review') {
      // 对话框模式：AI 自动打招呼，用户直接对话
      actionsEl.style.display = '';
      document.getElementById('humanReviewSimple').style.display = 'none';
      document.getElementById('humanReviewDialog').style.display = 'block';
      document.getElementById('dialogHistory').innerHTML = '';
      document.getElementById('consensusSection').style.display = 'none';
      document.getElementById('dialogInput').value = '';
      window._lastDialogAnalysis = null;
      window._consensusAsked = false;
      const existingHint = document.getElementById('consensusHint');
      if (existingHint) existingHint.remove();
      // AI 自动发欢迎消息
      addDialogMessage('assistant', '您好！我是评审助手。请告诉我您对这份文档的评审意见，我会分析并给出修改建议。如果有任何问题需要讨论，我们可以在对话中逐步沟通。');
    } else {
      actionsEl.style.display = 'none';
    }
    // Show blocked recovery for blocked tasks - auto-recover
    if (status === 'blocked') {
      blockedEl.style.display = 'block';
      // 显示译后的原因和详细分析
      const reasonValEl = document.getElementById('blockedReasonValue');
      const analysisEl = document.getElementById('blockedAnalysisText');
      const autoEl = document.getElementById('autoRecoveryText');
      if (d.blocked_reason) {
        const r = d.blocked_reason;
        const cn = translateReason(r);
        reasonValEl.textContent = cn;
        // 详细分析
        if (r === 'commit_failed') {
          analysisEl.textContent = 'Writer 在完成文档撰写后尝试 git 提交时，.kanban/writer_state.json 中的文档内容版本没有变化。这可能是因为 Writer 在上次提交后没有实际修改文档内容，或者文档在撰写过程中未保存成功。系统将自动把文档推送到「修改中」状态，让 Writer 重新提交。';
        } else if (r === 'self_check_failed') {
          analysisEl.textContent = 'Writer 完成文档后执行自检流程时发现 P0（必须修复）或 P1（强烈建议修复）级别的问题。这些问题是系统在文档中包含的一致性检查规则中定义的，可能是概念引用错误、跨系统依赖缺失、术语使用不一致等。系统会自动将文档推送到「修改中」状态，并要求 Writer 逐一修复所有 P0/P1 问题后再提交。';
        } else if (r === 'max_iterations_exceeded') {
          analysisEl.textContent = '文档已经过多轮修改迭代（Writer→Reviewer 循环），仍然存在未解决问题。通常是因为 Reviewer 发现的深层问题需要重新设计文档结构，而非表面修改。系统会自动将文档推送到「待领取」状态，让 Writer 重新从头撰写。';
        } else {
          analysisEl.textContent = '发生了一个意外的系统异常，导致工作流中断。可能原因包括：git 仓库异常、数据库连接失败、或外部工具不可用。系统会自动将文档推送到「修改中」状态，让 Writer 重新尝试。';
        }
        // 自动恢复 - 根据原因选择合适的恢复策略
        autoEl.textContent = '正在自动恢复...';
        let target = 'revision';
        if (r === 'max_iterations_exceeded') target = 'backlog';
        fetch('/api/recover-blocked/'+currentTaskId, {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({target: target, project: currentProject})
        }).then(resp => resp.json()).then(data => {
          if (data.success) {
            autoEl.textContent = '✓ 已自动恢复：推送到「' + (target==='revision'?'修改中':'待领取') + '」状态，Writer 将在下一周期接收到修复任务。';
          } else {
            autoEl.textContent = '✗ 自动恢复失败：' + (data.error||'未知错误');
          }
        }).catch(e => {
          autoEl.textContent = '✗ 自动恢复请求失败：' + e.message;
        });
      }
    } else {
      blockedEl.style.display = 'none';
    }
    // Show auto-repair info for tasks in auto-repair mode
    const repairEl = document.getElementById('autoRepairInfo');
    const attemptsEl = document.getElementById('autoRepairAttemptsText');
    const failureEl = document.getElementById('autoRepairFailureText');
    const failureValEl = document.getElementById('autoRepairFailureValue');
    if (d.revision_data) {
      try {
        const rd = JSON.parse(d.revision_data);
        const a = rd.auto_repair_attempts || 0;
        if (a > 0) {
          repairEl.style.display = 'block';
          const f = rd.last_auto_repair_failure || '';
          if (a >= 3) {
            attemptsEl.textContent = a + '/3（已耗尽量试次数，将送审由 Reviewer 判断）';
            attemptsEl.style.color = '#f0883e';
          } else {
            attemptsEl.textContent = a + '/3（将自动重试）';
            attemptsEl.style.color = '#d29922';
          }
          if (f) {
            failureEl.style.display = 'inline';
            failureValEl.textContent = f;
          } else {
            failureEl.style.display = 'none';
          }
        } else {
          repairEl.style.display = 'none';
        }
      } catch(e) {
        repairEl.style.display = 'none';
      }
    } else {
      repairEl.style.display = 'none';
    }
    // Show stuck actions for tasks that have been in same status too long
    const stuckEl = document.getElementById('stuckActions');
    const stuckReasonEl = document.getElementById('stuckReasonText');
    const statusList = ['drafting','awaiting_review','reviewing','revision','re_review','re_reviewing','waiting_human_review'];
    if (d.timer_stale && statusList.includes(status) && d.workflow_status !== 'stopped') {
          stuckEl.style.display = 'block';
          const reasonMap = {
            'drafting': 'Writer not completed for a long time. Retrigger or reset to backlog.',
            'awaiting_review': 'Reviewer not started. Retrigger reviewer.',
            'reviewing': 'Reviewer timeout. Retrigger reviewer.',
            'revision': 'Writer timeout. Retrigger writer or mark blocked.',
            're_review': 'Re-review timeout. Retrigger reviewer.',
            're_reviewing': 'Re-review stuck. Retrigger reviewer.',
            'waiting_human_review': 'Waiting for your review.',
          };
          stuckReasonEl.textContent = reasonMap[status] || 'Task stuck.';
          document.getElementById('stuckActionFeedback').style.display = 'none';
          
          // Per-status button rules
          const retriggerBtn = document.querySelector('#stuckActions .ctrl-btn[onclick*="retriggerTask"]');
          const resetBtn = document.querySelector('#stuckActions .ctrl-btn[onclick*="resetTaskToBacklog"]');
          const blockBtn = document.querySelector('#stuckActions .ctrl-btn[onclick*="markTaskBlocked"]');
          
          retriggerBtn.style.display = '';
          resetBtn.style.display = '';
          blockBtn.style.display = '';
          
          if (status === 'drafting') {
            // show all three
          } else if (status === 'awaiting_review' || status === 're_review') {
            // only retrigger
            resetBtn.style.display = 'none';
            blockBtn.style.display = 'none';
          } else if (status === 'reviewing' || status === 'revision' || status === 're_reviewing') {
            // retrigger + mark blocked
            resetBtn.style.display = 'none';
          }
        } else {
          stuckEl.style.display = 'none';
        }
    // Show reviewer feedback for tasks with audit data (re_review, revision, waiting_human_review)
    const reviewerEl = document.getElementById('reviewerFeedback');
    const pcountsEl = document.getElementById('reviewerFeedbackPcounts');
    const issuesEl = document.getElementById('reviewerFeedbackIssues');
    const reportEl = document.getElementById('reviewerFeedbackReport');
    if (d.revision_data && (status === 're_review' || status === 'revision' || status === 'waiting_human_review')) {
      try {
        const rd = JSON.parse(d.revision_data);
        const hasIssues = rd.issues && rd.issues.length > 0;
        const hasResult = rd.re_review_result;
        const p0 = rd.p0_count || 0;
        const p1 = rd.p1_count || 0;
        const p2 = rd.p2_count || 0;
        if (hasIssues && hasResult === 'fail') {
          reviewerEl.style.display = 'block';
          pcountsEl.innerHTML = `<span style="color:#f85149">P0: ${p0}</span> <span style="color:#d29922">P1: ${p1}</span> <span style="color:var(--dim)">P2: ${p2}</span>`;
          issuesEl.innerHTML = rd.issues.map((i, idx) => {
            const pri = i.priority || 'P2';
            const desc = i.description || '';
            const standard = i.standard || '';
            const priColor = pri === 'P0' ? '#f85149' : pri === 'P1' ? '#d29922' : 'var(--dim)';
            return '<div style="padding:6px 8px;margin-bottom:4px;background:var(--card);border:1px solid var(--border);border-radius:4px;font-size:12px;line-height:1.5">' +
              '<span style="color:' + priColor + ';font-weight:600">[' + pri + ']</span> ' +
              '<span>' + desc + '</span>' +
              (standard ? '<br/><span style="color:var(--dim);font-size:11px">规则：' + standard + '</span>' : '') +
              '</div>';
          }).join('');
          if (rd.report_path) {
            const fn = rd.report_path.split('/').pop() || rd.report_path;
            reportEl.innerHTML = '审计报告：<a href="' + rd.report_path + '" target="_blank" style="color:var(--blue)">' + fn + '</a>';
          } else {
            reportEl.innerHTML = '';
          }
        } else if (hasResult === 'pass') {
          reviewerEl.style.display = 'block';
          reviewerEl.querySelector('div:first-child').innerHTML = '✅ 复审通过 — 等待人工确认';
          reviewerEl.querySelector('div:first-child').style.color = '#3fb950';
          pcountsEl.innerHTML = '<span style="color:var(--green)">P0: 0 P1: 0 P2: 0</span> — 无问题';
          issuesEl.innerHTML = '';
          reportEl.innerHTML = '';
        } else {
          reviewerEl.style.display = 'none';
        }
      } catch(e) {
        reviewerEl.style.display = 'none';
      }
    } else {
      reviewerEl.style.display = 'none';
    }
  });
}

function closeDocModal() { document.getElementById('docModal').style.display = 'none'; currentTaskId = null; }
window.onclick = function(e) { if (e.target == document.getElementById('docModal')) closeDocModal(); };

function showHelp(name, text) {
  document.getElementById('helpModalTitle').textContent = name;
  document.getElementById('helpModalBody').textContent = text;
  document.getElementById('helpModal').style.display = 'block';
}
function closeHelpModal() { document.getElementById('helpModal').style.display = 'none'; }

// 一键复制
function copyDocContent() {
  const text = document.getElementById('modalBody').textContent;
  navigator.clipboard.writeText(text).then(() => {
    const btns = document.querySelectorAll('#modalTitle .ctrl-btn');
    for (let b of btns) {
      if (b.textContent.includes('\u{1F4CB}')) {
        const orig = b.textContent;
        b.textContent = '\u2705 \u5df2\u590d\u5236';
        setTimeout(() => b.textContent = orig, 2000);
        break;
      }
    }
  }).catch(() => alert('\u590d\u5236\u5931\u8d25\uff0c\u8bf7\u624b\u52a8\u9009\u4e2d\u5185\u5bb9\u590d\u5236'));
}

// 大白话
async function plainLanguage() {
  if (!currentTaskId) return;
  const btn = document.getElementById('plainLangBtn');
  btn.disabled = true;
  btn.textContent = '\u23f3 \u751f\u6210\u4e2d...';
  document.getElementById('plainLangFeedback').style.display = 'none';
  try {
    const r = await fetch('/api/plain-language/' + currentTaskId + '?project=' + currentProject);
    const data = await r.json();
    if (!data.success) { document.getElementById('plainLangBody').textContent = '\u274c \u751f\u6210\u5931\u8d25: ' + (data.error||'\u672a\u77e5\u9519\u8bef'); document.getElementById('plainLangSection').style.display = 'block'; btn.textContent = '\uD83D\uDDE3 \u5927\u767d\u8bdd'; btn.disabled = false; return; }
    document.getElementById('plainLangBody').textContent = data.content;
    document.getElementById('plainLangSection').style.display = 'block';
    document.getElementById('understoodBtn').style.display = 'inline-block';
    document.getElementById('confusedBtn').style.display = 'inline-block';
    btn.textContent = '\u2705 \u5df2\u751f\u6210';
  } catch(e) {
    alert('\u8bf7\u6c42\u5931\u8d25: ' + e.message);
    btn.textContent = '\uD83D\uDDE3 \u5927\u767d\u8bdd';
    btn.disabled = false;
  }
}

// 大白话反馈
async function plainLangFeedback(action) {
  if (!currentTaskId) return;
  document.getElementById('understoodBtn').style.display = 'none';
  document.getElementById('confusedBtn').style.display = 'none';
  const fb = document.getElementById('plainLangFeedback');
  fb.style.display = 'inline-block';
  if (action === 'understood') {
    fb.textContent = '\ud83d\ude0a \u5df2\u786e\u8ba4 \u2014 \u4f60\u770b\u61c2\u4e86\u5927\u767d\u8bdd\u63cf\u8ff0';
    fb.style.color = 'var(--green)';
    await fetch('/api/plain-language-feedback/' + currentTaskId, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({understood: true, project: currentProject})
    });
  } else {
    fb.style.color = 'var(--red)';
    fb.innerHTML = '\uD83E\uDD14 \u4f60\u89c9\u5f97\u54ea\u91cc\u6ca1\u8bf4\u6e05\u695a\uff1f<br><textarea id="confusedReason" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:4px;padding:6px;color:var(--text);font-size:12px;min-height:40px;margin-top:4px" placeholder="\u968f\u4fbf\u5199\uff0c\u6211\u4f1a\u53cd\u9988\u7ed9 Writer \u6539\u8fdb..."></textarea><button onclick="submitConfused()" style="margin-top:4px;padding:4px 10px;background:var(--blue);border:none;border-radius:4px;color:#fff;font-size:11px;cursor:pointer">\u63d0\u4ea4\u53cd\u9988</button>';
  }
}

async function submitConfused() {
  const reason = document.getElementById('confusedReason').value;
  await fetch('/api/plain-language-feedback/' + currentTaskId, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({understood: false, reason: reason, project: currentProject})
  });
  document.getElementById('plainLangFeedback').textContent = '\u2705 \u5df2\u53cd\u9988\uff0cWriter \u4f1a\u6539\u8fdb\u6587\u6863';
  document.getElementById('plainLangFeedback').style.color = 'var(--green)';
}


function switchProject(project) { currentProject = project; render(); }

async function controlAutomation(action) {
  const r = await fetchJSON('/api/automation/control?action='+action);
  if (r) render();
}

async function humanReview(action) {
  if (!currentTaskId) return;
  const comment = document.getElementById('reviewComment').value;
  const r = await fetch('/api/human-review/'+currentTaskId, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({action: action, comment: comment, project: currentProject})
  });
  const data = await r.json();
  closeDocModal();
  render();
  if (!data.success) alert('操作失败: '+data.error);
}

async function recoverBlocked(target) {
  if (!currentTaskId) return;
  const r = await fetch('/api/recover-blocked/'+currentTaskId, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({target: target, project: currentProject})
  });
  const data = await r.json();
  closeDocModal();
  render();
  if (!data.success) alert('恢复失败: '+data.error);
}

// 用户操作：重新触发当前任务
async function retriggerTask() {
  if (!currentTaskId) return;
  const fb = document.getElementById('stuckActionFeedback');
  fb.style.display = 'inline-block';
  fb.textContent = '⏳ 正在重触发...';
  fb.style.color = 'var(--yellow)';
  const r = await fetch('/api/retrigger-task/'+currentTaskId, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({project: currentProject})
  });
  const data = await r.json();
  if (data.success) {
    fb.textContent = '✅ 已发送重触发信号，等待处理...';
    fb.style.color = 'var(--green)';
    setTimeout(() => { closeDocModal(); render(); }, 1500);
  } else {
    fb.textContent = '❌ 触发失败: '+data.error;
    fb.style.color = 'var(--red)';
  }
}

// 用户操作：退回待领取
async function resetTaskToBacklog() {
  if (!currentTaskId) return;
  if (!confirm('确定要将此任务退回「待领取」状态吗？Writer 将重新撰写此文档。')) return;
  const fb = document.getElementById('stuckActionFeedback');
  fb.style.display = 'inline-block';
  fb.textContent = '⏳ 正在退回...';
  const r = await fetch('/api/reset-task-backlog/'+currentTaskId, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({project: currentProject})
  });
  const data = await r.json();
  if (data.success) {
    fb.textContent = '✅ 已退回待领取';
    fb.style.color = 'var(--green)';
    setTimeout(() => { closeDocModal(); render(); }, 1500);
  } else {
    fb.textContent = '❌ 退回失败: '+data.error;
    fb.style.color = 'var(--red)';
  }
}

// 用户操作：标记阻塞
async function markTaskBlocked() {
  if (!currentTaskId) return;
  if (!confirm('确定要将此任务标记为「已阻塞」吗？系统将自动尝试恢复。')) return;
  const fb = document.getElementById('stuckActionFeedback');
  fb.style.display = 'inline-block';
  fb.textContent = '⏳ 正在标记...';
  const r = await fetch('/api/mark-task-blocked/'+currentTaskId, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({project: currentProject})
  });
  const data = await r.json();
  if (data.success) {
    fb.textContent = '✅ 已标记为阻塞，系统将自动恢复';
    fb.style.color = 'var(--green)';
    setTimeout(() => { closeDocModal(); render(); }, 2000);
  } else {
    fb.textContent = '❌ 标记失败: '+data.error;
    fb.style.color = 'var(--red)';
  }
}

render();
setInterval(render, 10000);

// 过渡提示倒计时：扫描所有 transition-banner，启动 5 秒倒计时
let _transitionTimers = {};
function startTransitionCountdowns() {
  const banners = document.querySelectorAll('.transition-banner');
  banners.forEach(b => {
    const id = b.id;
    if (_transitionTimers[id]) return; // 已有计时器，不重复创建
    const countdownEl = b.querySelector('.transition-countdown');
    if (!countdownEl) return;
    let sec = 5;
    _transitionTimers[id] = setInterval(() => {
      sec--;
      if (sec <= 0) {
        clearInterval(_transitionTimers[id]);
        delete _transitionTimers[id];
        const el = document.getElementById(id);
        if (el) el.remove();
      } else {
        if (countdownEl) countdownEl.textContent = sec;
      }
    }, 1000);
  });
}
// 每次 render() 后执行
const _origRender = render;
render = function() { _origRender(); startTransitionCountdowns(); };
</script>
</body>
</html>"""

# ===================== API =====================

@app.get("/")
async def root():
    return HTMLResponse(HTML)

@app.get("/api/projects")
async def api_projects():
    return JSONResponse(discover_projects())

@app.get("/api/profiles")
async def api_profiles():
    profiles_info = [
        {"name": "yaya", "role": "Writer"},
        {"name": "yaya-reviewer", "role": "Reviewer"},
        {"name": "yaya-watcher", "role": "Watcher"},
    ]
    # 读取自动化控制状态
    auto = get_automation_state()
    auto_running = auto.get("running", True)
    auto_paused = auto.get("paused", False)
    # 扫描所有 hermes gateway / hermes chat 进程
    r = subprocess.run(["ps", "aux"], capture_output=True, text=True)
    all_procs = r.stdout
    for p in profiles_info:
        cfg_path = HERMES_HOME / p["name"] / "config.yaml"
        p["model"] = "—"
        p["running"] = False
        if cfg_path.exists():
            content = cfg_path.read_text()
            m = re.search(r"default:\s*(\S+)", content)
            if not m:
                m = re.search(r"model:\s*(\S+)", content)
            if m:
                p["model"] = m.group(1)
        # 如果工作流已停止，Profiles 状态跟随工作流，不看进程
        if not auto_running:
            p["running"] = False
            p["workflow_state"] = "stopped"
            continue
        if auto_paused:
            p["running"] = False
            p["workflow_state"] = "paused"
            continue
        # 工作流运行中：检测进程是否存活
        if p["name"] in all_procs and ("gateway" in all_procs or "hermes" in all_procs):
            for line in all_procs.split("\n"):
                if p["name"] in line and ("hermes" in line or "gateway" in line):
                    p["running"] = True
                    break
        if not p["running"]:
            lr = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
            if f"hermes.{p['name']}" in lr.stdout:
                p["running"] = True
        p["workflow_state"] = "running" if p["running"] else "stopped"
    return JSONResponse(profiles_info)

@app.get("/api/watcher")
async def api_watcher():
    heartbeat, started = None, None
    hb_path = KANBAN_DIR / "watcher_heartbeat_yaya-zhujiao.json"
    st_path = KANBAN_DIR / "watcher_started_yaya-zhujiao.json"
    if hb_path.exists():
        try: heartbeat = json.loads(hb_path.read_text())
        except: pass
    if st_path.exists():
        try: started = json.loads(st_path.read_text())
        except: pass
    return JSONResponse({"heartbeat": heartbeat, "started": started})

@app.get("/api/alerts")
async def api_alerts():
    alerts = []
    if ALERTS_DIR.exists():
        files = sorted(ALERTS_DIR.iterdir(), reverse=True)[:50]
        for f in files:
            try: content = f.read_text().strip()
            except: content = ""
            parts = content.split("\n", 1)
            time = parts[0] if parts else f.name
            msg = parts[1] if len(parts) > 1 else ""
            alerts.append({"time": time, "message": msg, "file": f.name})
    return JSONResponse(alerts)

@app.get("/api/board")
async def api_board(project: str = default_project):
    db_path = KANBAN_DIR / f"{project}.db"
    columns = []
    if not db_path.exists():
        for key, label, combined, statuses, tooltip in KANBAN_LAYOUT:
            columns.append({"status": key, "label": label, "count": 0, "tasks": [], "tooltip": tooltip,
                            "type": "combined" if combined else "single"})
        return JSONResponse(columns)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        auto_state = get_automation_state()
        auto_stopped = not auto_state.get("running", True)

        # 自动恢复所有阻塞任务（阻塞超过 30 秒的）
        auto_recovered = []
        try:
            blocked_rows = conn.execute("SELECT * FROM tasks WHERE status='blocked'").fetchall()
            for br in blocked_rows:
                bd = dict(br)
                reason = bd.get("blocked_reason", "")
                # 只恢复进入阻塞状态超过 30 秒的任务，避免刚进去就恢复
                entered = bd.get("status_entered_at")
                auto_recover = False
                if entered:
                    try:
                        et = datetime.fromisoformat(entered)
                        nt = datetime.fromisoformat(now_iso)
                        if (nt - et).total_seconds() > 30:
                            auto_recover = True
                    except:
                        auto_recover = True
                else:
                    auto_recover = True
                if not auto_recover:
                    continue
                # 根据原因选择恢复目标
                target = "backlog" if reason == "max_iterations_exceeded" else "revision"
                update_task_status(project, bd["id"], target, validate=False)
                add_comment(project, bd["id"], "system",
                    f"系统自动恢复阻塞：阻塞原因[{reason}]，已推送到{target}")
                # 通知 Writer
                notify_path = NOTIFY_DIR / f"writer-{project}"
                NOTIFY_DIR.mkdir(parents=True, exist_ok=True)
                notify_path.write_text(
                    f"auto-recover blocked {bd['id']} to {target} at {now_iso}")
                auto_recovered.append({"id": bd["id"], "title": bd["title"],
                    "reason": reason, "target": target})
        except Exception as e:
            auto_recovered = [{"error": str(e)}]

        # 提前加载评分
        scores_by_task = {}
        try:
            rows = conn.execute("SELECT task_id, total_score, compliance_score, ai_quality_score, defect_trend_score FROM quality_scores ORDER BY id DESC").fetchall()
            for r in rows:
                tid = r["task_id"]
                if tid not in scores_by_task:
                    scores_by_task[tid] = {
                        "total": r["total_score"],
                        "compliance": r["compliance_score"],
                        "ai_quality": r["ai_quality_score"],
                        "defect_trend": r["defect_trend_score"],
                    }
        except:
            pass

        for key, label, combined, statuses, tooltip in KANBAN_LAYOUT:
            if combined:
                upper_statuses = [statuses[0]]
                lower_statuses = list(statuses[1:]) if len(statuses) > 1 else []
                # Section labels per column
                section_labels = {
                    "review_modify": ("审查中", "待审查 / 修改中"),
                    "re_review_modify": ("复审中", "复审不通过，等待修改"),
                }
                upper_label, lower_label = section_labels.get(key, ("上栏", "下栏"))

                # Upper section: fetch tasks for each upper status
                upper_rows = []
                for s in upper_statuses:
                    upper_rows.extend(conn.execute(
                        "SELECT * FROM tasks WHERE status=? ORDER BY updated_at ASC", (s,)
                    ).fetchall())

                # Lower section: fetch tasks for each lower status
                lower_rows = []
                for s in lower_statuses:
                    lower_rows.extend(conn.execute(
                        "SELECT * FROM tasks WHERE status=? ORDER BY updated_at ASC", (s,)
                    ).fetchall())

                def build_task(r, status):
                    d = dict(r)
                    elapsed, timer_stale = calc_elapsed(d.get("status_entered_at"), now_iso, status)
                    p0_dot, p1_dot, p2_dot = calc_pdots(d, status)
                    rr = ""
                    rev_data = {}
                    if d.get("revision_data"):
                        try: rev_data = json.loads(d["revision_data"])
                        except: pass
                    rr = rev_data.get("re_review_result", "")
                    auto_repair_attempts = rev_data.get("auto_repair_attempts", 0)
                    auto_repair_failure = rev_data.get("last_auto_repair_failure", "")
                    # 计算卡住原因
                    stale = False
                    stale_reason = ""
                    if timer_stale:
                        stale = True
                        reas = {
                            "drafting": "Writer 长时间未完成撰写，可能已中断",
                            "awaiting_review": "Reviewer 长时间未启动审核，可能任务漏触发",
                            "reviewing": "Reviewer 审核超时，可能已中断",
                            "revision": "Writer 修改超时，可能已中断或自动修复循环",
                            "re_review": "复审超时，可能 Reviewer 未正常处理",
                            "re_reviewing": "复审中长时间未响应，可能已中断",
                            "waiting_human_review": "等待人工审核超时（您可能需要查看）",
                            "blocked": "任务已阻塞，需手动处理",
                        }
                        stale_reason = reas.get(status, "未知状态超时")
                    # 工作流状态（不设卡住原因，由外部展示）
                    workflow_status = "stopped" if (auto_stopped and status not in ('finalized', 'blocked', 'backlog')) else "running"
                    # 停止时不报 timer 错误（已在卡片顶部显示"已停止"状态）
                    if workflow_status == "stopped":
                        stale = False
                        stale_reason = ""
                    # 计算过渡提示（状态进入 < 10 秒时显示）
                    transition_message = ""
                    if d.get("status_entered_at"):
                        try:
                            et = datetime.fromisoformat(d["status_entered_at"])
                            nt = datetime.fromisoformat(now_iso)
                            if (nt - et).total_seconds() < 10:
                                prev = d.get("previous_status", "")
                                if prev:
                                    tmap = {
                                        ("revision", "re_review"): "修改已完成，5秒后进入复审+修改环节",
                                        ("drafting", "awaiting_review"): "撰写已完成，5秒后进入审查+修改环节",
                                        ("reviewing", "revision"): "审查不通过，5秒钟后进入修改阶段",
                                        ("reviewing", "waiting_human_review"): "审查通过，5秒钟后进入人工审核环节",
                                        ("re_reviewing", "revision"): "复审不通过，5秒钟后进入修改阶段",
                                        ("re_reviewing", "waiting_human_review"): "复审通过，5秒钟后进入人工审核环节",
                                        ("waiting_human_review", "finalized"): "人工审核通过，5秒钟后封版",
                                        ("waiting_human_review", "re_review"): "人工审核不通过，5秒钟后进入复审+修改环节",
                                    }
                                    transition_message = tmap.get((prev, status), "")
                        except:
                            pass
                    return {
                        "id": d["id"], "title": d["title"], "file_path": d.get("file_path",""),
                        "version": d.get("version"), "doc_version": parse_doc_version_from_file(d.get("file_path","")), "assigned_to": d.get("assigned_to",""),
                        "commit_sha": d.get("commit_sha",""),
                        "iteration": d.get("iteration_count",0) or 0,
                        "elapsed": elapsed, "timer_stale": timer_stale,
                        "stale": stale, "stale_reason": stale_reason,
                        "blocked_reason": d.get("blocked_reason",""),
                        "p0_count": d.get("p0_count",0) or 0,
                        "p1_count": d.get("p1_count",0) or 0,
                        "p2_count": d.get("p2_count",0) or 0,
                        "p0_dot": p0_dot, "p1_dot": p1_dot, "p2_dot": p2_dot,
                        "re_review_result": rr,
                        "scores": scores_by_task.get(d["id"]),
                        "transition_message": transition_message,
                        "auto_repair_attempts": auto_repair_attempts,
                        "auto_repair_failure": auto_repair_failure,
                        "workflow_status": workflow_status,
                    }

                upper_tasks = [build_task(r, r["status"]) for r in upper_rows]
                lower_tasks = [build_task(r, r["status"]) for r in lower_rows]
                columns.append({
                    "status": key, "label": label, "tooltip": tooltip,
                    "type": "combined", "total_count": len(upper_tasks) + len(lower_tasks),
                    "upper_count": len(upper_tasks), "upper_status": upper_statuses[0] if upper_statuses else None,
                    "upper_label": upper_label,
                    "upper_tasks": upper_tasks,
                    "lower_count": len(lower_tasks), "lower_status": lower_statuses[0] if lower_statuses else None,
                    "lower_label": lower_label,
                    "lower_tasks": lower_tasks,
                })
            else:
                status = statuses[0]
                rows = conn.execute(
                    "SELECT * FROM tasks WHERE status=? ORDER BY updated_at ASC", (status,)
                ).fetchall()
                tasks = []
                for r in rows:
                    d = dict(r)
                    elapsed, timer_stale = calc_elapsed(d.get("status_entered_at"), now_iso, status)
                    p0_dot, p1_dot, p2_dot = calc_pdots(d, status)
                    rev_data = {}
                    if d.get("revision_data"):
                        try: rev_data = json.loads(d["revision_data"])
                        except: pass
                    auto_repair_attempts = rev_data.get("auto_repair_attempts", 0)
                    auto_repair_failure = rev_data.get("last_auto_repair_failure", "")
                    # 计算卡住原因
                    stale = False
                    stale_reason = ""
                    if timer_stale:
                        stale = True
                        reas = {
                            "drafting": "Writer 长时间未完成撰写，可能已中断",
                            "awaiting_review": "Reviewer 长时间未启动审核，可能任务漏触发",
                            "reviewing": "Reviewer 审核超时，可能已中断",
                            "revision": "Writer 修改超时，可能已中断或自动修复循环",
                            "re_review": "复审超时，可能 Reviewer 未正常处理",
                            "re_reviewing": "复审中长时间未响应，可能已中断",
                            "waiting_human_review": "等待人工审核超时（您可能需要查看）",
                            "blocked": "任务已阻塞，需手动处理",
                        }
                        stale_reason = reas.get(status, "未知状态超时")
                    # 工作流状态（不设卡住原因，由外部展示）
                    workflow_status = "stopped" if (auto_stopped and status not in ('finalized', 'blocked', 'backlog')) else "running"
                    # 停止时不报 timer 错误（已在卡片顶部显示"已停止"状态）
                    if workflow_status == "stopped":
                        stale = False
                        stale_reason = ""
                    # 计算过渡提示（状态进入 < 10 秒时显示）
                    transition_message = ""
                    if d.get("status_entered_at"):
                        try:
                            et = datetime.fromisoformat(d["status_entered_at"])
                            nt = datetime.fromisoformat(now_iso)
                            if (nt - et).total_seconds() < 10:
                                prev = d.get("previous_status", "")
                                if prev:
                                    tmap = {
                                        ("revision", "re_review"): "修改已完成，5秒后进入复审+修改环节",
                                        ("drafting", "awaiting_review"): "撰写已完成，5秒后进入审查+修改环节",
                                        ("reviewing", "revision"): "审查不通过，5秒钟后进入修改阶段",
                                        ("reviewing", "waiting_human_review"): "审查通过，5秒钟后进入人工审核环节",
                                        ("re_reviewing", "revision"): "复审不通过，5秒钟后进入修改阶段",
                                        ("re_reviewing", "waiting_human_review"): "复审通过，5秒钟后进入人工审核环节",
                                        ("waiting_human_review", "finalized"): "人工审核通过，5秒钟后封版",
                                        ("waiting_human_review", "re_review"): "人工审核不通过，5秒钟后进入复审+修改环节",
                                    }
                                    transition_message = tmap.get((prev, status), "")
                        except:
                            pass
                    tasks.append({
                        "id": d["id"], "title": d["title"], "file_path": d.get("file_path",""),
                        "version": d.get("version"), "doc_version": parse_doc_version_from_file(d.get("file_path","")), "assigned_to": d.get("assigned_to",""),
                        "commit_sha": d.get("commit_sha",""),
                        "iteration": d.get("iteration_count",0) or 0,
                        "elapsed": elapsed, "timer_stale": timer_stale,
                        "stale": stale, "stale_reason": stale_reason,
                        "blocked_reason": d.get("blocked_reason",""),
                        "p0_count": d.get("p0_count",0) or 0,
                        "p1_count": d.get("p1_count",0) or 0,
                        "p2_count": d.get("p2_count",0) or 0,
                        "p0_dot": p0_dot, "p1_dot": p1_dot, "p2_dot": p2_dot,
                        "scores": scores_by_task.get(d["id"]),
                        "transition_message": transition_message,
                        "auto_repair_attempts": auto_repair_attempts,
                        "auto_repair_failure": auto_repair_failure,
                        "workflow_status": workflow_status,
                    })
                columns.append({
                    "status": status, "label": label, "tooltip": tooltip,
                    "type": "single", "count": len(tasks), "tasks": tasks,
                    "extra_css": "",
                })
    finally:
        conn.close()
    return JSONResponse(columns)

def calc_elapsed(status_entered_at, now_iso, status):
    if not status_entered_at:
        return "", False
    # 已封版不需要超时告警
    if status == 'finalized':
        try:
            et = datetime.fromisoformat(status_entered_at)
            nt = datetime.fromisoformat(now_iso)
            secs = (nt - et).total_seconds()
            if secs < 60:
                elapsed = f"{int(secs)}s"
            elif secs < 3600:
                elapsed = f"{int(secs//60)}m {int(secs%60)}s"
            else:
                h = int(secs // 3600)
                m = int((secs % 3600) // 60)
                elapsed = f"{h}h {m}m"
            return elapsed, False
        except:
            return "", False
    try:
        et = datetime.fromisoformat(status_entered_at)
        nt = datetime.fromisoformat(now_iso)
        secs = (nt - et).total_seconds()
        if secs < 60:
            elapsed = f"{int(secs)}s"
        elif secs < 3600:
            elapsed = f"{int(secs//60)}m {int(secs%60)}s"
        else:
            h = int(secs // 3600)
            m = int((secs % 3600) // 60)
            elapsed = f"{h}h {m}m"
        threshold = ALERT_SECONDS.get(status, 7200)
        return elapsed, secs > threshold
    except:
        return "", False

def calc_pdots(d, status):
    p0_dot, p1_dot, p2_dot = "done", "done", "done"
    if status == "revision":
        if (d.get("p0_count",0) or 0) > 0: p0_dot = "queued"
        if (d.get("p1_count",0) or 0) > 0: p1_dot = "queued"
        if (d.get("p2_count",0) or 0) > 0: p2_dot = "queued"
        rev_data = {}
        if d.get("revision_data"):
            try: rev_data = json.loads(d["revision_data"])
            except: pass
        if rev_data.get("human_feedback"):
            p0_dot, p1_dot, p2_dot = "working", "working", "working"
    return p0_dot, p1_dot, p2_dot


def parse_doc_version_from_file(file_path):
    """Read the latest version from a document's changelog section."""
    if not file_path or not os.path.isfile(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Step 1: find the changelog header
        in_changelog = False
        found_separator = False
        for i, line in enumerate(lines):
            stripped = line.rstrip()
            if stripped.startswith("## 变更记录"):
                in_changelog = True
                continue
            if not in_changelog:
                continue
            # Step 2: skip the table header row (|版本|日期|...|)
            if stripped.startswith("|") and not stripped.startswith("|--") and not found_separator:
                continue
            # Step 3: find the separator row (|---|---|---|)
            if stripped.startswith("|--"):
                found_separator = True
                continue
            # Step 4: first data row after separator
            if found_separator and stripped.startswith("|"):
                # Extract the first cell (|vX.Y|...|)
                parts = stripped.split("|")
                if len(parts) >= 2:
                    version = parts[1].strip()
                    if version.startswith("v"):
                        return version
                break
        # Fallback: parse from title "# Sxx xxx vX.X"
        first_line = lines[0].strip() if lines else ""
        m2 = re.search(r"v[\d.]+", first_line)
        if m2:
            return m2.group(0)
        return None
    except Exception:
        return None


@app.get("/api/document/{task_id}")
async def api_document(task_id: str, project: str = default_project):
    sys.path.insert(0, str(PROJECT_ROOT))
    from kanban_ops import get_document_content, get_task  # noqa
    task = get_task(project, task_id)
    result = get_document_content(task_id, project)
    if task:
        result["blocked_reason"] = task.get("blocked_reason", "")
        result["revision_data"] = task.get("revision_data", "")
        # 计算 timer_stale
        status = task.get("status", "")
        entered = task.get("status_entered_at", "")
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        _, timer_stale = calc_elapsed(entered, now_iso, status)
        result["timer_stale"] = timer_stale
        # pass workflow_status for frontend stopped check
        auto_state = get_automation_state()
        status_val = task.get("status", "")
        result["workflow_status"] = "stopped" if (not auto_state.get("running", True) and status_val not in ("finalized", "blocked", "backlog")) else "running"
        # Parse version from document file changelog (source of truth)
        result["doc_version"] = parse_doc_version_from_file(task.get("file_path", ""))
    return JSONResponse(result)

@app.post("/api/human-review/{task_id}")
async def api_human_review(task_id: str, request: Request):
    data = await request.json()
    action = data.get("action")
    comment = data.get("comment", "")
    project = data.get("project", default_project)
    try:
        task = get_task(project, task_id)
        if not task:
            return JSONResponse({"success": False, "error": "任务不存在"})
        if task["status"] != "waiting_human_review":
            return JSONResponse({"success": False, "error": f"当前状态为 {task['status']}，无法进行人工审核"})
        if action == "pass":
            update_task_status(project, task_id, "finalized")
            add_comment(project, task_id, "liufeng", f"人工审核通过")
        elif action == "fail":
            if not comment.strip():
                return JSONResponse({"success": False, "error": "不通过时必须输入理由"})
            update_task_status(project, task_id, "re_review",
                               revision_data=json.dumps({"human_feedback": [comment]}))
            add_comment(project, task_id, "liufeng", f"人工审核不通过，意见：{comment}")
        else:
            return JSONResponse({"success": False, "error": f"未知操作: {action}"})
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/api/recover-blocked/{task_id}")
async def api_recover_blocked(task_id: str, request: Request):
    data = await request.json()
    target = data.get("target", "backlog")
    project = data.get("project", default_project)
    try:
        task = get_task(project, task_id)
        if not task:
            return JSONResponse({"success": False, "error": "任务不存在"})
        if task["status"] != "blocked":
            return JSONResponse({"success": False, "error": f"当前状态为 {task['status']}，不是阻塞状态"})
        update_task_status(project, task_id, target, validate=False)
        add_comment(project, task_id, "liufeng", f"手动恢复阻塞：重置为 {target}")
        # 恢复后触发 writer 或 reviewer
        notify_path = NOTIFY_DIR / f"writer-{project}"
        NOTIFY_DIR.mkdir(parents=True, exist_ok=True)
        notify_path.write_text(f"recover blocked {task_id} to {target} at {datetime.now().isoformat()}")
        return JSONResponse({"success": True, "target": target})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


@app.post("/api/retrigger-task/{task_id}")
async def api_retrigger_task(task_id: str, request: Request):
    """重新触发当前任务 — 根据状态写 NOTIFY 文件"""
    data = await request.json()
    project = data.get("project", default_project)
    try:
        task = get_task(project, task_id)
        if not task:
            return JSONResponse({"success": False, "error": "任务不存在"})
        status = task["status"]
        # 根据状态选择触发的 profile
        writer_states = ("backlog", "drafting", "revision")
        reviewer_states = ("awaiting_review", "reviewing", "re_review", "re_reviewing")
        if status in writer_states:
            notify_path = NOTIFY_DIR / f"writer-{project}"
        elif status in reviewer_states:
            notify_path = NOTIFY_DIR / f"review-{project}"
        elif status == "waiting_human_review":
            # 等待人工审核的，通知 reviewer 重新审核
            notify_path = NOTIFY_DIR / f"review-{project}"
        elif status == "blocked":
            # 阻塞的则调用恢复逻辑
            target = "backlog" if task.get("blocked_reason") == "max_iterations_exceeded" else "revision"
            update_task_status(project, task_id, target, validate=False)
            add_comment(project, task_id, "system", f"用户通过重触发恢复阻塞：目标 {target}")
            notify_path = NOTIFY_DIR / f"writer-{project}"
        else:
            return JSONResponse({"success": False, "error": f"状态 {status} 不支持重触发"})
        NOTIFY_DIR.mkdir(parents=True, exist_ok=True)
        notify_path.write_text(f"user retrigger {task_id} at {datetime.now().isoformat()}")
        add_comment(project, task_id, "liufeng", f"用户触发了重操作（当前状态：{status}）")
        return JSONResponse({"success": True, "status": status, "notify": str(notify_path.name)})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


@app.post("/api/reset-task-backlog/{task_id}")
async def api_reset_task_backlog(task_id: str, request: Request):
    """退回待领取"""
    data = await request.json()
    project = data.get("project", default_project)
    try:
        task = get_task(project, task_id)
        if not task:
            return JSONResponse({"success": False, "error": "任务不存在"})
        update_task_status(project, task_id, "backlog", validate=False)
        add_comment(project, task_id, "liufeng", "用户将任务退回「待领取」状态")
        # 触发 Writer 认领
        notify_path = NOTIFY_DIR / f"writer-{project}"
        NOTIFY_DIR.mkdir(parents=True, exist_ok=True)
        notify_path.write_text(f"user reset to backlog {task_id} at {datetime.now().isoformat()}")
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


@app.post("/api/mark-task-blocked/{task_id}")
async def api_mark_task_blocked(task_id: str, request: Request):
    """标记为阻塞"""
    data = await request.json()
    project = data.get("project", default_project)
    try:
        task = get_task(project, task_id)
        if not task:
            return JSONResponse({"success": False, "error": "任务不存在"})
        if task["status"] == "blocked":
            return JSONResponse({"success": False, "error": "任务已经是阻塞状态"})
        reason = data.get("reason", "user_marked_stale")
        update_task_status(project, task_id, "blocked",
                           blocked_reason=reason,
                           blocked_recovery_target="revision")
        add_comment(project, task_id, "liufeng",
                    f"用户手动标记为阻塞（原状态：{task['status']}，原因：{reason}）")
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


@app.get("/api/plain-language/{task_id}")
async def api_plain_language(task_id: str, project: str = default_project):
    """调用 Hermes CLI 用大白话重述文档"""
    try:
        # 获取文档内容
        task = get_task(project, task_id)
        if not task:
            return JSONResponse({"success": False, "error": "任务不存在"})
        doc = get_document_content(task_id, project)
        if not doc.get("found"):
            return JSONResponse({"success": False, "error": "文档内容不可用"})
        content_text = doc.get("content", "")
        if not content_text.strip():
            return JSONResponse({"success": False, "error": "文档内容为空"})

        # 调用 Hermes CLI 生成大白话
        prompt = f"请用大白话总结概括下面文档的主要内容。用几句话说清楚：这个模块是干嘛的、解决什么问题、怎么工作的。简短易懂，别用术语。直接输出结果：\n\n{content_text[:6000]}"
        result = subprocess.run(
             ["/Users/liufeng/.hermes/hermes-agent/venv/bin/hermes",
             "chat", "-q", prompt, "--profile", "yaya"],
            capture_output=True, text=True, timeout=60
        )
        output = result.stdout.strip()
        # 提取 Hermes 的回复正文（去掉框架、推理等装饰内容）
        if output:
            # 从最后一条 ╭─ Hermes 框里提取正文
            import re as _re
            lines = output.split('\n')
            clean = []
            in_response = False
            for line in lines:
                if '╭─' in line and 'Hermes' in line:
                    in_response = True
                    continue
                if in_response:
                    if '╰' in line:
                        break
                    stripped = line.strip()
                    if stripped and not stripped.startswith('│'):
                        clean.append(stripped)
                    elif stripped.startswith('│'):
                        clean.append(stripped[1:].strip())
            if clean:
                output = '\n'.join(clean)
            else:
                # fallback: 去掉开头几行框架信息
                output = '\n'.join(l for l in lines if not l.startswith('Query:') and 'Initializing' not in l and '━━' not in l and not l.startswith('┌─') and not l.startswith('└') and not l.startswith('│')).strip()
        if not output:
            output = result.stderr.strip() or "生成失败"
        return JSONResponse({"success": True, "content": output})
    except subprocess.TimeoutExpired:
        return JSONResponse({"success": False, "error": "生成超时，文档可能过长"})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/api/plain-language-feedback/{task_id}")
async def api_plain_language_feedback(task_id: str, request: Request):
    """记录大白话反馈"""
    try:
        data = await request.json()
        understood = data.get("understood", False)
        reason = data.get("reason", "")
        project = data.get("project", default_project)

        task = get_task(project, task_id)
        if not task:
            return JSONResponse({"success": False, "error": "任务不存在"})

        if understood:
            add_comment(project, task_id, "liufeng", "用户确认看懂了大白话描述")
        else:
            comment = f"用户觉得大白话没看懂"
            if reason:
                comment += f"，反馈意见：{reason}"
            add_comment(project, task_id, "liufeng", comment)

        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


@app.get("/api/automation/state")
async def api_automation_state():
    return JSONResponse(get_automation_state())

@app.get("/api/automation/control")
async def api_automation_control(action: str = ""):
    if action == "start":
        state = set_automation_state(running=True, paused=False, message="运行中")
        # 触发 bootstrap：写 NOTIFY 检查待处理任务
        notify_path = NOTIFY_DIR / "writer-yaya-zhujiao"
        NOTIFY_DIR.mkdir(parents=True, exist_ok=True)
        notify_path.write_text(f"restart automation at {datetime.now().isoformat()}")
    elif action == "pause":
        state = set_automation_state(running=True, paused=True, message="已暂停")
    elif action == "stop":
        state = set_automation_state(running=False, paused=False, message="已停止")
    else:
        return JSONResponse({"success": False, "error": f"未知操作: {action}"})
    return JSONResponse({"success": True, "state": state})

@app.get("/api/reports")
async def api_reports():
    reports = []
    if AUDIT_DIR.exists():
        files = sorted(AUDIT_DIR.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)[:20]
        for f in files:
            if f.suffix in (".md", ".json", ".txt"):
                reports.append({
                    "name": f.name,
                    "time": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "size": f.stat().st_size,
                })
    return JSONResponse(reports)

@app.post("/api/human-review-dialog/{task_id}")
async def api_human_review_dialog(task_id: str, request: Request):
    """人审对话框：接收用户意见，调用 Hermes chat API 生成修改建议"""
    import subprocess, json
    data = await request.json()
    opinion = data.get("opinion", "")
    project = data.get("project", default_project)
    try:
        task = get_task(project, task_id)
        if not task:
            return JSONResponse({"success": False, "error": "任务不存在"})
        doc = get_document_content(task_id, project)
        doc_text = doc.get("content", "")
        if len(doc_text) > 6000:
            doc_text = doc_text[:6000] + "\n[文档截断]"

        # 构造 prompt：评审判定用户意见 + 生成修改说明
        prompt = f"""你是一位文档评审专家。以下是待评审的文档内容以及用户的评审意见。

文档标题：{task.get('title','')}
文档内容：
{doc_text}

用户评审意见：
{opinion}

请完成以下任务：
1. 分析用户的评审意见是否合理，与文档中的问题是否一致。
2. 如果合理，生成详细的修改说明（包含具体位置、修改内容、参考规范）。
3. 如果不完全合理，给出解释并与用户达成共识。
4. 输出格式：用「评审分析：」开头说明你的判断，然后「修改说明：」开头列出具体的修改步骤。

请保持专业、客观和建设性。"""

        result = subprocess.run(
            ["/Users/liufeng/.hermes/hermes-agent/venv/bin/hermes",
             "chat", "-q", prompt, "--profile", "yaya"],
            capture_output=True, text=True, timeout=60
        )
        output = result.stdout.strip()
        # 清理 Hermes 输出框装饰
        if output:
            lines = output.split("\n")
            clean_lines = []
            in_response = False
            for line in lines:
                if "╭─" in line and "Hermes" in line:
                    in_response = True
                    continue
                if in_response:
                    if "╰" in line:
                        break
                    stripped = line.strip()
                    if stripped:
                        clean_lines.append(stripped.lstrip("│ "))
            if clean_lines:
                output = "\n".join(clean_lines)
            else:
                output = "\n".join(l for l in lines if "Initializing" not in l
                    and "━━" not in l and not l.startswith("┌─") and not l.startswith("└")
                    and not l.startswith("│") and "Query:" not in l).strip()

        if not output:
            output = result.stderr.strip() or "生成失败"

        return JSONResponse({"success": True, "content": output})
    except subprocess.TimeoutExpired:
        return JSONResponse({"success": False, "error": "生成超时"})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


@app.post("/api/human-review-consensus/{task_id}")
async def api_human_review_consensus(task_id: str, request: Request):
    """人审达成共识：保存最终修改意见 → 触发 Writer（生产P）"""
    data = await request.json()
    instructions = data.get("instructions", "")
    project = data.get("project", default_project)
    try:
        task = get_task(project, task_id)
        if not task:
            return JSONResponse({"success": False, "error": "任务不存在"})
        if task["status"] != "waiting_human_review":
            return JSONResponse({"success": False, "error": f"当前状态为 {task['status']}，无法确认"})

        # 保存修改意见到 extra，将任务切换为 re_review（进入复审+修改）
        add_comment(project, task_id, "liufeng", f"人审达成共识，修改意见：{instructions}")
        update_task_status(project, task_id, "re_review",
                           revision_data=json.dumps({
                               "human_feedback": [instructions],
                               "human_consensus": instructions,
                           }))

        # 触发 Writer
        from pathlib import Path as _Path
        notify_path = _Path(str(KANBAN_DIR)) / ".notify" / f"writer-{project}"
        notify_path.parent.mkdir(parents=True, exist_ok=True)
        notify_path.write_text(f"human-review consensus {task_id} at {datetime.now().isoformat()}")

        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


"""End of human review dialog endpoints"""

if __name__ == "__main__":
    print("DocProductionReview Dashboard v3.0 → http://127.0.0.1:9119")
    print(f"Kanban DB: {KANBAN_DIR / 'yaya-zhujiao.db'}")
    uvicorn.run(app, host="127.0.0.1", port=9119, log_level="info")
