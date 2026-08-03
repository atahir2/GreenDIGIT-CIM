"""Standards Registry — base types (Milestone 1 skeleton)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


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
