"""Registry package for the modular, registry-driven CIM.

Milestone 1 adds a skeleton under ``cloud_metrics.registry.<name>`` for each
of the 11 target registries (types + placeholder services).

Legacy helpers remain available and unchanged:
- ``cloud_metrics.registry.namespace_registry``
- ``cloud_metrics.registry.mapping_registry``
"""

from cloud_metrics.registry.base import RegistryName, RegistryMeta, SKELETON_ONLY

from cloud_metrics.registry.metric import (
    MetricEntry,
    MetricRegistryService,
    get_metric_registry_service,
)
from cloud_metrics.registry.unit import (
    QuantityKindEntry,
    UnitEntry,
    UnitRegistryService,
    UnitValidationResult,
    get_unit_registry_service,
)
from cloud_metrics.registry.source import (
    SourceEntry,
    SourceRegistryService,
    SourceResolutionResult,
    get_source_registry_service,
)
from cloud_metrics.registry.asset import (
    AssetEntry,
    AssetRegistryService,
    AssetResolutionResult,
    get_asset_registry_service,
)
from cloud_metrics.registry.standards import (
    StandardEntry,
    StandardsRegistryService,
    get_standards_registry_service,
)
from cloud_metrics.registry.mapping import (
    MappingEntry,
    MappingLookupResult,
    MappingRegistryService,
    get_mapping_registry_service,
    resolve_raw_metric,
)
from cloud_metrics.registry.lifecycle import (
    LifecycleStageEntry,
    LifecycleRegistryService,
    get_lifecycle_registry_service,
)
from cloud_metrics.registry.rule import (
    RuleEntry,
    RuleRegistryService,
    get_rule_registry_service,
)
from cloud_metrics.registry.evidence import (
    EvidenceRequirementEntry,
    EvidenceRegistryService,
    get_evidence_registry_service,
)
from cloud_metrics.registry.provenance import (
    ProvenanceEntry,
    ProvenanceRegistryService,
    get_provenance_registry_service,
)
from cloud_metrics.registry.extension import (
    ExtensionEntry,
    ExtensionRegistryService,
    get_extension_registry_service,
)
from cloud_metrics.registry.orchestrator import (
    CimRegistryOrchestrator,
    OrchestratorResult,
    RawMetricContext,
    RegistryOrchestrator,
    RegistryOrchestratorService,
    get_registry_orchestrator,
)

# All 11 registry names for discovery / smoke tests.
REGISTRY_MODULES = (
    RegistryName.METRIC,
    RegistryName.UNIT,
    RegistryName.SOURCE,
    RegistryName.ASSET,
    RegistryName.STANDARDS,
    RegistryName.MAPPING,
    RegistryName.LIFECYCLE,
    RegistryName.RULE,
    RegistryName.EVIDENCE,
    RegistryName.PROVENANCE,
    RegistryName.EXTENSION,
)

SERVICE_FACTORIES = {
    RegistryName.METRIC: get_metric_registry_service,
    RegistryName.UNIT: get_unit_registry_service,
    RegistryName.SOURCE: get_source_registry_service,
    RegistryName.ASSET: get_asset_registry_service,
    RegistryName.STANDARDS: get_standards_registry_service,
    RegistryName.MAPPING: get_mapping_registry_service,
    RegistryName.LIFECYCLE: get_lifecycle_registry_service,
    RegistryName.RULE: get_rule_registry_service,
    RegistryName.EVIDENCE: get_evidence_registry_service,
    RegistryName.PROVENANCE: get_provenance_registry_service,
    RegistryName.EXTENSION: get_extension_registry_service,
}


def get_all_registry_services():
    """Instantiate all placeholder registry services (Milestone 1)."""
    return {name: factory() for name, factory in SERVICE_FACTORIES.items()}


__all__ = [
    "RegistryName",
    "RegistryMeta",
    "SKELETON_ONLY",
    "REGISTRY_MODULES",
    "SERVICE_FACTORIES",
    "get_all_registry_services",
    "MetricEntry",
    "MetricRegistryService",
    "get_metric_registry_service",
    "QuantityKindEntry",
    "UnitEntry",
    "UnitValidationResult",
    "UnitRegistryService",
    "get_unit_registry_service",
    "SourceEntry",
    "SourceResolutionResult",
    "SourceRegistryService",
    "get_source_registry_service",
    "AssetEntry",
    "AssetResolutionResult",
    "AssetRegistryService",
    "get_asset_registry_service",
    "StandardEntry",
    "StandardsRegistryService",
    "get_standards_registry_service",
    "MappingEntry",
    "MappingLookupResult",
    "MappingRegistryService",
    "get_mapping_registry_service",
    "resolve_raw_metric",
    "LifecycleStageEntry",
    "LifecycleRegistryService",
    "get_lifecycle_registry_service",
    "RuleEntry",
    "RuleRegistryService",
    "get_rule_registry_service",
    "EvidenceRequirementEntry",
    "EvidenceRegistryService",
    "get_evidence_registry_service",
    "ProvenanceEntry",
    "ProvenanceRegistryService",
    "get_provenance_registry_service",
    "ExtensionEntry",
    "ExtensionRegistryService",
    "get_extension_registry_service",
    "RawMetricContext",
    "OrchestratorResult",
    "RegistryOrchestratorService",
    "RegistryOrchestrator",
    "CimRegistryOrchestrator",
    "get_registry_orchestrator",
]
