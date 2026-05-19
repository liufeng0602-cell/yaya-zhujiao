#!/usr/bin/env python3
"""
Closed-source strategy pack loader.

Produces a populated ``StrategyPack`` instance from the YAML files in
``closed_source_pack/`` directory.

Usage::

    from closed_source_pack.pack_loader import load_closed_source_pack

    pack = load_closed_source_pack()
    engine = AuditEngine()
    engine.load_strategy(pack)
    report = engine.run(document_text)

Four responsibilities:
1. Parse ``rules_prd.yaml``, ``rules_tech_doc.yaml`` and any other ``rules_*.yaml``
2. Load prompts from ``prompts/`` (recursive, all ``.yaml`` files)
3. Load ``glossary.yaml`` if present
4. Build ``BaseChecker`` instances from the parsed rules
"""

import os
import re
import functools
from typing import Dict, List, Any, Optional

import yaml

from reusable_review_rules.strategy_pack import StrategyPack
from reusable_review_rules.base_checker import BaseChecker, CheckResult


# ── constants ───────────────────────────────────────────────────────

PACK_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_DIR = os.path.join(PACK_DIR, "prompts")
GLOSSARY_PATH = os.path.join(PACK_DIR, "glossary.yaml")


# ════════════════════════════════════════════════════════════════════
# Glossary helpers
# ════════════════════════════════════════════════════════════════════


_GLOSSARY_CACHE: Optional[dict] = None


def _load_glossary_if_available() -> Optional[dict]:
    """Load and cache glossary.yaml.  Returns None if absent or unparseable."""
    global _GLOSSARY_CACHE
    if _GLOSSARY_CACHE is not None:
        return _GLOSSARY_CACHE
    if not os.path.isfile(GLOSSARY_PATH):
        _GLOSSARY_CACHE = None
        return None
    try:
        with open(GLOSSARY_PATH) as fh:
            _GLOSSARY_CACHE = yaml.safe_load(fh)
        return _GLOSSARY_CACHE
    except Exception:
        _GLOSSARY_CACHE = None
        return None


def _lookup_glossary_term(glossary: dict, param_name: str) -> Optional[dict]:
    """Find a glossary term by its *english* name matching the PARAM name.

    Also matches by aliases list.
    """
    for term in glossary.get('terms', []):
        eng = term.get('english', '')
        if eng.lower() == param_name.lower():
            return term
        for alias in term.get('aliases', []):
            if alias.lower() == param_name.lower():
                return term
    return None


def _validate_param_against_term(
    severity: str,
    check_id: str,
    param_name: str,
    param_value: str,
    term: dict,
    location: Optional[int],
) -> List[CheckResult]:
    """Validate a single PARAM value against its glossary term definition.

    Checks:
    - ``min`` / ``max`` range constraints
    - ``allowed_values`` enum constraints
    """
    issues: List[CheckResult] = []

    # Parse the value
    val: Any = param_value
    term_type = term.get('type', 'string')
    try:
        if term_type == 'integer':
            val = int(param_value)
        elif term_type == 'float':
            val = float(param_value)
    except (ValueError, TypeError):
        # Unparseable value (e.g. "30s" with units) — report as P2 advisory
        issues.append(CheckResult(
            severity='P2',
            check_id=check_id,
            msg=f"PARAM '{param_name}={param_value}' has unparseable format — "
                f"value-range validation skipped (expected {term_type})",
            evidence=param_value,
        ))
        return issues

    # Range check
    constraints = term.get('constraints', {})
    min_v = constraints.get('min')
    max_v = constraints.get('max')
    if min_v is not None and isinstance(val, (int, float)):
        if val < min_v:
            issues.append(CheckResult(
                severity=severity,
                check_id=check_id,
                msg=f"PARAM '{param_name}={param_value}' below minimum {min_v} "
                    f"(defined in glossary term '{term.get('name', '')}')",
                location=location,
                evidence=param_value,
            ))
    if max_v is not None and isinstance(val, (int, float)):
        if val > max_v:
            issues.append(CheckResult(
                severity=severity,
                check_id=check_id,
                msg=f"PARAM '{param_name}={param_value}' exceeds maximum {max_v} "
                    f"(defined in glossary term '{term.get('name', '')}')",
                location=location,
                evidence=param_value,
            ))

    # Enum check
    allowed = term.get('allowed_values')
    if allowed is not None and isinstance(param_value, str):
        if param_value not in allowed:
            issues.append(CheckResult(
                severity=severity,
                check_id=check_id,
                msg=f"PARAM '{param_name}={param_value}' not in allowed values {allowed} "
                    f"(defined in glossary term '{term.get('name', '')}')",
                location=location,
                evidence=param_value,
            ))

    return issues


# ════════════════════════════════════════════════════════════════════
# Checker factory registry  — check_type → factory function
# ════════════════════════════════════════════════════════════════════

_CHECKER_FACTORIES: Dict[str, callable] = {}


def _register_factory(check_type: str):
    """Decorator to register a checker factory."""
    def wrapper(fn):
        _CHECKER_FACTORIES[check_type] = fn
        return fn
    return wrapper


def _get_factory(check_type: str) -> Optional[callable]:
    return _CHECKER_FACTORIES.get(check_type)


# ════════════════════════════════════════════════════════════════════
# section_presence — check that required section headings/markers exist
# ════════════════════════════════════════════════════════════════════

@_register_factory('section_presence')
def _factory_section_presence(rule: dict) -> BaseChecker:
    required = rule['params']['required']

    class _Checker(BaseChecker):
        id = rule['id']
        name = rule['name']
        description = rule['description']
        severity = rule['severity']
        layer = rule['layer']
        _rule = rule

        def check(self, document: str, tracker: dict) -> List[CheckResult]:
            if not _should_trigger(self._rule, document, tracker):
                return []
            issues: List[CheckResult] = []
            lines = document.split('\n')
            for section in required:
                found = False
                if section.startswith('<') and section.endswith('>'):
                    # Angle-bracket marker, e.g. <self_check_report>
                    found = section in document
                else:
                    # Markdown heading
                    pattern = r'^#{1,4}\s+' + re.escape(section) + r'\s*$'
                    if re.search(pattern, document, re.MULTILINE):
                        found = True
                if not found:
                    loc = None
                    for i, line in enumerate(lines, 1):
                        if line.startswith('#'):
                            loc = i
                            break
                    issues.append(CheckResult(
                        severity=self.severity,
                        check_id=self.id,
                        msg=f"Missing required section: {section}",
                        location=loc,
                        evidence=section,
                    ))
            return issues

    return _Checker()


# ════════════════════════════════════════════════════════════════════
# section_coverage — validate content quality of a section
# ════════════════════════════════════════════════════════════════════

@_register_factory('section_coverage')
def _factory_section_coverage(rule: dict) -> BaseChecker:
    section = rule['params'].get('section', '')
    criteria = rule['params'].get('quality_criteria', [])

    class _Checker(BaseChecker):
        id = rule['id']
        name = rule['name']
        description = rule['description']
        severity = rule['severity']
        layer = rule['layer']
        _rule = rule

        def check(self, document: str, tracker: dict) -> List[CheckResult]:
            if not _should_trigger(self._rule, document, tracker):
                return []
            issues: List[CheckResult] = []
            if not section:
                return issues

            heading_pat = r'^#{1,4}\s+' + re.escape(section) + r'\s*$'
            match = re.search(heading_pat, document, re.MULTILINE)
            if not match:
                return issues  # L0 already flagged this

            # Extract content after heading until next heading or end
            start = match.end()
            section_level = match.group().count('#')
            remaining = document[start:]
            next_heading = re.search(r'^#{1,' + str(section_level) + r'}\s', remaining, re.MULTILINE)
            content = remaining[:next_heading.start()] if next_heading else remaining
            content = content.strip()

            if not content:
                issues.append(CheckResult(
                    severity=self.severity,
                    check_id=self.id,
                    msg=f"Section '{section}' exists but is empty",
                    location=document[:start].count('\n') + 1,
                ))
                return issues

            for criterion in criteria:
                if '具体' in criterion and '默认值' in criterion:
                    # Check for presence of table-like content (key-value pairs)
                    if not re.search(r'\|.*\|', content) and not re.search(r'\w+\s*[:：]\s*\w+', content):
                        issues.append(CheckResult(
                            severity=self.severity,
                            check_id=self.id,
                            msg=f"Section '{section}' should contain concrete default value entries",
                            location=document[:start].count('\n') + 1,
                        ))
                        break

            return issues

    return _Checker()


# ════════════════════════════════════════════════════════════════════
# value_range — validate PARAM values against glossary constraints
# ════════════════════════════════════════════════════════════════════

@_register_factory('value_range')
def _factory_value_range(rule: dict) -> BaseChecker:

    class _Checker(BaseChecker):
        id = rule['id']
        name = rule['name']
        description = rule['description']
        severity = rule['severity']
        layer = rule['layer']
        _rule = rule

        def check(self, document: str, tracker: dict) -> List[CheckResult]:
            if not _should_trigger(self._rule, document, tracker):
                return []
            issues: List[CheckResult] = []
            glossary = _load_glossary_if_available()
            if not glossary:
                return issues

            params = tracker.get('params', [])
            for p in params:
                name = p.get('name', '')
                value = p.get('value', '')
                term = _lookup_glossary_term(glossary, name)
                if not term:
                    continue
                issues.extend(_validate_param_against_term(
                    self.severity, self.id, name, value, term, p.get('location'),
                ))

            # If cross_check is set, also validate same-term consistency
            cross = rule['params'].get('cross_check')
            if cross == 'same_doc':
                from reusable_review_rules.hardcoded_tracker import param_values_by_name
                for term_name, values in param_values_by_name(tracker).items():
                    if len(set(values)) > 1:
                        issues.append(CheckResult(
                            severity=self.severity,
                            check_id=self.id,
                            msg=f"PARAM '{term_name}' has inconsistent values: {values}",
                            evidence=str(values),
                        ))

            return issues

    return _Checker()


# ════════════════════════════════════════════════════════════════════
# term_consistency — check that terms are not using unapproved aliases
# ════════════════════════════════════════════════════════════════════

@_register_factory('term_consistency')
def _factory_term_consistency(rule: dict) -> BaseChecker:

    class _Checker(BaseChecker):
        id = rule['id']
        name = rule['name']
        description = rule['description']
        severity = rule['severity']
        layer = rule['layer']
        _rule = rule

        def check(self, document: str, tracker: dict) -> List[CheckResult]:
            if not _should_trigger(self._rule, document, tracker):
                return []
            issues: List[CheckResult] = []
            glossary = _load_glossary_if_available()
            if not glossary:
                return issues

            # Build a single regex per term: match any alias but not where standard also appears
            # This avoids O(terms × aliases × lines) triple nesting
            lines = document.split('\n')
            for term in glossary.get('terms', []):
                standard = term.get('name', '')
                if not standard:
                    continue
                aliases = term.get('aliases', [])
                if not aliases:
                    continue
                # Build pattern: any of the aliases, but on a line that does NOT contain the standard term
                escaped = [re.escape(a) for a in aliases]
                alias_pat = '(' + '|'.join(escaped) + ')'
                for i, line in enumerate(lines, 1):
                    if alias_pat not in line:
                        # Quick skip — re.search is slower than 'in' for non-matches
                        continue
                    if standard in line:
                        # Standard and alias both present on the same line — could be intentional
                        continue
                    m = re.search(alias_pat, line)
                    if m:
                        issues.append(CheckResult(
                            severity=self.severity,
                            check_id=self.id,
                            msg=f"Use standard term '{standard}' instead of alias '{aliases}'",
                            location=i,
                            evidence=line.strip()[:80],
                        ))
                        break  # One issue per term per line is enough

            return issues

    return _Checker()


# ════════════════════════════════════════════════════════════════════
# cross_field_consistency — validate that the same field has same value
# ════════════════════════════════════════════════════════════════════

@_register_factory('cross_field_consistency')
def _factory_cross_field(rule: dict) -> BaseChecker:
    pairs = rule['params'].get('pairs', [])
    if not pairs:
        # Fallback: try document_header_vs_changelog_version heuristic
        pairs = [
            {
                'source': 'document.header.version',
                'target': 'document.changelog.latest_version',
                'description': 'Header version should match changelog latest version',
            }
        ]

    class _Checker(BaseChecker):
        id = rule['id']
        name = rule['name']
        description = rule['description']
        severity = rule['severity']
        layer = rule['layer']
        _rule = rule

        def check(self, document: str, tracker: dict) -> List[CheckResult]:
            if not _should_trigger(self._rule, document, tracker):
                return []
            issues: List[CheckResult] = []
            lines = document.split('\n')
            for pair in pairs:
                source_desc = pair.get('source', '')
                target_desc = pair.get('target', '')
                desc = pair.get('description', '')
                source_val = None
                target_val = None
                if 'version' in source_desc and 'version' in target_desc:
                    # Match "version: X.Y" in the header area (within first 20 lines)
                    for i in range(min(20, len(lines))):
                        m = re.search(r'version\s*[:：]\s*([\d.]+)', lines[i])
                        if m:
                            source_val = m.group(1)
                            break
                    # Match changelog heading like "## 2.0"
                    for line in lines:
                        m = re.search(r'^##\s+([\d.]+)', line)
                        if m:
                            target_val = m.group(1)
                    if source_val and target_val and source_val != target_val:
                        issues.append(CheckResult(
                            severity=self.severity,
                            check_id=self.id,
                            msg=f"{desc}: header v{source_val} != changelog v{target_val}",
                        ))
            return issues

    return _Checker()


# ════════════════════════════════════════════════════════════════════
# llm_evidence — stub for Layer 2 LLM-based checks
# ════════════════════════════════════════════════════════════════════

@_register_factory('llm_evidence')
def _factory_llm_evidence(rule: dict) -> BaseChecker:
    prompt_id = rule['params'].get('prompt_id', '')

    class _Checker(BaseChecker):
        id = rule['id']
        name = rule['name']
        description = rule['description']
        severity = rule['severity']
        layer = rule['layer']
        _rule = rule

        # TODO: When implementing real LLM evidence checks in closed-source extension:
        # 1. Inject prompt from StrategyPack.prompts into _strategy_prompts
        # 2. Use self._strategy_prompts[prompt_id] in check() to call LLM
        # 3. Remove the stub return below
        _strategy_prompts: Dict[str, str] = {}

        def check(self, document: str, tracker: dict) -> List[CheckResult]:
            if not _should_trigger(self._rule, document, tracker):
                return []
            return [CheckResult(
                severity='P2',
                check_id=self.id,
                msg=f"LLM evidence check '{prompt_id}' not yet implemented (stub)",
            )]

    return _Checker()


# ════════════════════════════════════════════════════════════════════
# Trigger-check helpers
# ════════════════════════════════════════════════════════════════════


def _should_trigger(rule: dict, document: str, tracker: dict) -> bool:
    """Determine whether this rule should fire given its trigger type."""
    trigger = rule.get('trigger', 'always')
    params = rule.get('params', {})

    if trigger == 'always':
        return True

    if trigger == 'on_doc_flag':
        flag = params.get('flag', '')
        # Check doc_flags from self-check report
        report = _extract_self_check_flags(document)
        return flag in report.get('doc_flags', [])

    if trigger == 'on_term':
        term_refs = params.get('term_refs', [])
        for ref in term_refs:
            if ref in document:
                return True
        return False

    if trigger == 'on_pattern':
        pattern = params.get('pattern', '')
        if pattern:
            return bool(re.search(pattern, document))
        return False

    return True


def _extract_self_check_flags(document: str) -> dict:
    """Extract doc_flags from the <self_check_report> YAML block."""
    m = re.search(r'<self_check_report>\s*(.*?)\s*</self_check_report>', document, re.DOTALL)
    if not m:
        return {'doc_flags': []}
    try:
        data = yaml.safe_load(m.group(1))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {'doc_flags': []}


# ════════════════════════════════════════════════════════════════════
# Prompt loading
# ════════════════════════════════════════════════════════════════════


_PROMPTS_CACHE: Optional[Dict[str, Dict[str, str]]] = None


def _load_prompts() -> Dict[str, Dict[str, str]]:
    """Scan prompts/ recursively and load all .yaml prompt files.

    Results are cached in the module-level ``_PROMPTS_CACHE`` so repeated
    calls from the same process avoid re-parsing YAML.

    Returns:
        {prompt_id: {"main": "...", "cross_validate": "...", ...}}
    """
    global _PROMPTS_CACHE
    if _PROMPTS_CACHE is not None:
        return _PROMPTS_CACHE

    prompts: Dict[str, Dict[str, str]] = {}
    if not os.path.isdir(PROMPTS_DIR):
        _PROMPTS_CACHE = prompts
        return prompts

    for root, dirs, files in os.walk(PROMPTS_DIR):
        for fname in sorted(files):
            if not fname.endswith('.yaml'):
                continue
            fpath = os.path.join(root, fname)
            # Compute prompt_id = relative path without extension
            rel = os.path.relpath(fpath, PROMPTS_DIR)
            prompt_id = rel.replace('.yaml', '')
            try:
                with open(fpath) as fh:
                    data = yaml.safe_load(fh)
                if not isinstance(data, dict) or 'main' not in data:
                    continue
                prompts[prompt_id] = data
            except Exception:
                continue

    _PROMPTS_CACHE = prompts
    return prompts


# ════════════════════════════════════════════════════════════════════
# Rules -> checkers
# ════════════════════════════════════════════════════════════════════


_RULES_CACHE: Optional[List[BaseChecker]] = None


def _build_checker(rule: dict) -> Optional[BaseChecker]:
    """Build a single BaseChecker from a parsed rule dict.

    Returns None if the check_type is unknown or the rule is deprecated.
    """
    if rule.get('status') == 'deprecated':
        return None

    factory = _get_factory(rule.get('check_type', ''))
    if factory is None:
        return None

    return factory(rule)


def _load_rules_from_file(fpath: str) -> List[BaseChecker]:
    """Parse a rules_*.yaml file and build all active checkers."""
    with open(fpath) as fh:
        data = yaml.safe_load(fh)

    checkers: List[BaseChecker] = []
    for rule in data.get('rules', []):
        checker = _build_checker(rule)
        if checker is not None:
            checkers.append(checker)
    return checkers


def _load_all_rules() -> List[BaseChecker]:
    """Scan PACK_DIR for rules_*.yaml files and load all checkers.

    Results are cached in the module-level ``_RULES_CACHE`` so repeated
    calls from the same process avoid re-parsing YAML.
    """
    global _RULES_CACHE
    if _RULES_CACHE is not None:
        return _RULES_CACHE

    checkers: List[BaseChecker] = []
    for fname in sorted(os.listdir(PACK_DIR)):
        if fname.startswith('rules_') and fname.endswith('.yaml'):
            fpath = os.path.join(PACK_DIR, fname)
            try:
                checkers.extend(_load_rules_from_file(fpath))
            except Exception:
                continue

    _RULES_CACHE = checkers
    return checkers


# ════════════════════════════════════════════════════════════════════
# Public API
# ════════════════════════════════════════════════════════════════════


def load_closed_source_pack() -> StrategyPack:
    """Load the entire closed-source strategy pack.

    Steps:
    1. Load all rules_*.yaml → build BaseChecker instances
    2. Load prompts/ → populate prompts dict
    3. Load glossary.yaml → set glossary_path
    4. Assemble and return StrategyPack instance
    """
    # 1. Checkers from rules
    checkers = _load_all_rules()

    # 2. Prompts
    prompts = _load_prompts()

    # 3. Glossary path
    glossary_path = GLOSSARY_PATH if os.path.isfile(GLOSSARY_PATH) else None

    # 4. Config (hardcoded defaults for now — can be externalised later)
    config = {
        'max_iterations': 6,
        'max_body_size': 5000,
    }

    # Filter out rules that are stubs / not-yet-implemented check_types
    # by removing None entries
    checkers = [c for c in checkers if c is not None]

    return StrategyPack(
        prompts=prompts,
        prompts_dir=PROMPTS_DIR if os.path.isdir(PROMPTS_DIR) else None,
        checkers=checkers,
        config=config,
        glossary_path=glossary_path,
    )
