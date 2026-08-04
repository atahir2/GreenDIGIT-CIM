# Registry-First Mapping Lookup

> **Milestone 4** · Lookup contract for Metric / Mapping Registries

---

## API

```python
from cloud_metrics.registry.mapping import resolve_raw_metric, MappingRegistryService

# Convenience
result = resolve_raw_metric(
    "energy_wh",
    session=session,
    use_fallback=True,
    create_candidate_on_fallback=False,
)

# Service
svc = MappingRegistryService(session=session)
result = svc.resolve_with_fallback("energy_wh")
entry = svc.resolve("energy_wh")  # registry-only; no fallback
```

Without a session, the service keeps the Milestone 1 skeleton contract
(`list_entries() == []`, `resolve() is None`).

---

## Flow

```
input: raw_key (+ optional source_id)
        │
        ▼
┌───────────────────────────────┐
│ cim_metric_mappings           │
│ status ∈ {approved, active}   │
└───────────────┬───────────────┘
                │ hit
                ▼
        return linked cim:* namespace
        + mapping metadata
        resolution_path = "registry"
                │ miss
                ▼
┌───────────────────────────────┐
│ Legacy fallback (if enabled)  │
│ 1. map_raw_to_unified (JSON)  │
│ 2. resolve_mapping (CimMapping)│
│ 3. guess_from_alias (ALIASES) │
└───────────────┬───────────────┘
                │ hit
                ▼
        return cim:* (via gd_to_cim) as candidate
        resolution_path = "legacy_fallback"
        optional: create candidate mapping / metric
                │ miss
                ▼
        resolved=False, status=unresolved
        (caller is not broken)
```

---

## Logging

| Event | Log message fragment |
|-------|----------------------|
| Registry hit | `registry mapping hit` |
| Legacy fallback | `legacy fallback hit` |
| Unresolved | `unresolved metric` |
| Candidate mapping | `candidate mapping created` |
| Candidate metric | `candidate metric definition created` |
| Duplicate skip | `duplicate mapping skipped` |

Logger name: `cloud_metrics.registry.mapping.service` /
`cloud_metrics.registry.migration.sync`.

---

## Result shape

`MappingLookupResult`:

| Field | Meaning |
|-------|---------|
| `resolved` | True if a namespace was found (registry or fallback) |
| `resolution_path` | `registry` \| `legacy_fallback` \| `unresolved` |
| `cim_namespace` | Canonical ``cim:*`` key when resolved |
| `legacy_unified_key` | ``gd.*`` key when known |
| `status` | `approved` \| `candidate` \| `unresolved` |
| `candidate_created` | True if fallback backfill wrote a row |
| `mapping` | `MappingEntry` when available |

---

## Non-goals (this milestone)

* Replacing `services.mapping_registry_service.resolve_mapping`
* Changing FastAPI `/mappings` to ``cim_metric_mappings``
* Making classifiers call this path by default
