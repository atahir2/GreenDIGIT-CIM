# Registry Orchestrator

> **Milestone 7** · Central coordinator for registry-driven metric resolution during ingestion

---

## Purpose

`RegistryOrchestratorService` (`cloud_metrics/registry/orchestrator/`) accepts a normalized raw metric context and coordinates:

| Registry | Role |
|----------|------|
| Mapping Registry | Registry-first lookup + legacy fallback (`resolve_raw_metric`) |
| Metric Registry | Linked via mapping → namespace / definition id / quantity kind |
| Unit Registry | Soft observed-unit validation |
| Source Registry | Soft source resolve / candidate create |
| Asset Registry | Soft asset resolve / candidate create |

It does **not** own storage (Influx / samples / JSON). Callers adapt `OrchestratorResult` into existing sinks.

---

## API

### Input — `RawMetricContext`

* `raw_metric_name`, `value`, `unit`, `timestamp`
* `source` / `source_type` / `source_metadata`
* `asset_labels`, `tags`, `labels`
* `original_raw_metadata`

### Output — `OrchestratorResult`

* `raw_metric_name`, `cim_namespace`, `metric_definition_id`
* `mapping_status`, `mapping_confidence`
* `unit_validation_status`, `observed_unit`, `canonical_unit`, `expected_quantity_kind`
* `source_resolution_status`, `source_id`
* `asset_resolution_status`, `asset_id`
* `candidate_flags`, `warnings`, `errors`
* `fallback_used`, `original_raw_metadata`
* Adapter helpers: `resolved`, `resolution_path`, `legacy_unified_key`, `storage_unified_key`

Aliases: `RegistryOrchestrator`, `CimRegistryOrchestrator`.

Factory: `get_registry_orchestrator(session=None)`.

---

## Behaviour

1. Log `registry orchestrator invoked`.
2. Call `resolve_raw_metric` with fallback enabled by default.
3. Attach unit / source / asset outcomes already produced by Milestones 5–6.
4. Set `fallback_used` when `resolution_path == legacy_fallback`.
5. Derive `storage_unified_key` from `legacy_unified_key` or `cim:*` → `gd.*` for legacy sinks.
6. Never raise on unresolved metrics; return status + flags instead.
7. Never silently mark unresolved metrics as `approved`.

---

## Logging

| Event | Level |
|-------|-------|
| Orchestrator invoked | INFO |
| Registry mapping hit | INFO |
| Legacy fallback used | INFO |
| Unit validation result | INFO |
| Source / asset resolution | INFO |
| Unresolved / candidate | INFO |
| Warnings / errors summary | INFO |
| Unexpected exception | EXCEPTION → unresolved result |

---

## Naming

Preferred service name in this codebase: **`RegistryOrchestratorService`** (matches `*RegistryService` pattern). Short aliases are exported for the milestone brief.
