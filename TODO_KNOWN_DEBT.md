# Known debt — deferred items (next iteration)

## Test coverage

- [ ] HardcodedValueTracker: value containing `]` truncation behavior
  Input `[PARAM:desc=foo]bar]` → value is `foo`, losing `bar]`
  Need: test documenting current behavior as intentional constraint
  Severity: P2 — low risk, only affects malformed (non-YAML) inputs

- [ ] SelfCheckReportValidator: deep nesting recursion limit
  YAML-like parser uses regex-based recursive descent for nested dicts
  Test: 100-level nested dict should not trigger Python recursion limit
  Severity: P2 — only affects adversarial/report-poisoning scenarios

- [ ] HardcodedValueTracker: value containing `]` truncation test
  Same test as above, in test_hardcoded_tracker.py

## Architecture

- [ ] StrategyPack `_strategy_prompts` attribute discoverability
  The injection exists (audit_engine.py:120) but attribute name is `_strategy_prompts`
  A Layer 2 checker developer writing `self.prompts` will get AttributeError
  Options: add alias property `prompts` on BaseChecker, or document in BaseChecker class

## Documentation

- [ ] Add BaseChecker docstring noting `_strategy_prompts` attribute
