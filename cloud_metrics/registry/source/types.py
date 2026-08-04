"""Source Registry — types (Milestone 6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

# Controlled vocabulary (also accept legacy aliases like prometheus → monitoring_system)
SOURCE_TYPES = frozenset(
    {
        "file",
        "api",
        "monitoring_system",
        "workflow_engine",
        "manual_input",
        "database",
        "cloud_api",
        # legacy / catalogue aliases kept for compatibility
        "prometheus",
        "opentelemetry",
        "scaphandre",
        "manual",
    }
)


@dataclass
class SourceEntry:
    """Telemetry / metric source system definition."""

    name: str
    type: str  # see SOURCE_TYPES
    protocol: Optional[str] = None
    format: Optional[str] = None
    schema_version: Optional[str] = None
    capabilities: Dict[str, Any] = field(default_factory=dict)
    auth_method: str = "none"
    status: str = "approved"
    review_status: str = "approved"
    confidence_score: Optional[float] = None
    version: int = 1
    notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)  # maps to metadata_info
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceResolutionResult:
    """Soft outcome of Source Registry resolution."""

    source_id: Optional[int] = None
    source_name: Optional[str] = None
    source_type: Optional[str] = None
    # resolved | candidate_created | missing | ambiguous | unknown | not_requested
    resolution_status: str = "not_requested"
    confidence_score: Optional[float] = None
    message: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    entry: Optional[SourceEntry] = None

    @property
    def ok(self) -> bool:
        return self.resolution_status in {"resolved", "candidate_created", "not_requested"}
