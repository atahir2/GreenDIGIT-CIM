"""Mapping Registry — lookup types (Milestone 4–6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from cloud_metrics.registry.asset.types import AssetResolutionResult
from cloud_metrics.registry.source.types import SourceResolutionResult
from cloud_metrics.registry.unit.types import UnitValidationResult


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
    # Align with CimGovernanceMixin: draft|candidate|approved|rejected|deprecated|active
    status: str = "candidate"
    review_status: str = "pending"
    version: int = 1
    origin: str = "manual"  # manual, auto-learned, seeded, imported, migrated, legacy_fallback
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    legacy_unified_key: Optional[str] = None
    # Milestone 5 — optional expectations from linked metric definition
    expected_quantity_kind: Optional[str] = None
    canonical_unit: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MappingLookupResult:
    """Result of registry-first mapping resolution with optional fallback."""

    raw_key: str
    resolved: bool
    resolution_path: str  # registry | legacy_fallback | unresolved
    cim_namespace: Optional[str] = None
    legacy_unified_key: Optional[str] = None
    mapping: Optional[MappingEntry] = None
    status: str = "unresolved"  # approved | candidate | unresolved
    message: Optional[str] = None
    candidate_created: bool = False
    # Milestone 5 — soft unit validation metadata (never blocks resolution)
    unit_validation: Optional[UnitValidationResult] = None
    expected_quantity_kind: Optional[str] = None
    canonical_unit: Optional[str] = None
    # Milestone 6 — soft source / asset resolution (never blocks resolution)
    source_resolution: Optional[SourceResolutionResult] = None
    asset_resolution: Optional[AssetResolutionResult] = None
