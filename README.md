# Reusable Review Rules — Document Quality Pipeline Framework

A **3-tier defense** system for automated document review.  Ships with 6 built-in
checkers and zero external dependencies (stdlib only).  Designed for teams that
want **verifiable, deterministic quality gates** in their documentation workflow.

```bash
pip install -e .                    # or just copy reusable_review_rules/ into your project
python3 demo_walkthrough.py         # see the full pipeline in action
```

---

## The Problem

Most document reviews rely on **LLM guesswork**: send the doc to an LLM, ask
"does this look right?", get a chatty prose report back.  This approach is:

- **Non-reproducible** — the same doc reviewed twice gives different results.
- **Non-actionable** — "section 3 needs improvement" tells the writer nothing.
- **Non-enforceable** — no way to gate a commit on a deterministic quality bar.

---

## The Solution: 3-Tier Defense

```
 Layer  │ Type         │ What it catches                     │ Severity
────────┼──────────────┼────────────────────────────────────┼──────────
   0    │ Code check   │ Missing structure, missing          │    P0
        │              │ self-check, file-level validity     │
   1    │ Code check   │ Duplicate PARAMs, inconsistent      │  P0/P1
        │              │ CONFIG blocks, dangling cross-refs, │
        │              │ missing hardcoded-value markers      │
   2    │ LLM + Code   │ Strategy pack injects LLM evidence  │  P2 →
        │              │ collection + code-based judgment    │ P0 (trained)
```

**Key insight**: Layers 0 and 1 are pure code — deterministic, zero-cost,
reproducible.  Layer 2 adds LLM-powered flexibility, but the LLM is
**an evidence collector, not a judge**.  The final decision tree lives in code.

---

## Components

| Component | File | Role |
|---|---|---|
| `HardcodedValueTracker` | `hardcoded_tracker.py` | Scans `[PARAM:name=value]` and `[CONFIG:entity]` markers. |
| `SelfCheckReportValidator` | `self_check_validator.py` | Validates Writer's `<self_check_report>` YAML block (custom zero-dep parser). |
| `BaseChecker` / `CheckResult` | `base_checker.py` | Abstract base class + typed result (severity P0/P1/P2). |
| `AuditEngine` | `audit_engine.py` | Orchestrator: runs all registered checkers, groups results by severity, handles skip-layer and duplicate IDs. |
| `Judge` | `judge.py` | Pure-function decision engine: P0>0 → `needs_revision`, P1>0 → `needs_revision`, P2>0 → `p2_clearing`, all clean → `waiting_human_review`, iteration≥6 → `blocked`. |
| Builtin Checkers (×6) | `builtin_checkers.py` | Out-of-the-box rules covering all three layers. |

### 6 Built-In Checkers

| Checker ID | Layer | Severity | Detection |
|---|---|---|---|
| `syntax/doc_structure` | L0 | P2 | Missing H1 title or H2 sections |
| `validity/self_check_report` | L0 | **P0** | Missing `<self_check_report>` block (blocks commit) |
| `uniqueness/param_names` | L1 | **P1** | `[PARAM:timeout=...]` defined in multiple places |
| `consistency/config_fields` | L1 | P2 | `[CONFIG:entity]` blocks with different field sets |
| `coverage/unresolved_cross_ref` | L1 | **P1** | Dangling "待 Sxx 定义" forward-references |
| `coverage/hardcoded_values_tagged` | L1 | P2 | No `[PARAM:...]` or `[CONFIG:...]` markers at all |

---

## State Machine

The kanban card states driven by Judge decisions:

```
                   ┌──────────────────────────────┐
                   │         awaiting_review        │
                   └──────────┬───────────────────┘
                              │
                              ▼
                   ┌──────────────────────────────┐
                   │           reviewing            │
                   └──┬────────────────┬─────────┬──┘
                      │                │         │
                      ▼                ▼         ▼
              needs_revision     p2_clearing  waiting_human_review
               (P0>0 | P1>0)     (P2>0 only)   (all clean)
                      │                │
                      ▼                ▼
                  drafting          drafting
                      │                │
                      ▼                ▼
                  awaiting_review  awaiting_review  ──► ...submits for re-review
                      │                │
                      ▼                ▼
                  re_review        re_review
                      │                │
                      ▼                ▼
                re_reviewing      re_reviewing
                      │                │
                      ▼                ▼
           ┌── needs_revision ── (back to drafting)
           │
           └── p2_clearing ────── (back to drafting)
           │
           └── waiting_human_review ── done
```

Iteration cap: if `iteration_count >= 6` and audit fails, card moves to
`blocked` instead of `revision`.

**Writer trigger mechanism**: When a card enters `revision` or `p2_clearing`,
the Reviewer writes a NOTIFY file.  A fswatch daemon watches for this file
and launches the Writer process, which picks up the card from `backlog` (via
`try_claim_task`) and enters `drafting`.  After commit, the Writer transitions
the card to `awaiting_review` or `re_review`, which triggers the Reviewer again.

*Implementation detail: see DEV_GUIDE.md §3.1 (Writer trigger) and §4.1
(Reviewer trigger) for the NOTIFY file format and fswatch lifecycle.*

---

## Quick Start

```python
from reusable_review_rules.audit_engine import AuditEngine
from reusable_review_rules.judge import Judge
from reusable_review_rules.builtin_checkers import get_default_checkers

# 1. Set up the pipeline
engine = AuditEngine()
engine.register_list(get_default_checkers(max_layer=1))

# 2. Run the audit
content = open("my_document.md").read()
audit = engine.run(content)

# 3. Judge decides the next state
decision = Judge.evaluate(audit, iteration=2)
print(f"Decision: {decision.state}")
print(f"P0={len(audit['P0'])}, P1={len(audit['P1'])}, P2={len(audit['P2'])}")
```

---

## Writing a Custom Checker

```python
from reusable_review_rules.base_checker import BaseChecker, CheckResult

class MyCustomChecker(BaseChecker):
    id = "style/title_case"          # unique dot-notation ID
    name = "Title case enforcement"
    description = "H1 titles must use Title Case."
    severity = "P2"                  # default severity
    layer = 1

    def check(self, document: str, tracker: dict) -> list:
        issues = []
        for line in document.split('\n'):
            if line.startswith('# ') and line[2].islower():
                issues.append(CheckResult(
                    'P2', self.id,
                    f"H1 title should use Title Case: '{line[2:]}'",
                ))
        return issues

# Register it
engine = AuditEngine()
engine.register(MyCustomChecker())
```

---

## Architecture Decisions

### Open-Source vs. Closed-Source Split

| Layer | Open Source (this repo) | Closed Source (strategy pack) |
|---|---|---|
| L0 + L1 | 6 built-in checkers | Additional custom checkers |
| L2 | **Not yet implemented** — placeholder at `max_layer >= 2` | LLM prompting templates, evidence validators |
| Evolution | — | Training data, rule auto-generation, manual approval gate |
| Glossary | — | `glossary.yaml` — term definitions, validation specs |

The framework is fully functional and demoable without the closed-source pack.
Layer 2 and evolution features are injected at `run_audit()` time via a strategy
object (to be released separately).

### Why Not Pure LLM?

The LLM is a **witness, not a judge**.  In Layer 2, the LLM collects evidence
("I found these 5 occurrences of hardcoded IP addresses"), then a code-based
Judge decides ("2 are known params → P2 warning, 3 are unknown → P1 flag").
This keeps the quality bar deterministic and the LLM's role contained.

---

## Roadmap

- [x] HardcodedValueTracker — zero-dep `[PARAM:...]` / `[CONFIG:...]` scanner
- [x] SelfCheckReportValidator — Writer self-check validation with custom YAML parser
- [x] BaseChecker / CheckResult — abstract base class + typed result
- [x] AuditEngine — orchestrator with skip-layer, duplicate-ID protection
- [x] Judge — decision engine with iteration cap
- [x] 6 built-in checkers covering L0 + L1
- [x] Kanban integration (p2_clearing state, full state machine)
- [ ] Writer self-check gate — enforce `SelfCheckReportValidator` before Writer commits
- [ ] Closed-source strategy pack — LLM prompts, glossary, evolution rules
- [ ] 30–50 rule initial pack across 3 domains (SaaS, toC, tools)
- [ ] Training period with manual approval gate
- [ ] Dual-model cross-validation for Layer 2 evidence

---

## License

MIT — see LICENSE file.

Built for the [DocCraft](https://github.com/liufeng0602-cell/yaya-zhujiao) project.
