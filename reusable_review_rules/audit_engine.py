#!/usr/bin/env python3
"""
AuditEngine
-----------
Orchestrator that runs all registered checkers against a document and
collects their findings into a structured audit report.

Flow
----
1. Run ``HardcodedValueTracker.scan(document)`` to extract tagged markers.
2. Pass the tracker result to every registered checker in registration order.
3. Collect all ``CheckResult`` instances, group by severity.
4. Return a flat dict that the ``Judge`` consumes directly.

Usage
-----
    from reusable_review_rules.audit_engine import AuditEngine
    from reusable_review_rules.base_checker import BaseChecker

    engine = AuditEngine()
    engine.register(MyLayer0Checker())
    engine.register(MyLayer1Checker())
    report = engine.run(document_text)

    if report['P0']:
        print('Blocking issues found, cannot commit.')
    elif report['P1']:
        print('Non-blocking issues, review recommended.')
    else:
        print(f'Clean: {len(report["P2"])} advisory notes.')

Zero external dependency (stdlib only).
"""

import time
from typing import Dict, List, Any

from reusable_review_rules.base_checker import BaseChecker, CheckResult
from reusable_review_rules.hardcoded_tracker import scan
from reusable_review_rules.hardcoded_tracker import param_values_by_name
from reusable_review_rules.hardcoded_tracker import config_fields_by_entity


class AuditEngine:
    """Register checkers, then run them all against a document.

    Parameters
    ----------
    skip_layer : int or None
        If set, checkers with ``layer >= skip_layer`` are skipped.
        Use ``skip_layer=2`` to run only Layer 0 + 1 (code checks)
        without Layer 2 (LLM evidence pass).
    """

    def __init__(self, skip_layer: int | None = None):
        self._checkers: List[BaseChecker] = []
        self._skip_layer = skip_layer

    # ── registration ────────────────────────────────────────────────

    def register(self, checker: BaseChecker) -> None:
        """Register a checker instance.

        Raises ``ValueError`` if another checker with the same ``id`` is
        already registered (duplicate detection).
        """
        if any(c.id == checker.id for c in self._checkers):
            raise ValueError(f"Duplicate checker id: {checker.id!r}")
        self._checkers.append(checker)

    def register_list(self, checkers: List[BaseChecker]) -> None:
        """Register multiple checkers at once."""
        for c in checkers:
            self.register(c)

    @property
    def checker_ids(self) -> List[str]:
        """Return IDs of all registered checkers."""
        return [c.id for c in self._checkers]

    # ── execution ───────────────────────────────────────────────────

    def run(self, document: str) -> Dict[str, Any]:
        """Run all checkers against ``document``.

        Returns
        -------
        dict with keys:
          'P0'       — list of P0 CheckResult dicts (blocking)
          'P1'       — list of P1 CheckResult dicts (must review)
          'P2'       — list of P2 CheckResult dicts (advisory)
          'tracker'  — raw output from HardcodedValueTracker.scan()
          'checkers' — list of checker IDs that ran
          'skipped'  — list of checker IDs that were skipped
          'duration_ms' — wall-clock time in milliseconds
        """
        t0 = time.perf_counter()

        # ── scan markers ─────────────────────────────────────────────
        tracker = scan(document)

        # ── run each checker ─────────────────────────────────────────
        issues: List[CheckResult] = []
        skipped: List[str] = []
        ran: List[str] = []

        for checker in self._checkers:
            if self._skip_layer is not None and checker.layer >= self._skip_layer:
                skipped.append(checker.id)
                continue
            ran.append(checker.id)
            issues.extend(checker.check(document, tracker))

        # ── promote tracker errors to P2 issues ──────────────────────
        for err in tracker.get('errors', []):
            issues.append(CheckResult(
                severity='P2',
                check_id='tracker/scan_error',
                msg=f"HardcodedValueTracker scan error: {err}",
            ))

        # ── group by severity ────────────────────────────────────────
        grouped: Dict[str, List[Dict[str, Any]]] = {'P0': [], 'P1': [], 'P2': []}
        for iss in issues:
            grouped.setdefault(iss.severity, []).append(iss.to_dict())

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

        return {
            'P0': grouped['P0'],
            'P1': grouped['P1'],
            'P2': grouped['P2'],
            'tracker': tracker,
            'checkers': ran,
            'skipped': skipped,
            'duration_ms': elapsed_ms,
        }


# ── convenience ─────────────────────────────────────────────────────

def print_report(report: Dict[str, Any]) -> None:
    """Human-readable dump of an audit report."""
    total = len(report['P0']) + len(report['P1']) + len(report['P2'])
    print(f"Audit report ({report['duration_ms']}ms, {len(report['checkers'])} checkers)")
    print(f"  Checkers: {', '.join(report['checkers'])}")
    if report['skipped']:
        print(f"  Skipped:  {', '.join(report['skipped'])}")
    print(f"  Total issues: {total}")
    if report['P0']:
        print(f"  P0 (blocking):")
        for i in report['P0']:
            loc = f" L{i['location']}" if 'location' in i else ""
            ev = f" [{i['evidence'][:60]}...]" if 'evidence' in i else ""
            print(f"    [{i['check_id']}]{loc} {i['msg']}{ev}")
    if report['P1']:
        print(f"  P1 (review):")
        for i in report['P1']:
            loc = f" L{i['location']}" if 'location' in i else ""
            print(f"    [{i['check_id']}]{loc} {i['msg']}")
    if report['P2']:
        print(f"  P2 (advisory):")
        for i in report['P2']:
            loc = f" L{i['location']}" if 'location' in i else ""
            print(f"    [{i['check_id']}]{loc} {i['msg']}")
