"""
Strategy pack interface — closed-source extension contract.

The open-source framework ships with 6 built-in checkers (L0 + L1).
Closed-source strategy packs inject additional capabilities at
``AuditEngine.load_strategy(pack)`` time:

- Layer 2 checkers (LLM-based evidence collection, prompting)
- Custom configuration (max_iterations, max_body_size, etc.)
- Glossary definitions for content validation

Usage
-----
    from reusable_review_rules.strategy_pack import StrategyPack
    from reusable_review_rules.audit_engine import AuditEngine

    pack = StrategyPack.load("path/to/pack.yaml")
    engine = AuditEngine()
    engine.load_strategy(pack)

The ``StrategyPack`` class is part of the open-source framework so that
the interface contract is fixed even while the actual pack implementation
is closed-source.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

from reusable_review_rules.base_checker import BaseChecker


@dataclass
class StrategyPack:
    """Immutable configuration object injected into AuditEngine.

    Fields
    ------
    prompts : dict
        Mapping of ``{checker_id: {purpose: prompt_template}}``.
        Example: ``{"llm/arch_contradiction": {"main": "...", "cross_validate": "..."}}``.
        The inner dict keys are purposes (``"main"``, ``"cross_validate"``, etc.)
        and are consumed by the checker's ``_strategy_prompts`` attribute.
    checkers : list[BaseChecker]
        Additional checkers (typically Layer 2) to register.
        Each checker's ``_strategy_prompts`` attribute is set to the resolved
        prompts dict at registration time.
    config : dict
        Arbitrary configuration keys consumed by checkers or the pipeline:
          - ``max_iterations`` (int, default 6) — override Judge iteration cap
          - ``max_body_size`` (int, default 5000) — override CONFIG block scan limit
          - ``glossary`` (str, optional) — path to ``glossary.yaml``
    glossary_path : str or None
        Absolute path to a ``glossary.yaml`` file.  ``None`` if unused.
    """

    prompts: Dict[str, Dict[str, str]] = field(default_factory=dict)
    checkers: List[BaseChecker] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    glossary_path: Optional[str] = None

    @classmethod
    def load(cls, path: str) -> 'StrategyPack':
        """Load a strategy pack from a YAML file.

        The actual YAML parser is not part of the open-source framework.
        Subclasses or the closed-source pack must implement this method.
        """
        raise NotImplementedError(
            "StrategyPack.load() is not implemented in the open-source "
            "framework.  Use the closed-source pack or subclass StrategyPack."
        )

    def __post_init__(self):
        """Validate invariants."""
        for cid, purpose_map in self.prompts.items():
            if '/' not in cid:
                raise ValueError(
                    f"Prompt key '{cid}' must use dot-notation checker ID "
                    f"(e.g. 'llm/hardcoded_ip')."
                )
            if not isinstance(purpose_map, dict):
                raise ValueError(
                    f"Prompt value for '{cid}' must be a dict "
                    f"{{purpose: template}}, got {type(purpose_map).__name__}."
                )
        for c in self.checkers:
            if not hasattr(c, 'layer'):
                raise ValueError(
                    f"Checker '{c.id}' has no 'layer' attribute."
                )
