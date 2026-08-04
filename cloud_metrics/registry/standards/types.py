"""Standards Registry — types (Milestone 8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Controlled relation vocabulary (also in seed RELATION_TYPES)
RELATION_TYPES = (
    "exactMatch",
    "closeMatch",
    "broadMatch",
    "narrowMatch",
    "inputToKPI",
    "derivedFrom",
    "contextualMatch",
    "extensionMetric",
    "noMatch",
    "underReview",
)

# Relations that assert strong identity — only when explicitly seeded
STRONG_IDENTITY_RELATIONS = frozenset({"exactMatch"})


@dataclass
class StandardEntry:
    """External standard / vocabulary catalog entry."""

    code: str
    name: str
    url: Optional[str] = None
    description: Optional[str] = None
    vocabulary_type: Optional[str] = None  # standard, ontology, vocabulary, convention
    namespace_prefix: Optional[str] = None
    namespace_uri: Optional[str] = None
    version: Optional[str] = None
    domain: Optional[str] = None
    status: str = "active"
    id: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StandardMappingEntry:
    """A CIM metric ↔ standard (term) mapping."""

    standard_code: str
    standard_name: str
    relation_type: str
    confidence_score: Optional[float] = None
    review_status: str = "approved"
    status: str = "approved"
    notes: Optional[str] = None
    standard_term: Optional[str] = None
    standard_term_code: Optional[str] = None
    metric_namespace: Optional[str] = None
    mapping_id: Optional[int] = None
    standard_id: Optional[int] = None


@dataclass
class StandardsLookupResult:
    """Soft standards enrichment for a CIM metric."""

    metric_namespace: Optional[str] = None
    mappings: List[StandardMappingEntry] = field(default_factory=list)
    relation_types: List[str] = field(default_factory=list)
    confidence_scores: List[Optional[float]] = field(default_factory=list)
    review_statuses: List[str] = field(default_factory=list)
    notes: List[Optional[str]] = field(default_factory=list)
    no_direct_standard_match: bool = False
    message: Optional[str] = None
