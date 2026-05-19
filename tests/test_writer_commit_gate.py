"""
Tests for Writer commit gate — self_check_commit_gate in writer.py

Three scenarios:
1. Doc without <self_check_report> block → commit blocked
2. Doc with valid self-check report → commit passes
3. Doc with P2 warnings → commit passes with warning
"""

import sys
import os
import tempfile
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.writer import (
    self_check_commit_gate,
    _auto_repair_self_check,
    _fallback_to_drafting,
    _log_gate_failure,
    PROJECT, KANBAN_DIR,
)
from kanban_ops import (
    get_task, add_comment,
    create_task, update_task_status, get_comments,
)


# ── Helpers ─────────────────────────────────────────────────────────

TEST_PROJECT = 'yaya-zhujiao'


def _make_valid_doc() -> str:
    """Create a document with a valid self-check report."""
    return """# Test Document

## Content

Some content with [PARAM:timeout=30] and [PARAM:retries=3].

[CONFIG:database]
host: localhost
port: 5432
[/CONFIG]

<self_check_report>
version: '1.0'
checks:
  value_audit:
    result: true
    note: all good
reported_params:
  - name: timeout
    value: '30'
    location: '## Content'
  - name: retries
    value: '3'
    location: '## Content'
reported_configs:
  - entity: database
    fields:
      host: localhost
      port: '5432'
    location: '## Content'
</self_check_report>
"""


def _make_no_report_doc() -> str:
    """Document without any self-check report block."""
    return """# Test Document

## Content

Some content here.

No self check report in this document.
"""


def _make_p2_warning_doc() -> str:
    """Document with valid report but P2 issues: unreported param."""
    return """# Test Document

## Content

Some content with [PARAM:timeout=30] and [PARAM:unreported_param=xyz].

<self_check_report>
version: '1.0'
checks:
  value_audit:
    result: true
    note: all good
reported_params:
  - name: timeout
    value: '30'
    location: '## Content'
reported_configs: []
</self_check_report>
"""


def _make_missing_keys_doc() -> str:
    """Document with self-check report missing required keys (P0)."""
    return """# Test Document

<self_check_report>
version: '1.0'
checks: {}
</self_check_report>
"""


def _make_type_error_doc() -> str:
    """Document with type errors: version as int, result as string."""
    return """# Test Document

## Content

Some content with [PARAM:timeout=30].

<self_check_report>
version: 2
checks:
  value_audit:
    result: "yes"
    note: bad type
reported_params:
  - name: timeout
    value: '30'
reported_configs: []
</self_check_report>
"""


# ── Test: gate blocks doc without self-check report ─────────────────

def test_gate_blocks_no_report():
    """
    Scenario: Writer submits a doc without <self_check_report> block.
    Expected: gate returns False, task falls back to drafting.
    """
    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(_make_no_report_doc())
        tmp_path = f.name

    try:
        # Create a test task in kanban
        tid = create_task(TEST_PROJECT, 'test_gate_blocks_no_report',
                          file_path=tmp_path, version='v1.0')
        update_task_status(TEST_PROJECT, tid, 'drafting', assigned_to='writer')

        # Run gate
        result = self_check_commit_gate(tmp_path, tid, 'test_gate_blocks_no_report')

        # Assert gate blocked
        assert result is False, f"Expected False (blocked), got {result}"

        # Assert task fell back to drafting
        task = get_task(TEST_PROJECT, tid)
        assert task['status'] == 'drafting', (
            f"Expected status 'drafting' after gate block, got '{task['status']}'"
        )

        # Assert gate failure comment exists
        comments = get_comments(TEST_PROJECT, tid)
        gate_comments = [c for c in comments if '门禁' in c.get('content', '')]
        assert len(gate_comments) >= 1, (
            f"Expected at least one gate-related comment, got {len(gate_comments)}"
        )

        print(f'  PASS gate blocks doc without self-check report')

    finally:
        os.unlink(tmp_path)


# ── Test: gate passes doc with valid self-check report ──────────────

def test_gate_passes_valid_report():
    """
    Scenario: Writer submits a doc with valid <self_check_report> block.
    Expected: gate returns True, commit proceeds.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(_make_valid_doc())
        tmp_path = f.name

    try:
        tid = create_task(TEST_PROJECT, 'test_gate_passes_valid_report',
                          file_path=tmp_path, version='v1.0')
        update_task_status(TEST_PROJECT, tid, 'drafting', assigned_to='writer')

        result = self_check_commit_gate(tmp_path, tid, 'test_gate_passes_valid_report')

        assert result is True, f"Expected True (pass), got {result}"

        # Task status should remain drafting (gate doesn't change it on pass)
        task = get_task(TEST_PROJECT, tid)
        assert task['status'] == 'drafting', (
            f"Expected status 'drafting' after gate pass, got '{task['status']}'"
        )

        print(f'  PASS gate passes valid self-check report')

    finally:
        os.unlink(tmp_path)


# ── Test: gate passes with P2 warnings ──────────────────────────────

def test_gate_passes_with_p2_warnings():
    """
    Scenario: Writer submits a doc with valid self-check report but P2 issues
    (unreported param). Expected: gate returns True with warning log.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(_make_p2_warning_doc())
        tmp_path = f.name

    try:
        tid = create_task(TEST_PROJECT, 'test_gate_passes_with_p2_warnings',
                          file_path=tmp_path, version='v1.0')
        update_task_status(TEST_PROJECT, tid, 'drafting', assigned_to='writer')

        result = self_check_commit_gate(tmp_path, tid,
                                        'test_gate_passes_with_p2_warnings')

        assert result is True, f"Expected True (pass with P2 warnings), got {result}"

        print(f'  PASS gate passes with P2 warnings')

    finally:
        os.unlink(tmp_path)


# ── Test: gate auto-repairs P1 type errors ──────────────────────────

def test_gate_auto_repairs_type_errors():
    """
    Scenario: Writer submits a doc with P1 type errors (version as int, result as string).
    Expected: gate auto-repairs, returns True with repaired file.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(_make_type_error_doc())
        tmp_path = f.name

    try:
        tid = create_task(TEST_PROJECT, 'test_gate_auto_repairs_type_errors',
                          file_path=tmp_path, version='v1.0')
        update_task_status(TEST_PROJECT, tid, 'drafting', assigned_to='writer')

        result = self_check_commit_gate(tmp_path, tid,
                                        'test_gate_auto_repairs_type_errors')

        assert result is True, f"Expected True (auto-repaired), got {result}"

        # Verify file was repaired: version should be quoted
        with open(tmp_path) as f:
            content = f.read()
        assert "version: '2'" in content, (
            f"Expected version to be quoted after repair: {content[:500]}"
        )
        assert "result: true" in content or "result: false" in content, (
            f"Expected result to be bool after repair: {content[:500]}"
        )

        print(f'  PASS gate auto-repairs P1 type errors')

    finally:
        os.unlink(tmp_path)


# ── Test: auto_repair_self_check handles missing keys ───────────────

def test_auto_repair_missing_keys():
    """
    Given a doc with missing required keys in self-check report,
    _auto_repair_self_check should insert defaults.
    """
    doc = _make_missing_keys_doc()
    issues = [
        {'severity': 'P0', 'msg': "Missing required key 'reported_params'"},
        {'severity': 'P0', 'msg': "Missing required key 'reported_configs'"},
    ]

    repaired = _auto_repair_self_check(doc, issues)

    assert repaired is not None, "Expected repaired doc, got None"
    assert 'reported_params: []' in repaired, (
        "Expected reported_params: [] to be inserted"
    )
    assert 'reported_configs: []' in repaired, (
        "Expected reported_configs: [] to be inserted"
    )
    # Original content preserved
    assert "Test Document" in repaired

    print(f'  PASS auto_repair adds missing required keys')


# ── Run all ─────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('=== test_writer_commit_gate ===')

    test_gate_blocks_no_report()
    test_gate_passes_valid_report()
    test_gate_passes_with_p2_warnings()
    test_gate_auto_repairs_type_errors()
    test_auto_repair_missing_keys()

    print('\nAll writer commit gate tests PASSED')
