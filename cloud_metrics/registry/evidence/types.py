"""Evidence Registry — types (Milestone 9)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvidenceRequirementEntry:
    """Evidence requirement linking metrics to standards/reporting."""

    standard_code: Optional[str] = None
    standard_name: Optional[str] = None
    metric_namespace: Optional[str] = None
    evidence_type: Optional[str] = None  # measurement, calculation, document, audit
    requirement_level: str = "recommended"  # mandatory, recommended, optional
    reporting_period: Optional[str] = None
    aggregation_method: Optional[str] = None
    boundary: Optional[str] = None
    description: Optional[str] = None
    id: Optional[int] = None
    status: str = "approved"
    review_status: str = "approved"
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceLookupResult:
    """Soft evidence enrichment for a metric."""

    metric_namespace: Optional[str] = None
    requirements: List[EvidenceRequirementEntry] = field(default_factory=list)
    mandatory: List[EvidenceRequirementEntry] = field(default_factory=list)
    optional: List[EvidenceRequirementEntry] = field(default_factory=list)
    # not_applicable | declared | incomplete_hint | unknown
    readiness_status: str = "not_applicable"
    message: Optional[str] = None
