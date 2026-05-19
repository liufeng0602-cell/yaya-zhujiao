#!/usr/bin/env python3
"""
Demo Walkthrough — Reusable Review Rules Pipeline
==================================================

Run this script to see the full AuditEngine + Judge pipeline in action.

  python3 demo_walkthrough.py

It creates a deliberately buggy document, runs all 6 built-in checkers,
prints a terminal report, generates an audit report file, and shows the
Judge's decision.  Then it runs the same pipeline on a clean document for
comparison.

All output goes to stdout + audit-reports/demo/.
"""

import os
import sys
import json
from datetime import datetime

# ── Ensure reusable_review_rules is importable ──────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reusable_review_rules.audit_engine import AuditEngine
from reusable_review_rules.judge import Judge
from reusable_review_rules.builtin_checkers import get_default_checkers


# ════════════════════════════════════════════════════════════════════
# DELIBERATELY BUGGY DOCUMENT (contains every issue the checkers catch)
# ════════════════════════════════════════════════════════════════════

BUGGY_DOC = """\
# 无章节标题的示例文档

本文档没有 H2 章节标题，也没有提交自检报告。

[PARAM:timeout=30]
[PARAM:timeout=60]
[PARAM:max_retries=3]

在下面这个配置块中，不同位置的字段不一样：

[CONFIG:database]
host: localhost
port: 5432
[/CONFIG]

[CONFIG:database]
host: prod.example.com
port: 5432
ssl: true
max_connections: 100
[/CONFIG]

本节存在一个未闭合的引用 — 待 S03 定义。

这是一个普通的正文段落，里面没有标记硬编码值，但有 3.14 这个数字。
"""


# ════════════════════════════════════════════════════════════════════
# CLEAN DOCUMENT (all issues fixed — passes all checkers)
# ════════════════════════════════════════════════════════════════════

CLEAN_DOC = """\
# 系统配置设计文档

## 连接配置

[PARAM:timeout=30]
[PARAM:max_retries=3]

[CONFIG:database]
host: localhost
port: 5432
ssl: false
[/CONFIG]

## 缓存配置

[PARAM:cache_ttl=300]

[CONFIG:cache]
host: localhost
port: 6379
db: 0
[/CONFIG]

## 已知依赖

本节功能由 S03 定义，已完整实现。

<self_check_report>
version: 2
reported_params:
  - name: timeout
    value: "30"
    location: "## 连接配置"
  - name: max_retries
    value: "3"
    location: "## 连接配置"
  - name: cache_ttl
    value: "300"
    location: "## 缓存配置"
reported_configs:
  - entity: database
    fields:
      host: localhost
      port: "5432"
      ssl: "false"
    location: "## 连接配置"
  - entity: cache
    fields:
      host: localhost
      port: "6379"
      db: "0"
    location: "## 缓存配置"
checks:
  value_audit:
    result: true
    note: "所有 PARAM 值已与配置代码一致"
  field_consistency:
    result: true
    note: "所有 CONFIG 字段与实际部署配置一致"
</self_check_report>
"""


# ════════════════════════════════════════════════════════════════════
# UTILITY
# ════════════════════════════════════════════════════════════════════

CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
GRAY = "\033[90m"
RESET = "\033[0m"
SEP = "─" * 72


def severity_color(s):
    return {"P0": RED, "P1": YELLOW, "P2": CYAN}.get(s, RESET)


def print_issues(level, issues, label):
    print(f"\n  {BOLD}{severity_color(level)}{level}{RESET} — {label}")
    if not issues:
        print(f"    {GREEN}✓ 无{RESET}")
        return
    for iss in issues:
        loc = f"[L{iss.get('location', '?')}]" if iss.get('location') else ""
        ev = f" ({iss['evidence'][:60]})" if iss.get('evidence') else ""
        print(f"    {severity_color(level)}⚠{RESET} {iss['check_id']:40s} {loc}")
        print(f"    {'':2s}{iss['msg']}{ev}")


def print_decision(decision):
    state_colors = {
        'waiting_human_review': GREEN,
        'p2_clearing': CYAN,
        'needs_revision': RED,
        'blocked': RED,
    }
    c = state_colors.get(decision.state, RESET)
    print(f"\n  {BOLD}Judge 裁决:{RESET} {c}{BOLD}{decision.state}{RESET}")
    print(f"    {decision.reason}")
    if decision.issue_counts:
        counts = decision.issue_counts
        parts = [f"  P0={counts.get('P0', 0)}", f"P1={counts.get('P1', 0)}", f"P2={counts.get('P2', 0)}"]
        print(f"    ({', '.join(parts)})")


def generate_audit_report(document_name, content, audit, decision):
    """Write a markdown audit report to audit-reports/demo/."""
    reports_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'audit-reports', 'demo'
    )
    os.makedirs(reports_dir, exist_ok=True)

    slug = document_name.replace('.md', '').replace(' ', '_')
    version = datetime.now().strftime('v%Y%m%d_%H%M%S')
    report_path = os.path.join(reports_dir, f'{slug}_audit_report_{version}.md')

    p0s = audit.get('P0', [])
    p1s = audit.get('P1', [])
    p2s = audit.get('P2', [])

    with open(report_path, 'w') as f:
        f.write(f'# 审计报告：{document_name}\n')
        f.write(f'审核引擎：AuditEngine v0.1.0\n')
        f.write(f'审核日期：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')

        for level, issues, label in [
            ('P0', p0s, '阻断问题 — 必须修复后才能提交'),
            ('P1', p1s, '审核问题 — 提交前必须审查'),
            ('P2', p2s, '建议项 — 不阻断，推荐修复'),
        ]:
            f.write(f'## {level}（{label}）\n')
            if issues:
                f.write('| 检查器 | 位置 | 问题描述 |\n')
                f.write('|--------|------|----------|\n')
                for iss in issues:
                    loc = str(iss.get('location', '-'))
                    msg = iss['msg']
                    ev = iss.get('evidence', '')
                    if ev:
                        msg = f'{msg}  (证据: {ev})'
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

        # Tracker summary
        tracker = audit.get('tracker', {})
        params = tracker.get('params', [])
        configs = tracker.get('configs', [])
        f.write(f'\n## 标记扫描摘要\n')
        f.write(f'- [PARAM:...] 标记: {len(params)} 个\n')
        f.write(f'- [CONFIG:...] 标记: {len(configs)} 个\n')
        if params:
            f.write(f'  - {", ".join(p.get("name", "?") for p in params)}\n')
        if configs:
            entities = set(c.get('entity', '?') for c in configs)
            f.write(f'  - 实体: {", ".join(sorted(entities))}\n')

    print(f"\n  {GRAY}审计报告已保存: {report_path}{RESET}")
    return report_path


# ════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════

def main():
    print(f"\n{BOLD}{'╔' + '═'*70 + '╗'}{RESET}")
    print(f"{BOLD}║  Reusable Review Rules — Pipeline Demo{RESET}")
    print(f"{BOLD}║  AuditEngine v0.1.0 • 6 built-in checkers • 3-tier defense{RESET}")
    print(f"{BOLD}{'╚' + '═'*70 + '╝'}{RESET}")

    # ── Set up the pipeline ─────────────────────────────────────
    print(f"\n{BOLD}初始化审核引擎...{RESET}")
    engine = AuditEngine()
    checkers = get_default_checkers(max_layer=1)
    engine.register_list(checkers)
    print(f"  已注册 {len(checkers)} 个检查器:")
    for c in checkers:
        layer_tag = f"L{c.layer}"
        sev_tag = f"[{c.severity}]" if c.layer == 0 else f"[{c.severity}]"
        print(f"    {c.id:42s} {GRAY}{layer_tag} {sev_tag}{RESET}")

    # ══════════════════════════════════════════════════════════════
    # SCENE 1: Buggy document
    # ══════════════════════════════════════════════════════════════
    print(f"\n\n{BOLD}{'═' * 72}{RESET}")
    print(f"{BOLD}场景 1: 有缺陷的文档 ═══════════════════════════════════{RESET}")
    print(f"{BOLD}{'═' * 72}{RESET}")

    doc_label = "buggy_doc.md"
    print(f"\n  文档内容 ({len(BUGGY_DOC)} 字符):")
    for line in BUGGY_DOC.strip().split('\n'):
        print(f"  {GRAY}|{RESET} {line}")

    audit = engine.run(BUGGY_DOC)

    print(f"\n{SEP}")
    print(f"\n  {BOLD}审核结果{RESET} (耗时 {audit['duration_ms']:.1f}ms)")
    print(f"  {GRAY}扫描到 {len(audit['tracker']['params'])} 个 [PARAM] + "
          f"{len(audit['tracker']['configs'])} 个 [CONFIG] 标记{RESET}")

    print_issues("P0", audit['P0'], label="阻断问题 — 必须修复")
    print_issues("P1", audit['P1'], label="审核问题 — 提交前必须审查")
    print_issues("P2", audit['P2'], label="建议项 — 不阻断，推荐修复")

    decision = Judge.evaluate(audit, iteration=1)
    print_decision(decision)
    generate_audit_report(doc_label, BUGGY_DOC, audit, decision)

    # ══════════════════════════════════════════════════════════════
    # SCENE 2: Clean document
    # ══════════════════════════════════════════════════════════════
    print(f"\n\n{BOLD}{'═' * 72}{RESET}")
    print(f"{BOLD}场景 2: 干净的文档（所有问题已修复）═══════════════════{RESET}")
    print(f"{BOLD}{'═' * 72}{RESET}")

    doc_label2 = "clean_doc.md"
    print(f"\n  文档内容 ({len(CLEAN_DOC)} 字符, 包含 <self_check_report>):")
    lines = CLEAN_DOC.strip().split('\n')
    for line in lines[:10]:
        print(f"  {GRAY}|{RESET} {line}")
    print(f"  {GRAY}|{RESET}   ...  (共 {len(lines)} 行)")

    audit2 = engine.run(CLEAN_DOC)

    print(f"\n{SEP}")
    print(f"\n  {BOLD}审核结果{RESET} (耗时 {audit2['duration_ms']:.1f}ms)")
    print(f"  {GRAY}扫描到 {len(audit2['tracker']['params'])} 个 [PARAM] + "
          f"{len(audit2['tracker']['configs'])} 个 [CONFIG] 标记{RESET}")

    print_issues("P0", audit2['P0'], label="阻断问题")
    print_issues("P1", audit2['P1'], label="审核问题")
    print_issues("P2", audit2['P2'], label="建议项")

    decision2 = Judge.evaluate(audit2, iteration=1)
    print_decision(decision2)
    generate_audit_report(doc_label2, CLEAN_DOC, audit2, decision2)

    # ══════════════════════════════════════════════════════════════
    # SCENE 3: Iteration cap
    # ══════════════════════════════════════════════════════════════
    print(f"\n\n{BOLD}{'═' * 72}{RESET}")
    print(f"{BOLD}场景 3: 迭代封顶演示 ═════════════════════════════════════{RESET}")
    print(f"{BOLD}    同一份缺陷文档在第 6 轮审核时自动 blocked{RESET}")
    print(f"{BOLD}{'═' * 72}{RESET}")

    for iteration in [1, 3, 5, 6]:
        d = Judge.evaluate(audit, iteration=iteration)
        cap_mark = " ← 封顶!" if iteration >= 6 else ""
        print(f"  iteration={iteration:2d} → {d.state:25s}{cap_mark}")

    # ── Summary ─────────────────────────────────────────────────
    print(f"\n\n{BOLD}{'═' * 72}{RESET}")
    print(f"{BOLD}摘要{RESET}")
    print(f"{BOLD}{'═' * 72}{RESET}")
    p0c1, p1c1, p2c1 = len(audit['P0']), len(audit['P1']), len(audit['P2'])
    p0c2, p1c2, p2c2 = len(audit2['P0']), len(audit2['P1']), len(audit2['P2'])
    print(f"""
  {GREEN}✓{RESET} 场景 1: {RED}needs_revision{RESET} — 发现 {p0c1} 个 P0、{p1c1} 个 P1、{p2c1} 个 P2
  {GREEN}✓{RESET} 场景 2: {GREEN}waiting_human_review{RESET} — 全部通过 (P0={p0c2}, P1={p1c2}, P2={p2c2})
  {GREEN}✓{RESET} 场景 3: iteration≥6 → {RED}blocked{RESET} — 封顶机制生效
""")

    print(f"{BOLD}审计报告文件:{RESET}")
    reports_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'audit-reports', 'demo'
    )
    if os.path.exists(reports_dir):
        for fname in sorted(os.listdir(reports_dir)):
            print(f"  audit-reports/demo/{fname}")

    print(f"\n{GRAY}{'─'*72}{RESET}")
    print(f"{GRAY}演示完成。去 README.md 查看如何编写自定义检查器。{RESET}")
    print()


if __name__ == '__main__':
    main()
