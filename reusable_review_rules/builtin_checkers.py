#!/usr/bin/env python3
"""Built-in checkers for the reusable review rules framework.

These are open-source BaseChecker implementations that demonstrate
the 3-tier defense model.  They ship with the framework so developers
can see the pipeline work out of the box.

Layers
------
Layer 0  — syntax, structure, file-level validity (code checks)
Layer 1  — semantic rules on structured content (code checks)
Layer 2  — LLM evidence pass (requires LLM call — not included here)

All checkers are zero-dependency (stdlib only).
"""

from typing import Dict, List, Any, Optional, Tuple

from reusable_review_rules.base_checker import BaseChecker, CheckResult


# ══════════════════════════════════════════════════════════════════════
# Layer 0 — syntax & structure
# ══════════════════════════════════════════════════════════════════════


class DocStructureChecker(BaseChecker):
    """Verify the document has minimum markdown structure: title, sections."""
    id = "syntax/doc_structure"
    name = "Document structure"
    description = "Document must have an H1 title (# ...) and at least one H2 (## ...)."
    severity = "P2"
    layer = 0

    def check(self, document: str, tracker: dict) -> list:
        issues = []
        lines = document.split('\n')

        has_h1 = any(l.startswith('# ') for l in lines)
        if not has_h1:
            issues.append(CheckResult(
                'P2', self.id,
                'Document has no H1 title (# ...)',
            ))

        has_h2 = any(l.startswith('## ') for l in lines)
        if not has_h2:
            issues.append(CheckResult(
                'P2', self.id,
                'Document has no H2 sections (## ...)',
            ))

        return issues


class SelfCheckReportChecker(BaseChecker):
    """Validate the <self_check_report> YAML block exists and is well-formed.

    Wraps SelfCheckReportValidator as a BaseChecker so it participates
    in the AuditEngine pipeline.
    """
    id = "validity/self_check_report"
    name = "Self-check report validation"
    description = "Validates the Writer <self_check_report> YAML block."
    severity = "P0"
    layer = 0

    def check(self, document: str, tracker: dict) -> list:
        from reusable_review_rules.self_check_validator import \
            SelfCheckReportValidator

        report_data, issues = SelfCheckReportValidator.validate(
            document, tracker,
        )

        results = []
        for iss in issues:
            msg = iss['msg']
            if iss.get('severity') == 'P0':
                msg += (
                    ' (Writer export gate: auto-fix not yet active — '
                    'this is a Reviewer-side check)'
                )
            results.append(CheckResult(
                severity=iss.get('severity', 'P2'),
                check_id=f"{self.id}/{iss.get('check_id', iss['msg'].split()[0].lower().strip('<>'))}",
                msg=msg,
                location=iss.get('location'),
            ))
        return results


# ══════════════════════════════════════════════════════════════════════
# Layer 1 — semantic consistency
# ══════════════════════════════════════════════════════════════════════


class ParamUniquenessChecker(BaseChecker):
    """Detect duplicate [PARAM:name=...] definitions.

    Same PARAM name in multiple places makes it unclear which value
    is authoritative.
    """
    id = "uniqueness/param_names"
    name = "PARAM name uniqueness"
    description = "Each [PARAM:name=...] must have a unique name within the document."
    severity = "P1"
    layer = 1

    def check(self, document: str, tracker: dict) -> list:
        from reusable_review_rules.hardcoded_tracker import \
            param_values_by_name

        issues = []
        for name, values in param_values_by_name(tracker).items():
            if len(values) > 1:
                issues.append(CheckResult(
                    'P1', self.id,
                    f"PARAM '{name}' appears {len(values)} times — "
                    f"which is authoritative?",
                    evidence=str(values),
                ))

        return issues


class ConfigFieldConsistencyChecker(BaseChecker):
    """Check that multiple [CONFIG:entity] blocks for the same entity
    have identical field names."""
    id = "consistency/config_fields"
    name = "CONFIG field cross-block consistency"
    description = "All [CONFIG:entity] blocks with the same entity must share field names."
    severity = "P2"
    layer = 1

    def check(self, document: str, tracker: dict) -> list:
        from reusable_review_rules.hardcoded_tracker import \
            config_fields_by_entity

        issues = []
        for entity, blocks in config_fields_by_entity(tracker).items():
            if len(blocks) <= 1:
                continue
            field_sets = [set(b.keys()) for b in blocks]
            if not all(fs == field_sets[0] for fs in field_sets[1:]):
                issues.append(CheckResult(
                    'P2', self.id,
                    f"CONFIG '{entity}' fields differ across blocks",
                    evidence=str([list(fs) for fs in field_sets]),
                ))

        return issues


class UnresolvedCrossReferenceChecker(BaseChecker):
    """Detect dangling cross-references like '待 Sxx 定义'.

    These indicate the writer committed a forward-reference without
    resolving it.
    """
    id = "coverage/unresolved_cross_ref"
    name = "Unresolved cross-references"
    description = ("Lines containing '待 S' and '定义' but not '已定义' are "
                   "dangling forward-references.")
    severity = "P1"
    layer = 1

    def check(self, document: str, tracker: dict) -> list:
        issues = []
        for i, line in enumerate(document.split('\n'), 1):
            if '待 S' in line and '定义' in line and '已定义' not in line:
                # Skip self-check report block
                stripped = line.strip()
                if stripped.startswith('#') or stripped == '':
                    continue
                issues.append(CheckResult(
                    'P1', self.id,
                    "Unresolved forward-reference (待 Sxx 定义) — "
                    "must be resolved or documented as intentional",
                    location=i,
                    evidence=stripped[:80],
                ))

        return issues


class HardcodedValuePresenceChecker(BaseChecker):
    """Check that the document has at least one [PARAM:...] or [CONFIG:...]
    marker if git commits to this subsystem have ever introduced them.

    This is a lightweight rule: if the document has NO tagged hardcoded
    values at all, it might be using bare numbers.  We warn (P2) the
    writer to consider tagging.
    """
    id = "coverage/hardcoded_values_tagged"
    name = "Hardcoded values tagging"
    description = "Documents should tag hardcoded values with [PARAM:...] or [CONFIG:...]."
    severity = "P2"
    layer = 1

    def check(self, document: str, tracker: dict) -> list:
        if not tracker.get('params') and not tracker.get('configs'):
            return [CheckResult(
                'P2', self.id,
                "No [PARAM:...] or [CONFIG:...] markers found in document. "
                "Consider tagging if any hardcoded values exist.",
            )]
        return []


# ══════════════════════════════════════════════════════════════════════
# Factory: get a standard set of built-in checkers
# ══════════════════════════════════════════════════════════════════════


def get_default_checkers(max_layer: int = 1) -> List[BaseChecker]:
    """Return the standard checker list.

    Parameters
    ----------
    max_layer : int
        Maximum layer to include.  0 = syntax only,
        1 = syntax + semantic (default), 2 = include placeholder
        for LLM checks (no-op until strategy pack injected).

    Returns
    -------
    list of BaseChecker instances.
    """
    checkers: List[BaseChecker] = [
        DocStructureChecker(),
        SelfCheckReportChecker(),
        ParamUniquenessChecker(),
        ConfigFieldConsistencyChecker(),
        UnresolvedCrossReferenceChecker(),
        HardcodedValuePresenceChecker(),
    ]

    if max_layer >= 2:
        # Layer 2 checkers are injected via closed-source strategy pack
        pass

    return checkers
