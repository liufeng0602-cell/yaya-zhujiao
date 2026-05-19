#!/usr/bin/env python3
"""
Judge
-----
Decision engine that consumes an audit report and determines the
document's next state in the review pipeline.

The Judge is a pure function — no I/O, no mutable state. It answers
one question: "Given this audit report and iteration count, what should
happen next?"

Decision table
--------------
+----------------------------------------+--------------------+
| Condition                              | Decision (state)   |
+----------------------------------------+--------------------+
| P0 > 0                                 | needs_revision     |
| P0 == 0, P1 > 0                        | needs_revision     |
| P0 == 0, P1 == 0, P2 > 0              | p2_clearing        |
| P0 == 0, P1 == 0, P2 == 0             | waiting_human_     |
|                                        | review             |
| iteration >= 6 AND not clean           | blocked            |
+----------------------------------------+--------------------+

The ``iteration >= 6`` rule overrides: if a document has looped 6+ times
without reaching clean, it is **blocked** for manual intervention, even
if the current issues are only P2.

Usage
-----
    from reusable_review_rules.judge import Judge, Decision

    report = engine.run(document)
    decision = Judge.evaluate(report, iteration=3)
    # => Decision(state='needs_revision', reason='2 P0, 1 P1 issues')

    if decision.should_block:
        print('Blocked:', decision.reason)

Zero external dependency (stdlib only).
"""

from typing import Dict, Any, Optional


# ── decision type ───────────────────────────────────────────────────

class Decision:
    """Immutable result from Judge.evaluate().

    Attributes
    ----------
    state : str
        One of: needs_revision, p2_clearing, waiting_human_review, blocked.
    reason : str
        Human-readable justification.
    issue_counts : dict
        ``{'P0': N, 'P1': N, 'P2': N}``
    """

    __slots__ = ('state', 'reason', 'issue_counts')

    def __init__(
        self,
        state: str,
        reason: str,
        issue_counts: Dict[str, int],
    ):
        valid_states = (
            'needs_revision',
            'p2_clearing',
            'waiting_human_review',
            'blocked',
        )
        if state not in valid_states:
            raise ValueError(f"Invalid state: {state!r}")
        self.state = state
        self.reason = reason
        self.issue_counts = issue_counts

    @property
    def should_block(self) -> bool:
        """``True`` if the document should not proceed without human
        intervention (either needs_revision or blocked)."""
        return self.state in ('needs_revision', 'blocked')

    @property
    def is_clean(self) -> bool:
        """``True`` if the document has no blocking/review issues."""
        return self.state == 'waiting_human_review'

    def __repr__(self) -> str:
        return (
            f"<Decision {self.state}: "
            f"P0={self.issue_counts['P0']} "
            f"P1={self.issue_counts['P1']} "
            f"P2={self.issue_counts['P2']} "
            f"— {self.reason}>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging / dashboard."""
        return {
            'state': self.state,
            'reason': self.reason,
            'issue_counts': self.issue_counts,
            'should_block': self.should_block,
            'is_clean': self.is_clean,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Decision':
        """Deserialize (for test helpers)."""
        return cls(
            state=d['state'],
            reason=d['reason'],
            issue_counts=d.get('issue_counts', {'P0': 0, 'P1': 0, 'P2': 0}),
        )


# ── judge ───────────────────────────────────────────────────────────

class Judge:
    """Stateless decision engine.

    Usage is always through the classmethod ``evaluate()`` — no
    instantiation needed.
    """

    MAX_ITERATIONS = 6

    @classmethod
    def evaluate(
        cls,
        report: Dict[str, Any],
        iteration: int = 0,
        max_iterations: int = 6,
    ) -> Decision:
        """Determine the document's next state.

        Parameters
        ----------
        report : dict
            Output from ``AuditEngine.run()``.  Must have ``'P0'``,
            ``'P1'``, and ``'P2'`` keys.
        iteration : int
            How many times this document has been through the review
            loop (0 = first pass).  The default (0) means first pass.
        max_iterations : int
            Maximum iterations before forced blocked (default 6).
            Callers can override via strategy pack configuration.

        Returns
        -------
        Decision
        """
        counts = {
            'P0': len(report.get('P0', [])),
            'P1': len(report.get('P1', [])),
            'P2': len(report.get('P2', [])),
        }

        # ── iteration cap (overrides all) ────────────────────────────
        if iteration >= max_iterations and (counts['P0'] + counts['P1'] + counts['P2']) > 0:
            return Decision(
                state='blocked',
                reason=(
                    f"Document has looped {iteration} times (max {max_iterations}) "
                    f"without resolving {counts['P0']} P0 + {counts['P1']} P1 + "
                    f"{counts['P2']} P2 issues.  Manual intervention required."
                ),
                issue_counts=counts,
            )

        # ── funnel: P0 first, then P1, then P2 ───────────────────────
        if counts['P0'] > 0:
            return Decision(
                state='needs_revision',
                reason=f"{counts['P0']} P0 issue(s) found — blocking.  Must fix before proceeding.",
                issue_counts=counts,
            )

        if counts['P1'] > 0:
            return Decision(
                state='needs_revision',
                reason=f"No P0, but {counts['P1']} P1 issue(s) found — must review before commit.",
                issue_counts=counts,
            )

        if counts['P2'] > 0:
            return Decision(
                state='p2_clearing',
                reason=f"No P0/P1.  {counts['P2']} P2 advisory item(s) — clear before human review.",
                issue_counts=counts,
            )

        return Decision(
            state='waiting_human_review',
            reason="All checks passed — document is clean and ready for human review.",
            issue_counts=counts,
        )
