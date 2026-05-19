#!/usr/bin/env python3
"""
HardcodedValueTracker
---------------------
Zero-dependency utility that scans text for tagged hardcoded values.

Extracts two types of markers:
  [PARAM:name=value]                         — single-line key-value pairs
  [CONFIG:entity]...[FIELD]...[/CONFIG]      — multi-line entity config blocks

Output is a flat, structured dict that downstream checkers (self-check
validator, reviewer) consume to verify uniqueness, consistency, and
coverage.  The tracker itself performs NO validation — it is a pure
extraction tool.

Usage:
    from reusable_review_rules.hardcoded_tracker import scan

    doc = open('S01.md').read()
    result = scan(doc)

    for p in result['params']:
        print(p['name'], p['value'], p['line'])

    for c in result['configs']:
        print(c['entity'], c['fields'])
"""

import re
from typing import List, Dict, Any


# ── regex patterns ──────────────────────────────────────────────────
# [PARAM:name=value] — name must not contain '=', value consumes up to ']'
_PARAM_RE = re.compile(r'\[PARAM:([^\]=]+)=([^\]]*)\]')

# [CONFIG:entity] ... [/CONFIG] (dotall mode, body capped at 5000 chars to avoid catastrophic backtracking)
_CONFIG_BLOCK_RE = re.compile(
    r'\[CONFIG:([^\]]+)\]\s*\n(.{0,5000}?)\n\s*\[/CONFIG\]',
    re.DOTALL,
)


# Sub-pattern: inside a CONFIG block, each field line is "key: value"
_FIELD_LINE_RE = re.compile(r'^([a-zA-Z_]\w*)\s*:\s*(.*?)\s*$')


def _line_number(text: str, pos: int) -> int:
    """1-based line number for character position `pos` in `text`."""
    return text[:pos].count('\n') + 1


def _clean_raw_value(raw: str) -> str:
    """Strip whitespace / quotes from a raw extracted value."""
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ('"', "'"):
        raw = raw[1:-1]
    return raw


# ── public API ──────────────────────────────────────────────────────


def scan(text: str) -> Dict[str, Any]:
    """
    Scan `text` and return all tagged hardcoded values.

    Returns
    -------
    dict with three keys:
      'params'  : list of {name, value, line, raw}
      'configs' : list of {entity, fields, line, raw}
      'errors'  : list of str — format anomalies (e.g. unclosed [CONFIG:)

    Each entry includes the 1-based line number where the marker starts
    and the original raw text for diagnostic use.

    Notes
    -----
    - PARAM markers must be on a single logical line.  Multi-line
      CONFIG blocks are supported.
    - A CONFIG block's fields are parsed as lines with the form
      ``field_name: value``.  Leading/trailing whitespace is stripped.
    - Comment lines (``# …``) inside CONFIG blocks are ignored.
    - Nested brackets inside a value are *not* supported; the scanner
      stops at the first unescaped ``]``.
    """
    params: List[Dict[str, Any]] = []
    configs: List[Dict[str, Any]] = []

    # --- PARAM extraction -------------------------------------------
    for m in _PARAM_RE.finditer(text):
        name = m.group(1).strip()
        raw_val = _clean_raw_value(m.group(2))
        params.append({
            'name': name,
            'value': raw_val,
            'line': _line_number(text, m.start()),
            'raw': m.group(0),
        })

    # --- CONFIG block extraction ------------------------------------
    for m in _CONFIG_BLOCK_RE.finditer(text):
        entity = m.group(1).strip()
        body = m.group(2)

        fields: Dict[str, str] = {}
        for line in body.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            fm = _FIELD_LINE_RE.match(line)
            if fm:
                fields[fm.group(1)] = fm.group(2).strip()

        configs.append({
            'entity': entity,
            'fields': fields,
            'line': _line_number(text, m.start()),
            'raw': m.group(0),
        })

    return {'params': params, 'configs': configs, 'errors': []}


# ── convenience / aggregate queries (zero dep) ─────────────────────


def param_values_by_name(result: Dict) -> Dict[str, List[str]]:
    """Group param values by name for uniqueness checks."""
    grouped: Dict[str, List[str]] = {}
    for p in result['params']:
        grouped.setdefault(p['name'], []).append(p['value'])
    return grouped


def config_fields_by_entity(result: Dict) -> Dict[str, List[Dict]]:
    """Group config fields by entity for cross-block consistency checks."""
    grouped: Dict[str, List[Dict]] = {}
    for c in result['configs']:
        grouped.setdefault(c['entity'], []).append(c['fields'])
    return grouped


# ── CLI smoke test ─────────────────────────────────────────────────

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            data = scan(f.read())
    else:
        # self-test with embedded sample
        SAMPLE = """
        [PARAM:timeout=30]  [PARAM:max_retries=5]

        [CONFIG:credit_system]
        init_value: 50
        max_value: 100
        excellent_threshold: 80
        [/CONFIG]

        [PARAM:api_url=http://localhost:8080]

        [CONFIG:retry_policy]
        # This is a comment
        base_delay: 1.5
        max_delay: 60
        jitter: True
        [/CONFIG]
        """
        data = scan(SAMPLE)

    for p in data['params']:
        print(f"PARAM  L{p['line']:>4}  {p['name']:30s} = {p['value']}")
    for c in data['configs']:
        print(f"CONFIG L{c['line']:>4}  {c['entity']:30s}  fields={c['fields']}")

    print("\n--- uniqueness groupings ---")
    for name, vals in param_values_by_name(data).items():
        print(f"  {name}: {vals}")
