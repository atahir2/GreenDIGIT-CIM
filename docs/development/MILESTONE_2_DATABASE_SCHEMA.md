# Milestone 2 — Database Schema and Migration Layer

> **Status**: Completed (pending review)  
> **Date**: 2026-08-03  
> **Depends on**: Milestone 1 registry skeleton

---

## Objective

Introduce an additive, reversible `cim_*` database schema aligned with the Milestone 1 registry modules, without changing ingestion or migrating legacy mapping data.

## Deliverables

* ORM models: `cloud_metrics/models/cim_registry.py` (14 tables)
* Alembic revision: `c2f8a1b9e047_add_cim_registry_tables.py` (upgrade + downgrade)
* Tests: `tests/test_cim_registry_migration.py`
* Docs: `REGISTRY_DATABASE_MODEL.md`, `REGISTRY_SCHEMA_REFERENCE.md`, updated `DATABASE_MIGRATION_PLAN.md`

## Explicitly untouched

* Ingestion / classifiers / namespace generation
* Mapping data migration / full registry seeding
* Dropping or renaming legacy / Antigravity tables
* Switching runtime services from old tables to `cim_*`

## Verification

```bash
pytest tests/test_cim_registry_migration.py -q
pytest tests/ -q
```

## Next milestone (recommended)

Wire placeholder registry services to the new `cim_*` ORM (CRUD) for Metric / Unit / Source / Asset — still without changing ingestion — **or** dual-write / migrate catalogue data once CRUD is stable.
