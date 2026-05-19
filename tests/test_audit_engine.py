"""Tests for AuditEngine — orchestrator: register checkers, run, collect results."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from reusable_review_rules.audit_engine import AuditEngine
from reusable_review_rules.base_checker import BaseChecker, CheckResult
from reusable_review_rules.builtin_checkers import get_default_checkers
from reusable_review_rules.strategy_pack import StrategyPack


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

class AlwaysP2Checker(BaseChecker):
    id = 'test/always_p2'
    name = 'Always P2'
    description = 'Always reports a P2 issue.'
    severity = 'P2'
    layer = 2
    def check(self, document, tracker):
        return [CheckResult('P2', self.id, 'forced P2')]


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


def test_p2_collected():
    """P2 issues from registered checkers are collected."""
    engine = AuditEngine()
    engine.register(AlwaysP2Checker())
    audit = engine.run('doc')
    assert len(audit['P2']) == 1
    assert audit['P2'][0]['check_id'] == 'test/always_p2'
    print('  PASS P2 collected')


def test_layer_attribute_present():
    """Checkers have a 'layer' attribute for skip_layer filtering."""
    engine = AuditEngine()
    engine.register(AlwaysP0Checker())     # layer 0
    engine.register(AlwaysP1Checker())     # layer 1
    audit = engine.run('doc')
    assert len(audit['P0']) == 1
    assert len(audit['P1']) == 1
    print('  PASS layer attribute present on checkers')


def test_skip_layer_blocks_layer1():
    """skip_layer=1 should skip all checkers with layer >= 1."""
    engine = AuditEngine(skip_layer=1)
    engine.register(AlwaysP0Checker())     # layer 0 — should run
    engine.register(AlwaysP1Checker())     # layer 1 — should be skipped
    engine.register(AlwaysPassChecker())   # layer 1 — should be skipped
    audit = engine.run('doc')
    assert len(audit['P0']) == 1, 'P0 should still fire'
    assert len(audit['P1']) == 0, 'P1 should be skipped'
    assert 'test/always_p1' in audit['skipped']
    assert 'test/always_pass' in audit['skipped']
    print('  PASS skip_layer=1 blocks Layer 1 checkers')


def test_skip_layer_0_skips_all():
    """skip_layer=0 should skip all checkers (layer >= 0 is always true)."""
    engine = AuditEngine(skip_layer=0)
    engine.register(AlwaysP0Checker())
    engine.register(AlwaysP1Checker())
    audit = engine.run('doc')
    assert len(audit['P0']) == 0, 'P0 should be skipped'
    assert len(audit['P1']) == 0, 'P1 should be skipped'
    assert audit['checkers'] == []
    assert len(audit['skipped']) == 2
    print('  PASS skip_layer=0 skips all checkers')


def test_skip_layer_none_runs_all():
    """skip_layer=None (default) runs all registered checkers."""
    engine = AuditEngine()
    engine.register(AlwaysP0Checker())
    engine.register(AlwaysP1Checker())
    audit = engine.run('doc')
    assert len(audit['P0']) == 1
    assert len(audit['P1']) == 1
    assert audit['skipped'] == []
    print('  PASS skip_layer=None runs all')


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


def test_load_strategy_injects_checkers():
    """load_strategy() appends strategy checkers and injects prompts."""
    engine = AuditEngine()

    # Create a strategy pack with one checker and config
    checker = AlwaysP2Checker()
    pack = StrategyPack(
        prompts={'test/always_p2': {'main': 'check this'}},
        checkers=[checker],
        config={'max_iterations': 10},
    )
    engine.load_strategy(pack)
    ids = engine.checker_ids
    assert 'test/always_p2' in ids
    assert getattr(checker, '_strategy_prompts', None) == {'main': 'check this'}
    print('  PASS load_strategy injects checkers and prompts')


def test_load_strategy_config_accessible():
    """Config from strategy pack is accessible via get_config()."""
    engine = AuditEngine()
    pack = StrategyPack(
        prompts={},
        checkers=[],
        config={'max_iterations': 10, 'max_body_size': 9999},
    )
    engine.load_strategy(pack)
    assert engine.get_config('max_iterations') == 10
    assert engine.get_config('max_body_size') == 9999
    assert engine.get_config('nonexistent', 'default') == 'default'
    print('  PASS load_strategy config accessible')


def test_load_strategy_no_pack_returns_default():
    """get_config() returns default when no strategy pack loaded."""
    engine = AuditEngine()
    assert engine.get_config('max_iterations', 6) == 6
    print('  PASS get_config default without pack')


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
    test_p2_collected()
    test_layer_attribute_present()
    test_skip_layer_blocks_layer1()
    test_skip_layer_0_skips_all()
    test_skip_layer_none_runs_all()
    test_run_idempotent()
    test_duration_ms_nonzero()
    test_builtin_checkers_all()
    test_load_strategy_injects_checkers()
    test_load_strategy_config_accessible()
    test_load_strategy_no_pack_returns_default()
    print('\nAll audit_engine tests PASSED')
