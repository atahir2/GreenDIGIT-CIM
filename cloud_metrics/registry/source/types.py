"""Source Registry — base types (Milestone 1 skeleton)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class SourceEntry:
    """Telemetry / metric source system definition."""

    name: str
    type: str  # file, api, prometheus, opentelemetry, scaphandre, manual
    protocol: Optional[str] = None
    format: Optional[str] = None
    schema_version: Optional[str] = None
    capabilities: Dict[str, Any] = field(default_factory=dict)
    auth_method: str = "none"
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    extra: Dict[str, Any] = field(default_factory=dict)
