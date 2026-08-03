# Registry Module Structure

> **Milestone 1 skeleton** · Updated 2026-08-03

This document describes the modular registry package layout introduced for the registry-driven CIM. It is a **framework skeleton**, not a GreenDIGIT-hardcoded schema and not a profile-based design.

---

## 1. Package Layout

```
cloud_metrics/registry/
├── __init__.py                 # Aggregated exports + get_all_registry_services()
├── base.py                     # RegistryName, RegistryMeta, RegistryService, SKELETON_ONLY
├── metric/                     # 1. Metric Registry
│   ├── __init__.py
│   ├── types.py                # MetricEntry
│   └── service.py              # MetricRegistryService (placeholder)
├── unit/                       # 2. Unit Registry
│   ├── __init__.py
│   ├── types.py                # QuantityKindEntry, UnitEntry
│   └── service.py
├── source/                     # 3. Source Registry
├── asset/                      # 4. Asset Registry
├── standards/                  # 5. Standards Registry
├── mapping/                    # 6. Mapping Registry (modular skeleton)
├── lifecycle/                  # 7. Lifecycle Registry
├── rule/                       # 8. Rule Registry
├── evidence/                   # 9. Evidence Registry
├── provenance/                 # 10. Provenance Registry
├── extension/                  # 11. Extension Registry
├── namespace_registry.py        # LEGACY — unchanged
└── mapping_registry.py         # LEGACY — unchanged
```

Each of the 11 registry packages follows the same pattern:

| File | Purpose |
|------|---------|
| `types.py` | Dataclass interfaces describing registry entries |
| `service.py` | Placeholder service (`skeleton_only=True`, empty `list_entries()`) |
| `__init__.py` | Stable public exports |

---

## 2. Service Facades (`cloud_metrics/services/`)

Project convention places callable service modules under `services/`. Milestone 1 added facades for registries that did not already have one:

| Module | Registry |
|--------|----------|
| `metric_registry_service.py` | Metric |
| `source_registry_service.py` | Source |
| `asset_registry_service.py` | Asset |
| `lifecycle_registry_service.py` | Lifecycle |
| `evidence_registry_service.py` | Evidence |
| `extension_registry_service.py` | Extension |

**Pre-existing (Antigravity) — not modified by Milestone 1:**

| Module | Registry |
|--------|----------|
| `unit_registry_service.py` | Unit |
| `mapping_registry_service.py` | Mapping |
| `rule_registry_service.py` | Rule |
| `provenance_registry_service.py` | Provenance |
| `standards_registry.py` | Standards |

---

## 3. Discovery Helpers

```python
from cloud_metrics.registry import (
    REGISTRY_MODULES,          # tuple of all 11 RegistryName values
    get_all_registry_services, # dict[RegistryName, placeholder service]
    RegistryName,
)
```

---

## 4. Relationship to ORM Models

| Registry | Skeleton types | Existing SQLAlchemy model (if any) |
|----------|----------------|-------------------------------------|
| Metric | `MetricEntry` | `MetricDefinition` |
| Unit | `UnitEntry`, `QuantityKindEntry` | `Unit`, `QuantityKind` |
| Source | `SourceEntry` | `Source` |
| Asset | `AssetEntry` | `Asset` |
| Standards | `StandardEntry` | `Standard` |
| Mapping | `MappingEntry` | `CimMapping` |
| Lifecycle | `LifecycleStageEntry` | *(none yet)* |
| Rule | `RuleEntry` | *(none yet — logic in service)* |
| Evidence | `EvidenceRequirementEntry` | *(none yet)* |
| Provenance | `ProvenanceEntry` | `ProvenanceRecord` |
| Extension | `ExtensionEntry` | *(none yet)* |

Milestone 1 **does not** add or alter database tables. Type ↔ ORM alignment is deferred.

---

## 5. Design Notes

1. Skeleton services return empty collections / pass-through entries so they are safe to import without side effects.
2. Legacy `namespace_registry` / `mapping_registry` modules remain the current helpers used by existing flows.
3. Ingestion must not import skeleton services until a later milestone explicitly wires them.
4. See `docs/development/MILESTONE_1_REGISTRY_SKELETON.md` for milestone scope and verification.
