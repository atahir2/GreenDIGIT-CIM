"""Asset Registry — types (Milestone 6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

ASSET_TYPES = frozenset(
    {
        "site",
        "data_centre",
        "datacenter",  # alias spelling
        "cluster",
        "rack",
        "node",
        "server",
        "cpu",
        "gpu",
        "storage_system",
        "network_device",
        "virtual_machine",
        "vm",  # alias
        "container",
        "service",
        "workflow",
        "workflow_run",
        "dataset",
        "experiment",
    }
)

# parent_type → child_type allowed links (soft guidance)
HIERARCHY_EDGES = {
    ("site", "data_centre"),
    ("site", "datacenter"),
    ("site", "cluster"),
    ("data_centre", "cluster"),
    ("datacenter", "cluster"),
    ("cluster", "rack"),
    ("cluster", "node"),
    ("cluster", "server"),
    ("rack", "node"),
    ("rack", "server"),
    ("node", "server"),
    ("node", "cpu"),
    ("node", "gpu"),
    ("server", "cpu"),
    ("server", "gpu"),
    ("node", "virtual_machine"),
    ("node", "vm"),
    ("server", "virtual_machine"),
    ("server", "vm"),
    ("node", "container"),
    ("server", "container"),
    ("workflow", "workflow_run"),
}


@dataclass
class AssetEntry:
    """Infrastructure or research asset in a hierarchy."""

    name: str
    type: str
    identifier: Optional[str] = None
    parent_id: Optional[int] = None
    location: Optional[str] = None
    provider: Optional[str] = None
    specifications: Dict[str, Any] = field(default_factory=dict)
    lifecycle_stage: Optional[str] = None
    status: str = "approved"
    review_status: str = "approved"
    confidence_score: Optional[float] = None
    version: int = 1
    notes: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssetResolutionResult:
    """Soft outcome of Asset Registry resolution (primary leaf asset)."""

    asset_id: Optional[int] = None
    asset_identifier: Optional[str] = None
    asset_type: Optional[str] = None
    parent_asset_id: Optional[int] = None
    # resolved | candidate_created | missing | ambiguous | unknown | not_requested
    resolution_status: str = "not_requested"
    confidence_score: Optional[float] = None
    message: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    entry: Optional[AssetEntry] = None
    # Optional chain created/resolved during hierarchy enrichment
    hierarchy: list[AssetEntry] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.resolution_status in {"resolved", "candidate_created", "not_requested"}
