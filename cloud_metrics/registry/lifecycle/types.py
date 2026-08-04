"""Lifecycle Registry — types (Milestone 8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Seed ``relevance`` → public importance vocabulary
RELEVANCE_TO_IMPORTANCE = {
    "primary": "required",
    "required": "required",
    "secondary": "recommended",
    "recommended": "recommended",
    "conditional": "conditional",
}

# Stage key → usage purpose (how the metric is used in that RILM stage)
STAGE_USAGE_PURPOSE = {
    "planning": "planning_assessment",
    "design": "design_assessment",
    "procurement": "procurement_assessment",
    "deployment": "deployment_verification",
    "operation": "operational_monitoring",
    "optimisation": "efficiency_optimisation",
    "reproducibility": "experiment_reproducibility",
    "reporting": "kpi_reporting",
    "continuous_improvement": "continuous_improvement",
    "decommissioning": "decommissioning_assessment",
}


@dataclass
class LifecycleStageEntry:
    """Research Infrastructure lifecycle stage."""

    stage: str  # stage_key
    label: Optional[str] = None
    description: Optional[str] = None
    sequence: Optional[int] = None
    applicable_metrics: List[str] = field(default_factory=list)
    applicable_assets: List[int] = field(default_factory=list)
    id: Optional[int] = None
    status: str = "approved"
    review_status: str = "approved"
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricLifecycleLink:
    """A metric ↔ lifecycle stage association."""

    stage_key: str
    stage_label: Optional[str] = None
    usage_purpose: Optional[str] = None
    importance: str = "recommended"  # required | recommended | conditional
    relevance: str = "secondary"  # raw DB relevance
    review_status: str = "approved"
    status: str = "approved"
    notes: Optional[str] = None
    lifecycle_stage_id: Optional[int] = None
    metric_id: Optional[int] = None
    metric_namespace: Optional[str] = None


@dataclass
class LifecycleLookupResult:
    """Soft lifecycle enrichment for a CIM metric."""

    metric_namespace: Optional[str] = None
    links: List[MetricLifecycleLink] = field(default_factory=list)
    stages: List[str] = field(default_factory=list)
    usage_purposes: List[str] = field(default_factory=list)
    importance: List[str] = field(default_factory=list)
    review_statuses: List[str] = field(default_factory=list)
    message: Optional[str] = None
