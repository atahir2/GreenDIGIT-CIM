"""Extension Registry — base types (Milestone 1 skeleton)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class ExtensionEntry:
    """Custom / extension metric proposal outside covered standards."""

    metric_namespace: Optional[str] = None
    metric_id: Optional[int] = None
    proposed_standard: Optional[str] = None
    justification: Optional[str] = None
    # proposed, accepted, submitted_to_standard, adopted
    status: str = "proposed"
    proposed_by: Optional[str] = None
    proposed_at: Optional[datetime] = None
    id: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)
