"""Asset Registry — base types (Milestone 1 skeleton)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class AssetEntry:
    """Infrastructure or research asset in a hierarchy."""

    name: str
    type: str  # datacenter, cluster, rack, node, server, cpu, gpu, ...
    parent_id: Optional[int] = None
    location: Optional[str] = None
    provider: Optional[str] = None
    specifications: Dict[str, Any] = field(default_factory=dict)
    lifecycle_stage: Optional[str] = None
    status: str = "active"
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    extra: Dict[str, Any] = field(default_factory=dict)
