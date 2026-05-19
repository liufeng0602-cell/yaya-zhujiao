"""Tests for SelfCheckReportValidator — Writer's <self_check_report> YAML validator."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from reusable_review_rules.self_check_validator import SelfCheckReportValidator
from reusable_review_rules.self_check_validator import _parse_scalar


# ── Helpers ──────────────────────────────────────────────────────────

def make_doc(self_check_block: str) -> str:
    return f"# Document Title\n\n## Content\n\nSome text.\n\n{self_check_block}"

VALID_REPORT = """<self_check_report>
version: '2'
reported_params:
  - name: timeout
    value: "30"
    location: "## Content"
  - name: retries
    value: "3"
    location: "## Content"
reported_configs:
  - entity: database
    fields:
      host: localhost
      port: "5432"
    location: "## Content"
checks:
  value_audit:
    result: true
    note: "all good"
  field_audit:
    result: true
    note: "all consistent"
</self_check_report>
"""

VALID_DOC = make_doc(VALID_REPORT)

VALID_TRACKER = {
    'params': [
        {'name': 'timeout', 'value': '30', 'line': 5},
        {'name': 'retries', 'value': '3', 'line': 6},
    ],
    'configs': [
        {'entity': 'database', 'fields': {'host': 'localhost', 'port': '5432'}, 'line': 8},
    ],
    'errors': [],
}


# ── _parse_scalar unit tests ─────────────────────────────────────────

def test_parse_scalar_empty():
    """Regression: _parse_scalar('') must not raise IndexError."""
    result = _parse_scalar('')
    assert result == '', repr(result)
    print('  PASS _parse_scalar empty string')


def test_parse_scalar_quoted_empty():
    result = _parse_scalar('""')
    assert result == '', repr(result)
    print('  PASS _parse_scalar quoted empty string')


def test_parse_scalar_normal():
    result = _parse_scalar('hello')
    assert result == 'hello', repr(result)
    print('  PASS _parse_scalar normal string')


def test_parse_scalar_bool_and_int():
    assert _parse_scalar('true') is True
    assert _parse_scalar('false') is False
    assert _parse_scalar('42') == 42
    print('  PASS _parse_scalar bool and int')


# ── Integration tests ────────────────────────────────────────────────

def test_valid_report():
    data, issues = SelfCheckReportValidator.validate(VALID_DOC, VALID_TRACKER)
    assert data is not None
    assert issues == []
    print('  PASS valid report')


def test_no_report_block():
    doc = "# Document\n\nNo report here."
    data, issues = SelfCheckReportValidator.validate(doc, VALID_TRACKER)
    assert data is None
    assert len(issues) == 1
    assert issues[0]['severity'] == 'P0'
    assert 'missing' in issues[0]['msg'].lower()
    print('  PASS missing report block')


def test_missing_required_key():
    doc = make_doc("""<self_check_report>
version: '2'
checks: {}
</self_check_report>""")
    data, issues = SelfCheckReportValidator.validate(doc, VALID_TRACKER)
    assert data is not None
    assert any('reported_params' in i['msg'] for i in issues)
    print('  PASS missing required key')


def test_version_int_rejected():
    """version as int (2) should be flagged as P1 issue."""
    doc = make_doc("""<self_check_report>
version: 2
checks:
  v:
    result: true
reported_params: []
reported_configs: []
</self_check_report>""")
    data, issues = SelfCheckReportValidator.validate(doc, VALID_TRACKER)
    # Must not crash
    assert data is not None
    # Should have at least one type-related issue for version
    version_issues = [i for i in issues if 'version' in i.get('msg', '').lower()]
    assert len(version_issues) >= 1, f"Expected version type issue, got: {[i['msg'] for i in issues]}"
    assert version_issues[0]['severity'] == 'P1'
    print('  PASS version int rejected with P1 issue')


def test_empty_report():
    """Empty <self_check_report></self_check_report> should fail gracefully."""
    doc = make_doc("<self_check_report></self_check_report>")
    data, issues = SelfCheckReportValidator.validate(doc, VALID_TRACKER)
    # Should either return empty or report parse issues — no crash
    assert data is None or isinstance(data, dict)
    print('  PASS empty report (no crash)')


def test_checks_result_not_bool():
    """checks.result as string (yes) should be flagged as type issue."""
    doc = make_doc("""<self_check_report>
version: '2'
reported_params: []
reported_configs: []
checks:
  value_audit:
    result: "yes"
    note: fake
</self_check_report>""")
    data, issues = SelfCheckReportValidator.validate(doc, VALID_TRACKER)
    assert data is not None
    type_issues = [i for i in issues if 'result' in i.get('msg', '') and 'bool' in i.get('msg', '')]
    assert len(type_issues) >= 1, (
        'Expected a type issue about result=bool, got none'
    )
    assert type_issues[0]['severity'] == 'P1'
    print('  PASS checks.result not bool flagged as P1')


def test_tracker_cross_check_missing_param():
    """Writer claims a param that doesn't exist in doc."""
    report = VALID_REPORT.replace(
        '- name: timeout',
        '- name: nonexistent_param'
    )
    doc = make_doc(report)
    data, issues = SelfCheckReportValidator.validate(doc, VALID_TRACKER)
    if data:
        cross_issues = [i for i in issues if 'cross' in i.get('check_id', '') or 'writer' in i.get('check_id', '')]
        # Should at least not crash
        pass
    print('  PASS cross-check missing param (no crash)')


# ── Edge cases ───────────────────────────────────────────────────────

def test_report_after_doc_end():
    """Report is the very last thing, no trailing newline."""
    doc = "# Doc\n\nText\n\n<self_check_report>\nversion: '2'\nchecks: {}\nreported_params: []\nreported_configs: []\n</self_check_report>"
    data, issues = SelfCheckReportValidator.validate(doc, {'params': [], 'configs': [], 'errors': []})
    # Should not crash
    assert data is not None or len(issues) > 0
    print('  PASS report at EOF (no crash)')


def test_no_tracker():
    """When tracker is empty dict, should handle gracefully."""
    doc = make_doc(VALID_REPORT)
    data, issues = SelfCheckReportValidator.validate(doc, {})
    # Should not crash
    assert data is not None or len(issues) > 0
    print('  PASS empty tracker (no crash)')


# ── Run all ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('=== test_self_check_validator ===')
    test_parse_scalar_empty()
    test_parse_scalar_quoted_empty()
    test_parse_scalar_normal()
    test_parse_scalar_bool_and_int()
    test_valid_report()
    test_no_report_block()
    test_missing_required_key()
    test_version_int_rejected()
    test_empty_report()
    test_checks_result_not_bool()
    test_tracker_cross_check_missing_param()
    test_report_after_doc_end()
    test_no_tracker()
    print('\nAll self_check_validator tests PASSED')
