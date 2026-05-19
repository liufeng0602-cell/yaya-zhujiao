#!/usr/bin/env python3
"""
BaseChecker
-----------
Abstract base for all document quality checkers in the reusable review
rules framework.

Every checker is a subclass that implements a single public method:
``check(document, tracker)``, which returns a list of issues found.

Layers
------
These map directly to the pipeline's 3-tier defense:
  Layer 0 = code / syntax  — structural validity (YAML parses, markers exist)
  Layer 1 = code / semantic — structured content rules (uniqueness, consistency,
                               cross-references)
  Layer 2 = LLM evidence   — semantic checks that require an LLM pass (AI
                               mutable boundary, requirement coverage, etc.)

Usage
-----
    from reusable_review_rules.base_checker import BaseChecker, CheckResult

    class MyChecker(BaseChecker):
        id = "uniqueness/param_names"
        name = "PARAM name uniqueness"
        description = "All [PARAM:name=...] must have unique names."
        severity = "P1"
        layer = 1

        def check(self, document: str, tracker: dict) -> list:
            issues = []
            for p in tracker['params']:
                ...  # logic
            return issues

Zero external dependency — only Python stdlib (abc, typing).
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


# ── Issue type ───────────────────────────────────────────────────────

class CheckResult:
    """A single issue raised by a checker during a quality pass.

    Attributes
    ----------
    severity : str
        P0 = blocking (must fix before commit), P1 = must review before
        commit, P2 = advisory (log, do not block).
    check_id : str
        Fully-qualified rule identifier, e.g. 'uniqueness/param_names'.
    msg : str
        Human-readable description of the issue.
    location : int or None
        1-based line number where the issue was found.  ``None`` when
        the issue is document-level (e.g. "no self-check report found").
    evidence : str or None
        Snippet of the offending text, or ``None`` if not applicable.
    """
    __slots__ = ('severity', 'check_id', 'msg', 'location', 'evidence')

    def __init__(
        self,
        severity: str,
        check_id: str,
        msg: str,
        location: Optional[int] = None,
        evidence: Optional[str] = None,
    ):
        if severity not in ('P0', 'P1', 'P2'):
            raise ValueError(f"Invalid severity: {severity!r} — must be P0/P1/P2")
        self.severity = severity
        self.check_id = check_id
        self.msg = msg
        self.location = location
        self.evidence = evidence

    def __repr__(self) -> str:
        loc = f" L{self.location}" if self.location else ""
        ev = f" [{self.evidence[:60]}...]" if self.evidence else ""
        return f"[{self.severity}]{loc} {self.check_id}: {self.msg}{ev}"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to the dict format consumed by AuditEngine / Judge."""
        d: Dict[str, Any] = {
            'severity': self.severity,
            'check_id': self.check_id,
            'msg': self.msg,
        }
        if self.location is not None:
            d['location'] = self.location
        if self.evidence is not None:
            d['evidence'] = self.evidence
        return d


# ── Base checker interface ──────────────────────────────────────────

class BaseChecker(ABC):
    """Abstract base for all checkers.

    Subclasses **must** define:
      * ``id``         — unique rule identifier (ClassVar[str])
      * ``name``       — short human-readable name (ClassVar[str])
      * ``description`` — longer explanation (ClassVar[str])
      * ``severity``   — default issue severity: P0, P1, or P2 (ClassVar[str])
      * ``layer``      — 0, 1, or 2 (ClassVar[int])
      * ``check()``    — the check logic

    Subclasses **may** override:
      * ``metadata``   — returns a frozen dict of the above
    """

    # ── class-level metadata (override in every subclass) ────────────

    id: str = ""
    name: str = ""
    description: str = ""
    severity: str = "P2"
    layer: int = 0

    # ── public API ───────────────────────────────────────────────────

    @abstractmethod
    def check(self, document: str, tracker: dict) -> List[CheckResult]:
        """Run this checker against a document.

        Parameters
        ----------
        document : str
            Full text of the document being audited.
        tracker : dict
            Output from ``hardcoded_tracker.scan(document)`` — a dict
            with ``'params'``, ``'configs'``, and ``'errors'`` keys.

        Returns
        -------
        List[CheckResult]
            Zero or more issues found.  An empty list means PASS.
        """
        ...

    # ── metadata accessor ────────────────────────────────────────────

    @classmethod
    def metadata(cls) -> Dict[str, Any]:
        """Immutable snapshot of this checker's identity."""
        return {
            'id': cls.id,
            'name': cls.name,
            'description': cls.description,
            'severity': cls.severity,
            'layer': cls.layer,
        }


# ── convenience ─────────────────────────────────────────────────────

def check_result_from_dict(d: Dict[str, Any]) -> CheckResult:
    """Deserialize a dict back into a CheckResult (for test helpers)."""
    return CheckResult(
        severity=d['severity'],
        check_id=d['check_id'],
        msg=d['msg'],
        location=d.get('location'),
        evidence=d.get('evidence'),
    )
