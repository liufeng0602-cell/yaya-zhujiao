"""Reusable Review Rules — open-source document quality pipeline framework.

A 3-tier defense system for automated document review:
  Layer 0 — Syntax & structure (code checks, no LLM)
  Layer 1 — Semantic consistency on structured markers (code checks, no LLM)
  Layer 2 — LLM-assisted evidence collection + code-based judgment (strategy pack)

Core components
---------------
- HardcodedValueTracker       — zero-dep [PARAM:...] / [CONFIG:...] scanner
- SelfCheckReportValidator    — validates Writer <self_check_report> YAML blocks
- BaseChecker / CheckResult   — abstract checker interface + result type
- AuditEngine                 — orchestrator: runs all registered checkers
- Judge                       — decision engine: maps audit results to kanban state
- Builtin checkers (x6)       — out-of-the-box rules covering all three layers
"""

__version__ = "0.1.0"
