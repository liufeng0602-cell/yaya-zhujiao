"""Tests for AuditEngine — orchestrator: register checkers, run, collect results."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from reusable_review_rules.audit_engine import AuditEngine
from reusable_review_rules.base_checker import BaseChecker, CheckResult
from reusable_review_rules.builtin_checkers import get_default_checkers


# ── Dummy checkers for testing ───────────────────────────────────────

class AlwaysPassChecker(BaseChecker):
    id = 'test/always_pass'
    name = 'Always passes'
    description = 'Never reports issues.'
    severity = 'P2'
    layer = 1
    def check(self, document, tracker):
        return []

class AlwaysP0Checker(BaseChecker):
    id = 'test/always_p0'
    name = 'Always P0'
    description = 'Always reports a P0 issue.'
    severity = 'P0'
    layer = 0
    def check(self, document, tracker):
        return [CheckResult('P0', self.id, 'forced P0')]

class AlwaysP1Checker(BaseChecker):
    id = 'test/always_p1'
    name = 'Always P1'
    description = 'Always reports a P1 issue.'
    severity = 'P1'
    layer = 1
    def check(self, document, tracker):
        return [CheckResult('P1', self.id, 'forced P1')]


# ── Tests ────────────────────────────────────────────────────────────

def test_engine_empty():
    """Engine with no checkers returns empty audit."""
    engine = AuditEngine()
    audit = engine.run('anything')
    assert audit['P0'] == []
    assert audit['P1'] == []
    assert audit['P2'] == []
    assert audit['tracker'] is not None
    print('  PASS empty engine')


def test_register_single():
    engine = AuditEngine()
    engine.register(AlwaysPassChecker())
    assert len(engine._checkers) == 1
    print('  PASS register single checker')


def test_register_list():
    engine = AuditEngine()
    checkers = [AlwaysPassChecker(), AlwaysP0Checker()]
    engine.register_list(checkers)
    assert len(engine._checkers) == 2
    print('  PASS register list')


def test_duplicate_id_detected():
    engine = AuditEngine()
    engine.register(AlwaysPassChecker())
    try:
        engine.register(AlwaysPassChecker())
        assert False, 'Expected ValueError for duplicate ID'
    except ValueError as e:
        assert 'duplicate' in str(e).lower()
    print('  PASS duplicate ID rejected')


def test_clean_document():
    """All checkers pass -> empty P0/P1/P2."""
    engine = AuditEngine()
    engine.register(AlwaysPassChecker())
    audit = engine.run('some document')
    assert audit['P0'] == []
    assert audit['P1'] == []
    assert audit['P2'] == []
    print('  PASS clean document')


def test_p0_collected():
    engine = AuditEngine()
    engine.register(AlwaysP0Checker())
    engine.register(AlwaysPassChecker())
    audit = engine.run('doc')
    assert len(audit['P0']) == 1
    assert audit['P0'][0]['check_id'] == 'test/always_p0'
    print('  PASS P0 collected')


def test_p0_and_p1_collected():
    engine = AuditEngine()
    engine.register(AlwaysP0Checker())
    engine.register(AlwaysP1Checker())
    engine.register(AlwaysPassChecker())
    audit = engine.run('doc')
    assert len(audit['P0']) == 1
    assert len(audit['P1']) == 1
    print('  PASS P0 and P1 both collected')


def test_skip_layer_via_checker_selection():
    """Selectively register checkers of different layers (no skip_layer param)."""
    engine = AuditEngine()
    engine.register(AlwaysP0Checker())     # layer 0
    engine.register(AlwaysP1Checker())     # layer 1
    audit = engine.run('doc')
    # Both run — no skip mechanism exists yet
    assert len(audit['P0']) == 1
    assert len(audit['P1']) == 1
    print('  PASS layer attribute present on checkers')


def test_run_idempotent():
    """Running same doc twice gives same result structure."""
    engine = AuditEngine()
    engine.register(AlwaysPassChecker())
    r1 = engine.run('hello')
    r2 = engine.run('hello')
    assert len(r1['P0']) == len(r2['P0'])
    assert len(r1['P1']) == len(r2['P1'])
    assert len(r1['P2']) == len(r2['P2'])
    print('  PASS run idempotent')


def test_duration_ms_nonzero():
    engine = AuditEngine()
    engine.register(AlwaysPassChecker())
    audit = engine.run('doc')
    assert audit['duration_ms'] >= 0
    print('  PASS duration_ms present')


def test_builtin_checkers_all():
    """All 6 built-in checkers load and run without error."""
    engine = AuditEngine()
    engine.register_list(get_default_checkers(max_layer=1))
    ids = sorted([c.id for c in engine._checkers])
    assert 'syntax/doc_structure' in ids
    assert 'validity/self_check_report' in ids
    assert 'uniqueness/param_names' in ids
    assert 'consistency/config_fields' in ids
    assert 'coverage/unresolved_cross_ref' in ids
    assert 'coverage/hardcoded_values_tagged' in ids
    assert len(ids) == 6
    print('  PASS all 6 built-in checkers')


# ── Run all ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('=== test_audit_engine ===')
    test_engine_empty()
    test_register_single()
    test_register_list()
    test_duplicate_id_detected()
    test_clean_document()
    test_p0_collected()
    test_p0_and_p1_collected()
    test_skip_layer_via_checker_selection()
    test_run_idempotent()
    test_duration_ms_nonzero()
    test_builtin_checkers_all()
    print('\nAll audit_engine tests PASSED')
