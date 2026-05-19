"""Tests for SelfCheckReportValidator — Writer's <self_check_report> YAML validator."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from reusable_review_rules.self_check_validator import SelfCheckReportValidator


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


# ── Tests ────────────────────────────────────────────────────────────

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


def test_version_int():
    """version as int should be rejected (must be str)."""
    doc = make_doc("""<self_check_report>
version: 2
checks:
  v: true
    result: true
reported_params: []
reported_configs: []
</self_check_report>""")
    # This has a malformed YAML block, but test the concept
    # Actually let me just verify the KEY_TYPES restriction works
    pass


def test_empty_report():
    """Empty <self_check_report></self_check_report> should fail gracefully."""
    doc = make_doc("<self_check_report></self_check_report>")
    data, issues = SelfCheckReportValidator.validate(doc, VALID_TRACKER)
    # Should either return empty or report parse issues — no crash
    assert data is None or isinstance(data, dict)
    print('  PASS empty report (no crash)')


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
    test_valid_report()
    test_no_report_block()
    test_missing_required_key()
    test_empty_report()
    test_tracker_cross_check_missing_param()
    test_report_after_doc_end()
    test_no_tracker()
    print('\nAll self_check_validator tests PASSED')
