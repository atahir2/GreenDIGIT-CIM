"""Extension Registry — types (Milestone 9)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class ExtensionEntry:
    """Custom / extension metric proposal outside covered standards."""

    metric_namespace: Optional[str] = None
    metric_id: Optional[int] = None
    raw_metric_name: Optional[str] = None
    proposed_standard: Optional[str] = None
    justification: Optional[str] = None
    suggested_domain: Optional[str] = None
    suggested_category: Optional[str] = None
    suggested_quantity_kind: Optional[str] = None
    suggested_unit: Optional[str] = None
    suggested_definition: Optional[str] = None
    source_context: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    # proposed | candidate | accepted | rejected | merged | submitted_to_standard
    status: str = "candidate"
    review_status: str = "under_review"  # candidate | pending | under_review | approved | rejected
    proposed_by: Optional[str] = None
    proposed_at: Optional[datetime] = None
    id: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_approved(self) -> bool:
        return (self.status or "").lower() in {"accepted", "approved", "adopted"} and (
            self.review_status or ""
        ).lower() == "approved"
