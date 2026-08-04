# Milestone 6 — Source & Asset Registry Integration

> **Status**: Implemented  
> **Date**: 2026-08-04  
> **Depends on**: Milestones 1–5

---

## Objective

Resolve or create candidate sources and assets from ingestion metadata, and
attach soft resolution results to registry-first mapping lookup without breaking
legacy callers or ingestion.

## Deliverables

* `cloud_metrics/registry/source/service.py` (CIM-backed)
* `cloud_metrics/registry/asset/service.py` (CIM-backed + hierarchy)
* `cloud_metrics/registry/context_extract.py`
* Mapping lookup `context` / `source_resolution` / `asset_resolution`
* Docs under `docs/target/LEGACY_SOURCE_AND_ASSET_HANDLING.md`,
  `SOURCE_REGISTRY_INTEGRATION.md`, `ASSET_REGISTRY_INTEGRATION.md`,
  `ASSET_HIERARCHY_MODEL.md`, `SOURCE_AND_ASSET_RESOLUTION_POLICY.md`
* Tests: `tests/test_source_asset_registry.py`

## Untouched

* Full ingestion pipeline refactor
* Legacy `Source` / `Asset` / `Datacenter` tables
* Hard-fail on missing source/asset
* Lifecycle / standards / provenance / evidence integration

## Verification

```bash
pytest tests/test_source_asset_registry.py -q
pytest tests/test_unit_registry_validation.py tests/test_mapping_registry_migration.py tests/test_registry_skeleton.py -q
```
