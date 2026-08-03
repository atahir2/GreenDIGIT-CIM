"""Mapping Registry — base types (Milestone 1 skeleton)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class MappingEntry:
    """Raw source key → CIM metric (and optional standard) mapping."""

    source_key: str
    cim_namespace: Optional[str] = None
    source_id: Optional[int] = None
    cim_metric_id: Optional[int] = None
    standard_id: Optional[int] = None
    # exactMatch, closeMatch, broadMatch, narrowMatch, inputToKPI,
    # derivedFrom, contextualMatch, extensionMetric, noMatch, underReview
    relation_type: str = "underReview"
    confidence: float = 1.0
    rationale: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    status: str = "proposed"  # proposed, approved, rejected, deprecated
    version: int = 1
    origin: str = "manual"  # manual, auto-learned, seeded, imported
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    extra: Dict[str, Any] = field(default_factory=dict)
