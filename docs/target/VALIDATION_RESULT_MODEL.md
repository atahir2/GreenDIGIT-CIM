# Validation Result Model

> **Milestone 9**

```text
ValidationResult
  rule_name: str
  passed: bool
  severity: info | warning | error | critical
  message: optional str
  rule_type: optional str
  target_registry: optional str
  details: dict
  is_blocking → not passed and severity in {error, critical}
```

Aggregated as `RuleEvaluationResult` with `results`, `warnings`, `errors`, `has_critical`.
