# Milestone 4 — Mapping Registry Migration

> **Status**: Implemented  
> **Date**: 2026-08-04  
> **Depends on**: Milestone 1–3 (skeleton, ``cim_*`` schema, approved seed)

---

## Objective

Migrate / synchronize existing metric mapping definitions into the Metric Registry
and Mapping Registry, and provide a registry-first lookup path with legacy
fallback — without breaking ingestion or removing legacy mapping sources.

## Deliverables

* `docs/target/LEGACY_MAPPING_SOURCES.md`
* `docs/target/MAPPING_REGISTRY_MIGRATION.md`
* `docs/target/BACKWARD_COMPATIBILITY_STRATEGY.md`
* `docs/target/REGISTRY_FIRST_MAPPING_LOOKUP.md`
* `docs/target/CANDIDATE_MAPPING_POLICY.md`
* `cloud_metrics/registry/migration/` (discover + sync)
* `cloud_metrics/scripts/migrate_legacy_mappings.py`
* Updated `cloud_metrics/registry/mapping/` (lookup + fallback)
* `tests/test_mapping_registry_migration.py`

## Untouched

* Ingestion pipeline (`automated_mapper`, realtime/unified ingestion)
* Ensemble / alias / semantic classifiers (still primary runtime path)
* Legacy `metric_mapping.json` files (not deleted)
* Legacy `CimMapping` / `mapping_registry_service.resolve_mapping`
* Namespace generation

## Verification

```bash
pytest tests/test_mapping_registry_migration.py -q
pytest tests/ -q
python -m cloud_metrics.scripts.migrate_legacy_mappings --dry-run
```
