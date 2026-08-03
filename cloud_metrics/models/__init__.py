# cloud_metrics/models/__init__.py
from .db_models import Base

# core entities (adjust filenames/names to your repo)
from .datacenter import Datacenter
from .metric_definition import MetricDefinition
from .metric_sample import MetricSample
from .upload_log import FileUploadLog           # <-- this is key
from .standard_models import Standard, MetricStandardMap
from .namespace_models import Category, Subcategory
from .unit import QuantityKind, Unit
from .source import Source
from .asset import Asset
from .cim_mapping import CimMapping
from .provenance import ProvenanceRecord
# Milestone 2 additive registry tables (coexist with legacy models above)
from .cim_registry import (  # noqa: F401
    CIM_REGISTRY_MODELS,
    CIM_REGISTRY_TABLES,
    GOVERNANCE_COLUMNS,
    CimAsset,
    CimEvidenceRequirement,
    CimExtensionMetric,
    CimLifecycleStage,
    CimMetricDefinition,
    CimMetricLifecycleLink,
    CimMetricMapping,
    CimProvenanceRecord,
    CimQuantityKind,
    CimSource,
    CimStandard,
    CimStandardTerm,
    CimUnit,
    CimValidationRule,
)

__all__ = [
    "Base",
    "Datacenter",
    "MetricDefinition",
    "MetricSample",
    "FileUploadLog",
    "Standard",
    "MetricStandardMap",
    "Category",
    "Subcategory",
    "QuantityKind",
    "Unit",
    "Source",
    "Asset",
    "CimMapping",
    "ProvenanceRecord",
    "CimQuantityKind",
    "CimUnit",
    "CimSource",
    "CimAsset",
    "CimStandard",
    "CimStandardTerm",
    "CimMetricDefinition",
    "CimMetricMapping",
    "CimLifecycleStage",
    "CimMetricLifecycleLink",
    "CimValidationRule",
    "CimEvidenceRequirement",
    "CimProvenanceRecord",
    "CimExtensionMetric",
    "CIM_REGISTRY_MODELS",
    "CIM_REGISTRY_TABLES",
    "GOVERNANCE_COLUMNS",
]