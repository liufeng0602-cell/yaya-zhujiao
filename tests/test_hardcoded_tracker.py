"""Tests for HardcodedValueTracker — zero-dep [PARAM]/[CONFIG] scanner."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from reusable_review_rules.hardcoded_tracker import scan, param_values_by_name, config_fields_by_entity


# ── PARAM tests ──────────────────────────────────────────────────────

def test_empty_document():
    result = scan('')
    assert result['params'] == []
    assert result['configs'] == []
    assert result['errors'] == []
    print('  PASS empty document')


def test_param_single():
    result = scan('[PARAM:timeout=30]')
    assert len(result['params']) == 1
    assert result['params'][0]['name'] == 'timeout'
    assert result['params'][0]['value'] == '30'
    print('  PASS single PARAM')


def test_param_multiple():
    doc = '[PARAM:timeout=30]\n[PARAM:max_retries=3]'
    result = scan(doc)
    assert len(result['params']) == 2
    names = [p['name'] for p in result['params']]
    assert 'timeout' in names
    assert 'max_retries' in names
    print('  PASS multiple PARAMs')


def test_param_value_with_equals():
    doc = '[PARAM:url=https://example.com/api?key=abc]'
    result = scan(doc)
    assert len(result['params']) == 1
    assert result['params'][0]['name'] == 'url'
    assert result['params'][0]['value'] == 'https://example.com/api?key=abc'
    print('  PASS PARAM value with =')


def test_param_no_match():
    result = scan('plain text without markers')
    assert result['params'] == []
    print('  PASS no PARAM match')


# ── CONFIG tests ─────────────────────────────────────────────────────

def test_config_single():
    doc = '[CONFIG:database]\nhost: localhost\nport: 5432\n[/CONFIG]'
    result = scan(doc)
    assert len(result['configs']) == 1
    assert result['configs'][0]['entity'] == 'database'
    assert result['configs'][0]['fields']['host'] == 'localhost'
    assert result['configs'][0]['fields']['port'] == '5432'
    print('  PASS single CONFIG block')


def test_config_multiple_same_entity():
    doc = (
        '[CONFIG:database]\nhost: localhost\nport: 5432\n[/CONFIG]\n'
        '[CONFIG:database]\nhost: prod\nport: 5432\nssl: true\n[/CONFIG]'
    )
    result = scan(doc)
    assert len(result['configs']) == 2
    assert result['configs'][0]['entity'] == 'database'
    assert result['configs'][1]['entity'] == 'database'
    print('  PASS multiple CONFIG same entity')


def test_config_no_entity_match():
    result = scan('[CONFIG:unknown]\nplaceholder: true\n[/CONFIG]')
    assert len(result['configs']) == 1
    assert result['configs'][0]['fields'] == {'placeholder': 'true'}
    print('  PASS CONFIG with one field')


def test_config_line_number():
    doc = 'line1\n[CONFIG:db]\nkey: val\n[/CONFIG]'
    result = scan(doc)
    assert result['configs'][0]['line'] == 2
    print('  PASS CONFIG line number')


# ── Large body protection ────────────────────────────────────────────

def test_config_body_too_large():
    """CONFIG block with body > 5000 chars should NOT match (avoid backtracking)."""
    long_body = 'x: 1\n' * 2000  # ~12000 chars
    doc = f'[CONFIG:big]\n{long_body}\n[/CONFIG]'
    result = scan(doc)
    # Block is too large, shouldn't match
    assert len(result['configs']) == 0
    print('  PASS CONFIG large body skipped')


# ── Aggregator tests ─────────────────────────────────────────────────

def test_param_values_by_name():
    doc = '[PARAM:x=1]\n[PARAM:x=2]\n[PARAM:y=3]'
    result = scan(doc)
    by_name = param_values_by_name(result)
    assert len(by_name['x']) == 2
    assert by_name['x'] == ['1', '2']
    assert by_name['y'] == ['3']
    print('  PASS param_values_by_name')


def test_config_fields_by_entity():
    doc = (
        '[CONFIG:db]\na: 1\nb: 2\n[/CONFIG]\n'
        '[CONFIG:db]\na: 3\n[/CONFIG]'
    )
    result = scan(doc)
    by_entity = config_fields_by_entity(result)
    assert len(by_entity['db']) == 2
    assert set(by_entity['db'][0].keys()) == {'a', 'b'}
    assert set(by_entity['db'][1].keys()) == {'a'}
    print('  PASS config_fields_by_entity')


# ── Run all ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('=== test_hardcoded_tracker ===')
    test_empty_document()
    test_param_single()
    test_param_multiple()
    test_param_value_with_equals()
    test_param_no_match()
    test_config_single()
    test_config_multiple_same_entity()
    test_config_no_entity_match()
    test_config_line_number()
    test_config_body_too_large()
    test_param_values_by_name()
    test_config_fields_by_entity()
    print('\nAll hardcoded_tracker tests PASSED')
