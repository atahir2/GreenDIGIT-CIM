"""Lifecycle Registry — base types (Milestone 1 skeleton)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LifecycleStageEntry:
    """Research Infrastructure lifecycle stage."""

    stage: str  # planning, design, procurement, deployment, operation, ...
    label: Optional[str] = None
    description: Optional[str] = None
    sequence: Optional[int] = None
    applicable_metrics: List[str] = field(default_factory=list)
    applicable_assets: List[int] = field(default_factory=list)
    id: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)
