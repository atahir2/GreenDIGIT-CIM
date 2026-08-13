# Provenance Export Model

> **Milestone 15** · PROV-O-**like** (not full PROV-O RDF)

## Status

Implemented as a structured JSON extract of `cim_provenance_records`. Profile: `prov-o-like`.

Not implemented: PROV-N, PROV-XML, PROV-O Turtle, or a complete Activity–Entity–Agent graph with qualified relations.

## Record fields

| Field | Source |
|-------|--------|
| `entity_type` | `cim_provenance_records.entity_type` |
| `entity_id` | `entity_id` |
| `activity` | `activity` |
| `agent` | `agent` |
| `inputs` | JSON `inputs` |
| `outputs` | JSON `outputs` |
| `timestamp` | `started_at` or `created_at` |
| `status` | governance `status` |
| `notes` | `notes` |

Also exported: `started_at`, `ended_at`, `method`, `prov_uri` when present.

## Typical chains

| Scenario | Activities |
|----------|------------|
| Orchestrated ingestion | `orchestration`, `registry_mapping_lookup`, unit/source/asset/lifecycle/standards/evidence events |
| Admin review | `approve` / `reject` / `edit` / `merge` / `deprecate` (Milestone 12) |
| KPI calculation | `kpi_calculation` (Milestone 13) |

Filter with `entity_type` + `entity_id` to retrieve one chain.

JSON-LD metric export may attach a **reference** to the latest `metric_definition` provenance record (`prov:Entity`). That is a pointer, not a full PROV graph.

## API

```text
GET /api/v1/cim-export/provenance
GET /api/v1/cim-export/provenance?entity_type=kpi_calculation&entity_id=12
```
