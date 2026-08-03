"""Rule Registry — base types (Milestone 1 skeleton)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RuleEntry:
    """Declarative validation rule definition."""

    name: str
    description: Optional[str] = None
    rule_type: Optional[str] = None  # required_field, type_check, range_check, ...
    target_registry: Optional[str] = None
    condition: Dict[str, Any] = field(default_factory=dict)
    severity: str = "error"  # error, warning, info
    status: str = "active"  # active, disabled
    id: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)
