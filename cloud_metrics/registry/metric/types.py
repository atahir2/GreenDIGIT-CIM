"""Metric Registry — base types (Milestone 1 skeleton)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class MetricEntry:
    """Canonical CIM metric definition (conceptual; not a DB model)."""

    namespace: str
    label: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None  # energy, performance, network, storage, environment
    category: Optional[str] = None
    subcategory: Optional[str] = None
    quantity_kind: Optional[str] = None
    canonical_unit: Optional[str] = None
    metric_type: Optional[str] = None  # observed, calculated, derived, aggregated, reported
    status: str = "draft"  # draft, active, deprecated, retired
    tags: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    version: int = 1
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    extra: Dict[str, Any] = field(default_factory=dict)
