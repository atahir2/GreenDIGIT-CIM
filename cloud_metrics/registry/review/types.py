"""Admin / candidate review types (Milestone 12)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ReviewEntityType(str, Enum):
    MAPPING = "mapping"
    EXTENSION = "extension"
    METRIC = "metric"
    SOURCE = "source"
    ASSET = "asset"
    UNIT = "unit"
    STANDARDS_MAPPING = "standards_mapping"
    LIFECYCLE_LINK = "lifecycle_link"


class ReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"
    MERGE = "merge"
    DEPRECATE = "deprecate"
    PROMOTE_TO_SEED = "promote_to_seed"
    REQUEST_CHANGES = "request_changes"
    MARK_UNDER_REVIEW = "mark_under_review"
    REOPEN = "reopen"


# Statuses considered "in the review queue"
QUEUE_STATUSES = frozenset(
    {
        "candidate",
        "pending",
        "under_review",
        "draft",
        "accepted",  # extension intermediate
        "proposed",
    }
)

APPROVED_STATUSES = frozenset({"approved", "active"})
TERMINAL_NEGATIVE = frozenset({"rejected", "deprecated", "retired", "merged"})


@dataclass
class ReviewableEntry:
    """Normalized view of an entity awaiting or under review."""

    entity_type: ReviewEntityType
    entity_id: int
    status: str
    review_status: str
    label: Optional[str] = None
    namespace_or_key: Optional[str] = None
    origin: Optional[str] = None
    relation_type: Optional[str] = None
    justification: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None
    confidence_score: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "status": self.status,
            "review_status": self.review_status,
            "label": self.label,
            "namespace_or_key": self.namespace_or_key,
            "origin": self.origin,
            "relation_type": self.relation_type,
            "justification": self.justification,
            "notes": self.notes,
            "created_by": self.created_by,
            "confidence_score": self.confidence_score,
            "details": dict(self.details),
        }


@dataclass
class ReviewDecision:
    """Result of a review action."""

    ok: bool
    action: ReviewAction
    entity_type: ReviewEntityType
    entity_id: int
    previous_status: Optional[str] = None
    previous_review_status: Optional[str] = None
    new_status: Optional[str] = None
    new_review_status: Optional[str] = None
    reviewer: Optional[str] = None
    notes: Optional[str] = None
    message: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    provenance_record_id: Optional[int] = None
    entry: Optional[ReviewableEntry] = None
    seed_proposal_path: Optional[str] = None
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "action": self.action.value,
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "previous_status": self.previous_status,
            "previous_review_status": self.previous_review_status,
            "new_status": self.new_status,
            "new_review_status": self.new_review_status,
            "reviewer": self.reviewer,
            "notes": self.notes,
            "message": self.message,
            "errors": list(self.errors),
            "provenance_record_id": self.provenance_record_id,
            "seed_proposal_path": self.seed_proposal_path,
            "entry": self.entry.to_dict() if self.entry else None,
            "extras": dict(self.extras),
        }


class ReviewError(Exception):
    """Raised for unsafe or invalid review transitions (also returned in decisions)."""

    def __init__(self, message: str, *, errors: Optional[List[str]] = None) -> None:
        super().__init__(message)
        self.errors = errors or [message]


@dataclass
class SeedPromotionItem:
    """One approved mapping/metric proposed for seed export (not auto-applied)."""

    kind: str  # mapping | metric | extension
    source_key: Optional[str] = None
    cim_namespace: Optional[str] = None
    relation_type: Optional[str] = None
    origin: Optional[str] = None
    entity_id: Optional[int] = None
    notes: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
