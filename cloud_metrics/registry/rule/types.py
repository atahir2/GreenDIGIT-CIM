"""Rule Registry — types (Milestone 9)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

SEVERITIES = ("info", "warning", "error", "critical")


@dataclass
class RuleEntry:
    """Declarative validation rule definition."""

    name: str
    description: Optional[str] = None
    rule_type: Optional[str] = None
    target_registry: Optional[str] = None
    condition: Dict[str, Any] = field(default_factory=dict)
    severity: str = "error"  # info | warning | error | critical
    status: str = "active"
    id: Optional[int] = None
    review_status: str = "approved"
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Structured outcome of applying one rule to a metric context."""

    rule_name: str
    passed: bool
    severity: str = "info"
    message: Optional[str] = None
    rule_type: Optional[str] = None
    target_registry: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_blocking(self) -> bool:
        return (not self.passed) and self.severity in {"error", "critical"}


@dataclass
class RuleEvaluationResult:
    """Aggregate rule evaluation for one orchestration pass."""

    results: List[ValidationResult] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    has_critical: bool = False

    @property
    def ok(self) -> bool:
        return not self.has_critical and not any(
            r.is_blocking for r in self.results
        )
