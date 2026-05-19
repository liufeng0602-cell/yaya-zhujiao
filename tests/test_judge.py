"""Tests for Judge — decision engine: P0/P1/P2 funnel + iteration cap."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from reusable_review_rules.judge import Judge, Decision


# ── Helpers ──────────────────────────────────────────────────────────

def make_report(p0: int = 0, p1: int = 0, p2: int = 0, duration_ms: float = 0.1) -> dict:
    return {
        'P0': ['issue'] * p0,
        'P1': ['issue'] * p1,
        'P2': ['issue'] * p2,
        'tracker': {'params': [], 'configs': [], 'errors': []},
        'checkers': [],
        'skipped': [],
        'duration_ms': duration_ms,
    }


# ── Decision type tests ──────────────────────────────────────────────

def test_decision_creation():
    d = Decision(state='needs_revision', reason='test', issue_counts={'P0': 1, 'P1': 0, 'P2': 0})
    assert d.state == 'needs_revision'
    assert d.reason == 'test'
    assert d.issue_counts['P0'] == 1
    print('  PASS decision creation')


def test_decision_repr():
    d = Decision(state='blocked', reason='too many', issue_counts={'P0': 0, 'P1': 0, 'P2': 0})
    r = repr(d)
    assert 'blocked' in r
    assert 'too many' in r
    print('  PASS decision repr')


def test_decision_to_dict():
    d = Decision(state='p2_clearing', reason='clear P2', issue_counts={'P0': 0, 'P1': 0, 'P2': 2})
    dd = d.to_dict()
    assert dd['state'] == 'p2_clearing'
    assert dd['reason'] == 'clear P2'
    print('  PASS decision to_dict')


def test_decision_from_dict():
    d = Decision.from_dict({'state': 'waiting_human_review', 'reason': 'clean', 'issue_counts': {'P0': 0, 'P1': 0, 'P2': 0}})
    assert d.state == 'waiting_human_review'
    print('  PASS decision from_dict')


# ── Judge decision branches ──────────────────────────────────────────

def test_clean_all_pass():
    d = Judge.evaluate(make_report(p0=0, p1=0, p2=0))
    assert d.state == 'waiting_human_review'
    print('  PASS clean -> waiting_human_review')


def test_p0_triggers_revision():
    d = Judge.evaluate(make_report(p0=1, p1=0, p2=0))
    assert d.state == 'needs_revision'
    print('  PASS P0 -> needs_revision')


def test_p1_triggers_revision():
    d = Judge.evaluate(make_report(p0=0, p1=1, p2=0))
    assert d.state == 'needs_revision'
    print('  PASS P1 -> needs_revision')


def test_p2_triggers_p2_clearing():
    d = Judge.evaluate(make_report(p0=0, p1=0, p2=1))
    assert d.state == 'p2_clearing'
    print('  PASS P2 -> p2_clearing')


def test_p0_dominates_p1():
    """P0 > 0 should dominate even when P1/P2 also present."""
    d = Judge.evaluate(make_report(p0=1, p1=5, p2=10))
    assert d.state == 'needs_revision'
    assert 'P0' in d.reason
    print('  PASS P0 dominates P1/P2')


def test_all_zero_without_counts():
    """Empty report dict should be treated as clean."""
    d = Judge.evaluate({'P0': [], 'P1': [], 'P2': []})
    assert d.state == 'waiting_human_review'
    print('  PASS empty report -> waiting_human_review')


# ── Iteration cap tests ──────────────────────────────────────────────

def test_iteration_below_cap_is_revision():
    d = Judge.evaluate(make_report(p0=1), iteration=5)
    assert d.state == 'needs_revision'
    print('  PASS iteration=5, P0>0 -> needs_revision')


def test_iteration_at_cap_is_blocked():
    d = Judge.evaluate(make_report(p0=1), iteration=6)
    assert d.state == 'blocked'
    print('  PASS iteration=6, P0>0 -> blocked')


def test_iteration_above_cap_is_blocked():
    d = Judge.evaluate(make_report(p1=1), iteration=7)
    assert d.state == 'blocked'
    print('  PASS iteration=7, P1>0 -> blocked')


def test_iteration_cap_clean_not_blocked():
    """Clean document at iteration cap should NOT be blocked."""
    d = Judge.evaluate(make_report(p0=0, p1=0, p2=0), iteration=6)
    assert d.state == 'waiting_human_review'
    print('  PASS iteration=6, clean -> waiting_human_review (not blocked)')


def test_iteration_over_cap_clean_not_blocked():
    d = Judge.evaluate(make_report(p0=0, p1=0, p2=0), iteration=10)
    assert d.state == 'waiting_human_review'
    print('  PASS iteration=10, clean -> waiting_human_review (not blocked)')


def test_custom_max_iterations():
    """max_iterations=3 should block at iteration >= 3."""
    d = Judge.evaluate(make_report(p0=1), iteration=3, max_iterations=3)
    assert d.state == 'blocked'
    d2 = Judge.evaluate(make_report(p0=1), iteration=2, max_iterations=3)
    assert d2.state == 'needs_revision'
    print('  PASS custom max_iterations=3 respected')


def test_max_iterations_zero_is_clamped():
    """max_iterations=0 should be clamped to 1, not block on first pass."""
    d = Judge.evaluate(make_report(p0=1), iteration=0, max_iterations=0)
    # Clamped to 1: iteration=0 < 1, so not blocked
    assert d.state == 'needs_revision', f"Expected needs_revision, got {d.state}"
    d2 = Judge.evaluate(make_report(p0=1), iteration=1, max_iterations=0)
    # iteration=1 >= clamped max_iterations=1 -> blocked
    assert d2.state == 'blocked', f"Expected blocked, got {d2.state}"
    print('  PASS max_iterations=0 clamped to 1')


def test_should_block_property():
    """Decision.should_block is True for needs_revision and blocked."""
    for state in ('needs_revision', 'blocked'):
        d = Decision(state=state, reason='x', issue_counts={'P0': 0, 'P1': 0, 'P2': 0})
        assert d.should_block is True, f"{state}.should_block should be True"
    for state in ('p2_clearing', 'waiting_human_review'):
        d = Decision(state=state, reason='x', issue_counts={'P0': 0, 'P1': 0, 'P2': 0})
        assert d.should_block is False, f"{state}.should_block should be False"
    print('  PASS should_block property')


def test_is_clean_property():
    """Decision.is_clean is True only for waiting_human_review."""
    d = Decision(state='waiting_human_review', reason='x', issue_counts={'P0': 0, 'P1': 0, 'P2': 0})
    assert d.is_clean is True
    for state in ('needs_revision', 'blocked', 'p2_clearing'):
        d = Decision(state=state, reason='x', issue_counts={'P0': 0, 'P1': 0, 'P2': 0})
        assert d.is_clean is False, f"{state}.is_clean should be False"
    print('  PASS is_clean property')


# ── Run all ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('=== test_judge ===')
    test_decision_creation()
    test_decision_repr()
    test_decision_to_dict()
    test_decision_from_dict()
    test_clean_all_pass()
    test_p0_triggers_revision()
    test_p1_triggers_revision()
    test_p2_triggers_p2_clearing()
    test_p0_dominates_p1()
    test_all_zero_without_counts()
    test_iteration_below_cap_is_revision()
    test_iteration_at_cap_is_blocked()
    test_iteration_above_cap_is_blocked()
    test_iteration_cap_clean_not_blocked()
    test_iteration_over_cap_clean_not_blocked()
    test_custom_max_iterations()
    test_max_iterations_zero_is_clamped()
    test_should_block_property()
    test_is_clean_property()
    print('\nAll judge tests PASSED')
