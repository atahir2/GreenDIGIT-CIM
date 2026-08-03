# Milestone 3 — Registry Seed Data

> **Status**: Completed (pending review)  
> **Date**: 2026-08-03  
> **Depends on**: Milestone 1 skeleton, Milestone 2 `cim_*` schema

---

## Objective

Populate additive `cim_*` tables with a trusted, idempotent initial catalogue so later milestones can migrate mappings and connect ingestion safely.

## Deliverables

* `cloud_metrics/registry/seed/` (`data.py`, `loader.py`)
* CLI: `cloud_metrics/scripts/seed_cim_registries.py`
* Tests: `tests/test_cim_registry_seed.py`
* Docs under `docs/target/REGISTRY_SEED_*.md` and related seed catalogues

## Untouched

* Ingestion pipeline
* Legacy mapping migration
* Namespace generation
* Runtime wiring of registries into classifiers / API

## Verification

```bash
pytest tests/test_cim_registry_seed.py -q
pytest tests/ -q
```
