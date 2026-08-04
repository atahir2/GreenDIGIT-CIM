"""Registry Orchestrator — types (Milestone 7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class RawMetricContext:
    """Normalized raw metric context passed into the registry orchestrator."""

    raw_metric_name: str
    value: Optional[float] = None
    unit: Optional[str] = None
    timestamp: Optional[datetime] = None
    source: Optional[str] = None
    source_type: Optional[str] = None
    source_metadata: Optional[Dict[str, Any]] = None
    asset_labels: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, Any]] = None
    labels: Optional[Dict[str, Any]] = None
    original_raw_metadata: Optional[Dict[str, Any]] = None


@dataclass
class OrchestratorResult:
    """Normalized CIM mapping result produced by the registry orchestrator."""

    raw_metric_name: str
    cim_namespace: Optional[str] = None
    metric_definition_id: Optional[int] = None
    mapping_status: str = "unresolved"  # approved | candidate | unresolved | ...
    mapping_confidence: Optional[float] = None
    unit_validation_status: Optional[str] = None
    observed_unit: Optional[str] = None
    canonical_unit: Optional[str] = None
    expected_quantity_kind: Optional[str] = None
    source_resolution_status: Optional[str] = None
    source_id: Optional[int] = None
    asset_resolution_status: Optional[str] = None
    asset_id: Optional[int] = None
    candidate_flags: Dict[str, bool] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    fallback_used: bool = False
    original_raw_metadata: Dict[str, Any] = field(default_factory=dict)
    # Adapter / tracing helpers (not part of the public contract, but useful)
    resolved: bool = False
    resolution_path: str = "unresolved"  # registry | legacy_fallback | unresolved
    legacy_unified_key: Optional[str] = None
    storage_unified_key: Optional[str] = None
    relation_type: Optional[str] = None
    message: Optional[str] = None

    def to_metadata(self) -> Dict[str, Any]:
        """Compact dict suitable for ``extra_meta`` / sample tags."""
        return {
            "raw_metric_name": self.raw_metric_name,
            "cim_namespace": self.cim_namespace,
            "metric_definition_id": self.metric_definition_id,
            "mapping_status": self.mapping_status,
            "mapping_confidence": self.mapping_confidence,
            "unit_validation_status": self.unit_validation_status,
            "observed_unit": self.observed_unit,
            "canonical_unit": self.canonical_unit,
            "expected_quantity_kind": self.expected_quantity_kind,
            "source_resolution_status": self.source_resolution_status,
            "source_id": self.source_id,
            "asset_resolution_status": self.asset_resolution_status,
            "asset_id": self.asset_id,
            "candidate_flags": dict(self.candidate_flags),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "fallback_used": self.fallback_used,
            "resolved": self.resolved,
            "resolution_path": self.resolution_path,
            "legacy_unified_key": self.legacy_unified_key,
            "storage_unified_key": self.storage_unified_key,
            "relation_type": self.relation_type,
            "message": self.message,
        }
