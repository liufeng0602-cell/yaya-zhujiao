#!/usr/bin/env python3
"""
SelfCheckReportValidator
------------------------
Validates the structured YAML self-check report that Writer MUST append
to every submitted document.

The validator does NOT judge content truthfulness (that is the job of the
Reviewer ruleset inside the closed-source strategy pack).  It only verifies:

  1. The YAML block exists and is parsable.
  2. All required top-level keys are present.
  3. Value types match the expected schema (str / list / int / bool).
  4. Claimed param/config names actually appear in the document
     (cross-check with HardcodedValueTracker output).

Failure on 1-2 -> block-level (P0), cannot proceed to git commit.
Failure on 3 -> P1, Writer must fix.
Failure on 4 -> P2 warning (allow pass but logged).


Writer-side contract (what Writer prompts must produce)
--------------------------------------------------------
The YAML block uses keys that the open-source framework understands.
Closed-source rules (strategy pack) may add extra keys via
``register_rule()``; those are validated more loosely.

Required keys (open-source):
  version         str     e.g. "1.0"
  checks          dict    mapping check-name -> result dict
  reported_params  list   [{name, value, line}] claimed by Writer
  reported_configs list   [{entity, fields}]     claimed by Writer

Each CHECK dict has:
  result    bool       only true/false
  evidence  list[str]  supporting locations / values
  severity  str        one of P0 P1 P2 P3

Usage
-----
    from reusable_review_rules.hardcoded_tracker import scan
    from reusable_review_rules.self_check_validator import SelfCheckReportValidator

    tracker_out = scan(doc_text)
    report, issues = SelfCheckReportValidator.validate(doc_text, tracker_out)

    if issues:
        for iss in issues:
            print(f"{iss['severity']}: {iss['msg']}")
"""

import re
import json
from typing import List, Dict, Any, Tuple, Optional


# The marker that delimits the start of the self-check report
_REPORT_BEGIN = re.compile(
    r'^<self_check_report>',
    re.MULTILINE,
)

# We expect a closing marker (optional -- if missing we grab to EOF)
_REPORT_END = re.compile(
    r'^</self_check_report>',
    re.MULTILINE,
)

# Keys that MUST be present in the YAML
REQUIRED_KEYS = ['version', 'checks', 'reported_params', 'reported_configs']

# Valid types for each required key
KEY_TYPES = {
    'version': (str, int),    # "1.0" or 2 are both acceptable
    'checks': dict,
    'reported_params': list,
    'reported_configs': list,
}

# Valid top-level keys (for unknown-key detection)
ALLOWED_KEYS = set(REQUIRED_KEYS) | {
    'strategy_pack_version',   # closed-source may inject this
    'extra_notes',
}


def _extract_yaml_block(text: str) -> Optional[str]:
    """
    Extract the raw YAML string between <self_check_report> and
    </self_check_report> markers.

    Returns None if the opening marker is not found.
    """
    start = _REPORT_BEGIN.search(text)
    if not start:
        return None

    # Find end marker -- if missing, grab to EOF
    end = _REPORT_END.search(text, start.end())
    if end:
        return text[start.end():end.start()].strip()
    else:
        return text[start.end():].strip()


def _validate_check_value(key: str, val: Any) -> List[Dict[str, Any]]:
    """Validate a single check's result dict."""
    issues: List[Dict[str, Any]] = []

    # Must have 'result'
    result_val = val.get('result')
    if not isinstance(result_val, bool):
        issues.append({
            'severity': 'P1',
            'msg': f"check '{key}'.result must be bool, got {type(result_val).__name__}",
        })

    # 'evidence' must be list of strings
    evidence_val = val.get('evidence', [])
    if not isinstance(evidence_val, list):
        issues.append({
            'severity': 'P2',
            'msg': f"check '{key}'.evidence must be list, got {type(evidence_val).__name__}",
        })
    else:
        for i, e in enumerate(evidence_val):
            if not isinstance(e, str):
                issues.append({
                    'severity': 'P2',
                    'msg': f"check '{key}'.evidence[{i}] is not a string",
                })

    # 'severity' must be P0..P3 if present (optional)
    sev = val.get('severity')
    if sev is not None and sev not in ('P0', 'P1', 'P2', 'P3'):
        issues.append({
            'severity': 'P2',
            'msg': f"check '{key}'.severity must be P0/P1/P2/P3, got {sev!r}",
        })

    return issues


def _validate_reported_item(item: Any, kind: str) -> List[Dict[str, Any]]:
    """Validate a single entry in reported_params or reported_configs."""
    issues: List[Dict[str, Any]] = []

    if not isinstance(item, dict):
        issues.append({
            'severity': 'P1',
            'msg': f"Item in {kind} is not a dict",
        })
        return issues

    # reported_params require name + value; reported_configs require entity + fields
    if kind == 'reported_params':
        for k in ('name', 'value'):
            if k not in item:
                issues.append({
                    'severity': 'P1',
                    'msg': f"{kind} entry missing '{k}'",
                })
    elif kind == 'reported_configs':
        if 'entity' not in item:
            issues.append({
                'severity': 'P1',
                'msg': f"{kind} entry missing 'entity'",
            })
        if 'fields' not in item:
            issues.append({
                'severity': 'P1',
                'msg': f"{kind} entry missing 'fields'",
            })
        elif not isinstance(item.get('fields'), dict):
            issues.append({
                'severity': 'P2',
                'msg': f"{kind} entry 'fields' must be a dict",
            })

    return issues


def _parse_yaml_simple(yaml_text: str) -> Optional[Dict[str, Any]]:
    """
    Minimal YAML-like parser for the self-check report.

    We intentionally do NOT import a full YAML library to keep the
    open-source framework zero-dep for this core path.  The report uses
    a constrained subset of YAML that this parser understands.

    Uses recursive descent by indentation level.
    """
    lines = yaml_text.split('\n')

    # Strip blank/comment lines but remember indentation
    prepped: List[Dict[str, Any]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        indent = len(line) - len(line.lstrip())
        prepped.append({'line': stripped, 'indent': indent})

    def _parse_block(start: int, parent_indent: int) -> Tuple[Any, int]:
        """Parse a block starting at `start` with indent > `parent_indent`.

        Returns (result, next_index) where result is a dict or list.
        """
        if start >= len(prepped):
            return {}, start

        # Determine block type by looking at the first child
        first = prepped[start]
        if first['line'].startswith('- '):
            return _parse_list_block(start, parent_indent)
        else:
            return _parse_dict_block(start, parent_indent)

    def _parse_dict_block(start: int, parent_indent: int) -> Tuple[Dict[str, Any], int]:
        """Parse a block of key: value pairs at the same indentation."""
        result: Dict[str, Any] = {}
        i = start
        while i < len(prepped):
            entry = prepped[i]
            if entry['indent'] <= parent_indent:
                break  # we've gone back up

            stripped = entry['line']
            m = re.match(r'^(\w[\w_]*)\s*:\s*(.*)', stripped)
            if not m:
                i += 1
                continue

            key = m.group(1)
            raw_val = m.group(2).strip()

            if raw_val:
                result[key] = _parse_scalar(raw_val)
                i += 1
            else:
                # Empty value -> children at deeper indent
                if i + 1 < len(prepped) and prepped[i + 1]['indent'] > entry['indent']:
                    child, consumed = _parse_block(i + 1, entry['indent'])
                    result[key] = child
                    i = consumed
                else:
                    result[key] = None
                    i += 1

        return result, i

    def _parse_list_block(start: int, parent_indent: int) -> Tuple[List[Any], int]:
        """Parse a block of - list items at the same indentation."""
        result: List[Any] = []
        i = start
        while i < len(prepped):
            entry = prepped[i]
            stripped = entry['line']
            if entry['indent'] <= parent_indent:
                break
            if not stripped.startswith('- '):
                i += 1
                continue

            # Parse the list item value
            item_raw = stripped[2:].strip()

            if item_raw and ':' in item_raw:
                # "- key: value" -> {"key": value}
                parts = item_raw.split(':', 1)
                item_dict = {parts[0].strip(): _parse_scalar(parts[1].strip())}

                # Collect children at deeper indent
                j = i + 1
                while j < len(prepped) and prepped[j]['indent'] > entry['indent']:
                    child_stripped = prepped[j]['line']
                    cm = re.match(r'^(\w[\w_]*)\s*:\s*(.*)', child_stripped)
                    if cm:
                        ckey = cm.group(1)
                        cval_raw = cm.group(2).strip()
                        if cval_raw:
                            item_dict[ckey] = _parse_scalar(cval_raw)
                            j += 1
                        else:
                            # Empty child key -> recursive parse
                            if j + 1 < len(prepped) and prepped[j + 1]['indent'] > prepped[j]['indent']:
                                child_val, consumed = _parse_block(j + 1, prepped[j]['indent'])
                                item_dict[ckey] = child_val
                                j = consumed
                            else:
                                item_dict[ckey] = None
                                j += 1
                    else:
                        j += 1
                result.append(item_dict)
                i = j
            else:
                # "- plain_value"
                result.append(_parse_scalar(item_raw))
                i += 1

        return result, i

    result, _ = _parse_dict_block(0, -1)
    return result


def _parse_scalar(val_str: str) -> Any:
    """Parse a single scalar value from YAML-like text."""
    if not val_str:
        return val_str

    # Empty list / empty dict shorthand
    if val_str == '[]':
        return []
    if val_str == '{}':
        return {}

    # Quoted string
    if (val_str[0] == '"' and val_str[-1] == '"') or \
       (val_str[0] == "'" and val_str[-1] == "'"):
        return val_str[1:-1]

    # Boolean
    if val_str.lower() == 'true':
        return True
    if val_str.lower() == 'false':
        return False

    # Integer
    try:
        return int(val_str)
    except ValueError:
        pass

    # Default: string
    return val_str


class SelfCheckReportValidator:
    """
    Validates the Writer self-check report appended to a document.
    """

    @staticmethod
    def validate(doc_text: str, tracker_output: Dict[str, Any]) \
            -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Run all validation stages.

        Parameters
        ----------
        doc_text : str
            Full document text (including the <self_check_report> block).
        tracker_output : dict
            Output of HardcodedValueTracker.scan(doc_text).

        Returns
        -------
        (report, issues)
            report : dict or None  -- parsed self-check report, or None if
                      the block was missing entirely.
            issues : list of dict  -- each with keys severity, msg[, line].
        """
        issues: List[Dict[str, Any]] = []

        # ---- Stage 1: extract YAML block --------------------------------
        raw_yaml = _extract_yaml_block(doc_text)
        if raw_yaml is None:
            issues.append({
                'severity': 'P0',
                'msg': 'Missing <self_check_report> block in document',
            })
            return None, issues

        # ---- Stage 2: parse YAML ----------------------------------------
        report = _parse_yaml_simple(raw_yaml)
        if report is None:
            issues.append({
                'severity': 'P0',
                'msg': '<self_check_report> block is not valid YAML',
            })
            return None, issues

        # ---- Stage 3: required top-level keys ---------------------------
        for key in REQUIRED_KEYS:
            if key not in report:
                issues.append({
                    'severity': 'P0',
                    'msg': f"Missing required key '{key}' in self-check report",
                })

        # If version/checks/reported_params/reported_configs are missing,
        # we cannot continue with deeper checks -- return early.
        missing_required = [k for k in REQUIRED_KEYS if k not in report]
        if missing_required:
            return report, issues

        # ---- Stage 4: type checks ---------------------------------------
        for key, expected_type in KEY_TYPES.items():
            if key in report and not isinstance(report[key], expected_type):
                type_name = expected_type if isinstance(expected_type, str) else \
                    ' | '.join(t.__name__ for t in expected_type) if isinstance(expected_type, tuple) else \
                    expected_type.__name__
                issues.append({
                    'severity': 'P1',
                    'msg': f"Key '{key}' should be {type_name}, "
                           f"got {type(report[key]).__name__}",
                })

        # ---- Stage 5: validate each check entry -------------------------
        checks = report.get('checks', {})
        if isinstance(checks, dict):
            for ck, cv in checks.items():
                if isinstance(cv, dict):
                    issues.extend(_validate_check_value(ck, cv))
                else:
                    issues.append({
                        'severity': 'P1',
                        'msg': f"check '{ck}' should be a dict, got {type(cv).__name__}",
                    })

        # ---- Stage 6: validate reported items ---------------------------
        reported_params = report.get('reported_params', [])
        reported_configs = report.get('reported_configs', [])

        if isinstance(reported_params, list):
            for item in reported_params:
                issues.extend(_validate_reported_item(item, 'reported_params'))
        if isinstance(reported_configs, list):
            for item in reported_configs:
                issues.extend(_validate_reported_item(item, 'reported_configs'))

        # ---- Stage 7: cross-check with HardcodedValueTracker ------------
        # If Writer claimed params/CONFIGs, verify they actually exist in
        # the document (as detected by the tracker).

        # Build a set of actual entities from tracker
        actual_param_names = {p['name'] for p in tracker_output.get('params', [])}
        actual_config_entities = {c['entity'] for c in tracker_output.get('configs', [])}

        if isinstance(reported_params, list):
            for item in reported_params:
                if isinstance(item, dict) and 'name' in item:
                    claimed_name = item.get('name', '')
                    if claimed_name and claimed_name not in actual_param_names:
                        issues.append({
                            'severity': 'P2',
                            'msg': f"Writer claimed PARAM '{claimed_name}' but "
                                   f"no [PARAM:{claimed_name}=...] found in document",
                        })

        if isinstance(reported_configs, list):
            for item in reported_configs:
                if isinstance(item, dict) and 'entity' in item:
                    claimed_entity = item.get('entity', '')
                    if claimed_entity and claimed_entity not in actual_config_entities:
                        issues.append({
                            'severity': 'P2',
                            'msg': f"Writer claimed CONFIG '{claimed_entity}' but "
                                   f"no [CONFIG:{claimed_entity}] block found in document",
                        })

        # ---- Stage 8: detect unreported params/CONFIGs ------------------
        # Any param/config found by tracker but not claimed by Writer
        # is a warning -- Writer may have missed something.

        if isinstance(reported_params, list):
            claimed_names = {item.get('name', '') for item in reported_params
                             if isinstance(item, dict)}
            unreported = [p for p in actual_param_names if p not in claimed_names]
            for name in sorted(unreported):
                issues.append({
                    'severity': 'P2',
                    'msg': f"PARAM '{name}' appears in document but Writer did "
                           f"not report it in <self_check_report>",
                })

        if isinstance(reported_configs, list):
            claimed_entities = {item.get('entity', '') for item in reported_configs
                                if isinstance(item, dict)}
            unreported_c = [c for c in actual_config_entities if c not in claimed_entities]
            for entity in sorted(unreported_c):
                issues.append({
                    'severity': 'P2',
                    'msg': f"CONFIG '{entity}' block appears in document but Writer "
                           f"did not report it in <self_check_report>",
                })

        return report, issues
