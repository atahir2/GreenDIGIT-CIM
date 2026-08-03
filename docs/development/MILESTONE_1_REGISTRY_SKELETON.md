# Milestone 1 — Registry Skeleton

> **Status**: Completed (pending review)  
> **Date**: 2026-08-03  
> **Scope**: Introduce modular registry package structure and base types without changing runtime behaviour

---

## 1. Objective

Introduce the basic registry module structure for the registry-driven CIM **without** changing existing runtime behaviour (ingestion, namespace generation, mapping, or database schema).

---

## 2. Context from Prior Audit

Antigravity previously audited the codebase and produced documentation under `docs/current/`, `docs/target/`, and `docs/development/`. Some advanced registry work (SQLAlchemy models, selected services, API routes, and ingestion hooks) already exists from that effort.

Milestone 1 **does not undo** that work. It adds a formal, modular skeleton under `cloud_metrics/registry/<name>/` so all 11 target registries have a consistent package layout, base types, and placeholder services.

---

## 3. What Was Delivered

### 3.1 Registry packages (11)

Each package under `cloud_metrics/registry/` contains:

| File | Role |
|------|------|
| `types.py` | Dataclass base types (conceptual; **not** SQLAlchemy models) |
| `service.py` | Placeholder service class (`skeleton_only=True`) |
| `__init__.py` | Public exports |

Packages: `metric`, `unit`, `source`, `asset`, `standards`, `mapping`, `lifecycle`, `rule`, `evidence`, `provenance`, `extension`.

Shared: `cloud_metrics/registry/base.py` (`RegistryName`, `RegistryMeta`, `RegistryService` protocol, `SKELETON_ONLY`).

### 3.2 Placeholder service facades

New thin modules under `cloud_metrics/services/` for registries that lacked a service facade:

- `metric_registry_service.py`
- `source_registry_service.py`
- `asset_registry_service.py`
- `lifecycle_registry_service.py`
- `evidence_registry_service.py`
- `extension_registry_service.py`

Existing Antigravity services (`unit_registry_service`, `mapping_registry_service`, `rule_registry_service`, `provenance_registry_service`, `standards_registry`) were **left untouched**.

### 3.3 Tests

- `tests/test_registry_skeleton.py` — import smoke tests, factory construction, empty `list_entries()`, legacy helper importability.

### 3.4 Documentation

- This file
- `docs/target/REGISTRY_MODULE_STRUCTURE.md`

---

## 4. Explicitly Untouched (Milestone 1 Constraints)

| Area | Status |
|------|--------|
| Ingestion / parsing (`automated_mapper`, `unified_ingestion`, parsers) | Untouched by this milestone |
| Namespace generation | Untouched |
| Legacy mapping logic / JSON maps | Untouched |
| Database schema / Alembic migrations | Untouched |
| Mapping migration / seed scripts | Untouched |
| Removal of old files / old CIM logic | Not performed |
| Wiring skeleton services into ingestion | Not performed |
| Lifecycle / evidence / provenance *behaviour* beyond existing Antigravity code | Not introduced by this skeleton |

---

## 5. Assumptions

1. **Dataclass types vs ORM models**: Milestone 1 base types are dataclasses describing the target conceptual schema. Existing SQLAlchemy models (where present) remain the persistence layer; aligning/wrapping them is a later milestone.
2. **Dual service surfaces**: Placeholder classes live under `registry/<name>/service.py`; thin facades under `services/` match project convention. Pre-existing Antigravity services remain the runtime path for unit/mapping/rule/provenance.
3. **Legacy registry helpers**: `namespace_registry.py` and `mapping_registry.py` stay in place and continue to work.
4. **No API changes in Milestone 1**: Existing `registry_api.py` was not modified.

---

## 6. Verification

```bash
pytest tests/test_registry_skeleton.py -q
pytest tests/ -q
```

---

## 7. Recommended Next Milestone

**Milestone 2**: Align Metric / Unit / Source / Asset registry types with (or introduce) persistence models and CRUD services — still without migrating legacy mappings or changing ingestion — *or* follow `IMPLEMENTATION_SEQUENCE.md` Stage 3 if database models are the agreed next step.

Await explicit approval before proceeding.
