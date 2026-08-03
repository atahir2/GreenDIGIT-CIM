"""Evidence Registry — base types (Milestone 1 skeleton)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class EvidenceRequirementEntry:
    """Evidence requirement linking metrics to standards/reporting."""

    standard_code: Optional[str] = None
    metric_namespace: Optional[str] = None
    evidence_type: Optional[str] = None  # measurement, calculation, document, audit
    requirement_level: str = "recommended"  # mandatory, recommended, optional
    reporting_period: Optional[str] = None
    aggregation_method: Optional[str] = None
    boundary: Optional[str] = None
    description: Optional[str] = None
    id: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)
