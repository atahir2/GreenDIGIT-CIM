"""Registry Orchestrator — types (Milestone 7–9)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from cloud_metrics.registry.evidence.types import EvidenceRequirementEntry
from cloud_metrics.registry.lifecycle.types import MetricLifecycleLink
from cloud_metrics.registry.rule.types import ValidationResult
from cloud_metrics.registry.standards.types import StandardMappingEntry


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
    # Optional governance context
    aggregation_period: Optional[str] = None
    boundary: Optional[str] = None
    formula_or_derivation_method: Optional[str] = None
    workflow_id: Optional[str] = None
    run_id: Optional[str] = None


@dataclass
class OrchestratorResult:
    """Normalized CIM mapping result produced by the registry orchestrator."""

    raw_metric_name: str
    cim_namespace: Optional[str] = None
    metric_definition_id: Optional[int] = None
    mapping_status: str = "unresolved"
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
    resolved: bool = False
    resolution_path: str = "unresolved"
    legacy_unified_key: Optional[str] = None
    storage_unified_key: Optional[str] = None
    relation_type: Optional[str] = None
    message: Optional[str] = None
    # Milestone 8 — lifecycle
    lifecycle_stages: List[str] = field(default_factory=list)
    lifecycle_usage_purposes: List[str] = field(default_factory=list)
    lifecycle_importance: List[str] = field(default_factory=list)
    lifecycle_review_status: List[str] = field(default_factory=list)
    lifecycle_links: List[MetricLifecycleLink] = field(default_factory=list)
    # Milestone 8 — standards
    standards_mappings: List[StandardMappingEntry] = field(default_factory=list)
    standards_relation_types: List[str] = field(default_factory=list)
    standards_confidence_scores: List[Optional[float]] = field(default_factory=list)
    standards_review_status: List[str] = field(default_factory=list)
    standards_notes: List[Optional[str]] = field(default_factory=list)
    no_direct_standard_match: bool = False
    # Milestone 9 — governance
    validation_results: List[ValidationResult] = field(default_factory=list)
    rule_results: List[ValidationResult] = field(default_factory=list)
    evidence_requirements: List[EvidenceRequirementEntry] = field(default_factory=list)
    evidence_readiness_status: Optional[str] = None
    provenance_record_id: Optional[int] = None
    provenance_log_reference: Optional[str] = None
    extension_candidate_id: Optional[int] = None
    governance_warnings: List[str] = field(default_factory=list)
    governance_errors: List[str] = field(default_factory=list)
    review_required: bool = False

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
            "lifecycle_stages": list(self.lifecycle_stages),
            "lifecycle_usage_purposes": list(self.lifecycle_usage_purposes),
            "lifecycle_importance": list(self.lifecycle_importance),
            "lifecycle_review_status": list(self.lifecycle_review_status),
            "standards_relation_types": list(self.standards_relation_types),
            "standards_confidence_scores": list(self.standards_confidence_scores),
            "standards_review_status": list(self.standards_review_status),
            "standards_notes": list(self.standards_notes),
            "standards_mappings": [
                {
                    "standard_code": m.standard_code,
                    "standard_name": m.standard_name,
                    "relation_type": m.relation_type,
                    "confidence_score": m.confidence_score,
                    "review_status": m.review_status,
                    "notes": m.notes,
                    "standard_term": m.standard_term,
                }
                for m in self.standards_mappings
            ],
            "no_direct_standard_match": self.no_direct_standard_match,
            "validation_results": [
                {
                    "rule_name": v.rule_name,
                    "passed": v.passed,
                    "severity": v.severity,
                    "message": v.message,
                }
                for v in self.validation_results
            ],
            "evidence_requirements": [
                {
                    "standard_code": e.standard_code,
                    "evidence_type": e.evidence_type,
                    "requirement_level": e.requirement_level,
                    "description": e.description,
                }
                for e in self.evidence_requirements
            ],
            "evidence_readiness_status": self.evidence_readiness_status,
            "provenance_record_id": self.provenance_record_id,
            "provenance_log_reference": self.provenance_log_reference,
            "extension_candidate_id": self.extension_candidate_id,
            "governance_warnings": list(self.governance_warnings),
            "governance_errors": list(self.governance_errors),
            "review_required": self.review_required,
        }
