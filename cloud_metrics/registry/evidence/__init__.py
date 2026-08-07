"""Evidence Registry package (Milestone 9)."""

from cloud_metrics.registry.evidence.types import (
    EvidenceLookupResult,
    EvidenceRequirementEntry,
)
from cloud_metrics.registry.evidence.service import (
    EvidenceRegistryService,
    get_evidence_registry_service,
)

__all__ = [
    "EvidenceRequirementEntry",
    "EvidenceLookupResult",
    "EvidenceRegistryService",
    "get_evidence_registry_service",
]
