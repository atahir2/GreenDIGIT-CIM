"""Evidence Registry service placeholder (Milestone 1).

Delegates to the modular skeleton under ``cloud_metrics.registry.evidence``.
No evidence/reporting behaviour is enforced yet.
"""

from __future__ import annotations

from typing import List, Optional

from cloud_metrics.registry.evidence import (
    EvidenceRequirementEntry,
    EvidenceRegistryService,
    get_evidence_registry_service,
)

__all__ = [
    "EvidenceRequirementEntry",
    "EvidenceRegistryService",
    "get_evidence_registry_service",
    "list_evidence_requirements",
    "get_evidence_requirement",
]


def list_evidence_requirements() -> List[EvidenceRequirementEntry]:
    return get_evidence_registry_service().list_entries()


def get_evidence_requirement(requirement_id: int) -> Optional[EvidenceRequirementEntry]:
    return get_evidence_registry_service().get_by_id(requirement_id)
