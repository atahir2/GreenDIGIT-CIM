"""Evidence Registry package."""

from cloud_metrics.registry.evidence.types import EvidenceRequirementEntry
from cloud_metrics.registry.evidence.service import (
    EvidenceRegistryService,
    get_evidence_registry_service,
)

__all__ = [
    "EvidenceRequirementEntry",
    "EvidenceRegistryService",
    "get_evidence_registry_service",
]
