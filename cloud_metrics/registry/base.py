"""Shared base types for the registry-driven CIM skeleton.

Milestone 1 introduces conceptual interfaces only. These dataclasses are not
SQLAlchemy models and do not alter the database schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Protocol, runtime_checkable


class RegistryName(str, Enum):
    """Canonical names for the 11 target registries."""

    METRIC = "metric"
    UNIT = "unit"
    SOURCE = "source"
    ASSET = "asset"
    STANDARDS = "standards"
    MAPPING = "mapping"
    LIFECYCLE = "lifecycle"
    RULE = "rule"
    EVIDENCE = "evidence"
    PROVENANCE = "provenance"
    EXTENSION = "extension"


@runtime_checkable
class RegistryService(Protocol):
    """Minimal protocol shared by placeholder registry services."""

    registry_name: RegistryName

    def list_entries(self) -> list[Any]:
        """Return known entries (empty in Milestone 1 placeholders)."""
        ...


@dataclass
class RegistryMeta:
    """Common metadata carried by registry entry types."""

    id: Optional[int] = None
    status: Optional[str] = None
    version: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    extra: Dict[str, Any] = field(default_factory=dict)


# Marker used by placeholder services to signal they are not wired yet.
SKELETON_ONLY = True
