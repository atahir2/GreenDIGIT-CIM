# Backward Compatibility Strategy

> **Milestone 4** · Safe coexistence of legacy mapping paths and ``cim_*`` registries

---

## Principles

1. **Additive first** — new tables and services do not replace callers.
2. **Opt-in registry path** — ingestion continues on legacy helpers until a later milestone.
3. **Fallback always available** — registry miss does not break callers that use `resolve_with_fallback`.
4. **No silent data loss** — noise and uncategorized keys are skipped with counts, not rewritten in JSON.

---

## Dual path (current)

```
raw_key
   │
   ├─► [NEW, opt-in] MappingRegistryService.resolve_with_fallback()
   │         │
   │         ├─ cim_metric_mappings (approved/active)  → registry hit
   │         └─ legacy fallback (JSON / CimMapping / aliases)
   │
   └─► [EXISTING] ensemble_classifier / automated_mapper / map_raw_to_unified
             └─ CimMapping, metric_mapping.json, ALIASES, namespace_generator
```

---

## Guarantees for Milestone 4

| Behaviour | Status |
|-----------|--------|
| Existing ingestion works | Unchanged |
| Existing namespace generation works | Unchanged |
| Existing mapping tests pass | Required |
| Callers forced onto registry-only | **No** |
| Old mapping files removed | **No** |
| Legacy `mapping_registry_service.resolve_mapping` | Untouched |

---

## Fallback behaviour

When using the new lookup:

1. Check ``cim_metric_mappings`` for ``status in {approved, active}``.
2. If miss → legacy: `map_raw_to_unified` → `resolve_mapping` (CimMapping) → `guess_from_alias`.
3. If legacy succeeds → return `resolution_path=legacy_fallback`, `status=candidate`.
4. Optionally (`create_candidate_on_fallback=True`) insert a candidate registry row for later review.
5. If all fail → `resolved=False`, `status=unresolved` (no exception).

---

## Rollback

* Stop calling `resolve_raw_metric` / `migrate_legacy_mappings`.
* Legacy path continues to operate.
* Migrated ``cim_metric_*`` rows can remain (additive) or be cleared with SQL if needed; they do not affect runtime until wired.

---

## Next compatibility step (Milestone 7 — partial)

Unified file ingestion (`ingest_from_file`) opts into `RegistryOrchestratorService`
via `process_metric_sample(..., use_registry_orchestrator=True)`. Other callers
remain on the legacy ensemble path. See `INGESTION_BACKWARD_COMPATIBILITY.md`.

## Next compatibility step (later milestone)

Wire ensemble / automated mapper defaults and real-time paths to registry-first
lookup **with** fallback, then gradually retire JSON and `CimMapping` once
coverage and review are complete.
