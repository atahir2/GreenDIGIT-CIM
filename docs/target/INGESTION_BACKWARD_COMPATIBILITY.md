# Ingestion Backward Compatibility

> **Milestone 7** · What stays the same when the registry orchestrator is introduced

---

## Guarantees

1. **Default `process_metric_sample` behaviour unchanged** — `use_registry_orchestrator=False` by default.
2. **Real-time / API / AWS / GCP / Streamlit** remain on the legacy classifier path.
3. **Legacy mapping fallback** inside Mapping Registry remains enabled (`use_fallback=True`).
4. **Old ingestion functions are not removed** (`ingest_from_api`, ensemble, `map_raw_to_unified`, etc.).
5. **Storage sinks unchanged** — samples, Influx, JSON sync, definitions, upload logs.
6. **Soft enrichment** — unit / source / asset issues produce warnings/flags; they do not abort ingestion.
7. **Existing tests** for mapping, unit, source/asset registries must continue to pass.

---

## Opt-in surface

| Call site | Orchestrator |
|-----------|--------------|
| `ingest_from_file()` | On by default; `use_registry_orchestrator=False` restores pre-M7 behaviour |
| `process_metric_sample(..., use_registry_orchestrator=True)` | Explicit opt-in |
| All other callers | Off |

---

## Fallback policy (orchestrator)

```
registry hit     → use registry result, fallback_used=false
registry miss + legacy hit → use legacy result, fallback_used=true, status=candidate
both miss        → unresolved/candidate flags; caller may use ensemble for storage
```

---

## Rollback

1. Call `ingest_from_file(..., use_registry_orchestrator=False)`, or
2. Stop passing `use_registry_orchestrator=True` to `process_metric_sample`, or
3. Revert the unified_ingestion default to `False`.

Legacy classifiers and Mapping Registry fallback continue to operate independently of the orchestrator package.

---

## Out of scope for Milestone 7

* Lifecycle / standards / provenance / evidence governance beyond existing sample provenance hooks
* Removing legacy fallback
* Rewiring all ingestion paths
* Full rewrite of `process_metric_sample`
