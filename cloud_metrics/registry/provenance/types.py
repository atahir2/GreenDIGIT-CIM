"""Provenance Registry — base types (Milestone 1 skeleton)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class ProvenanceEntry:
    """Audit / lineage record for a pipeline activity."""

    entity_type: str
    activity: str
    agent: str
    entity_id: Optional[int] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    method: Optional[str] = None
    confidence: Optional[float] = None
    prov_uri: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    extra: Dict[str, Any] = field(default_factory=dict)
