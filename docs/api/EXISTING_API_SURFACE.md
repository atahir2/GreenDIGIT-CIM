# Existing API Surface

> **Milestone 16C** · Inventory of FastAPI routes before / after CIM API ingest

Base URL (local): `http://127.0.0.1:8000`  
Interactive docs: `http://127.0.0.1:8000/docs`

## Health

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness `{"status":"ok"}` |

## Legacy ingest / query

| Method | Path | Purpose | Orchestrator? |
|--------|------|---------|---------------|
| GET | `/metrics/aws` | Trigger AWS cloud ingest helper | No (legacy `ingest_from_api`) |
| GET | `/metrics/gcp` | Trigger GCP cloud ingest helper | No (legacy `ingest_from_api`) |
| GET | `/query/` | Query InfluxDB time-series | N/A (read) |

Notes:

- `/metrics/aws` and `/metrics/gcp` are **GET triggers**, not payload ingest endpoints.
- Legacy `ingest_from_api()` calls `process_metric_sample` **without** `use_registry_orchestrator=True`.

## Legacy registry API (`/api/v1/registry`)

CRUD-style endpoints over **legacy** tables (`MetricDefinition`, `Unit`, `Source`, `Asset`, `CimMapping`, `ProvenanceRecord`):

| Method | Path |
|--------|------|
| GET/POST | `/quantity-kinds`, `/units`, `/metrics`, `/sources`, `/assets`, `/mappings` |
| POST | `/mappings/{id}/approve` |
| GET | `/provenance` |

These do **not** replace CIM `cim_*` catalogues or Admin Review Service.

## CIM Admin Review (`/api/v1/cim-review`)

| Method | Path | Backend |
|--------|------|---------|
| GET | `/candidates` | `AdminReviewService.list_pending` |
| GET | `/candidates/{entity_type}/{entity_id}` | `get_entry` |
| POST | `/candidates/.../approve\|reject\|merge\|promote\|deprecate` | `AdminReviewService.apply` |

## CIM KPI (`/api/v1/cim-kpi`)

| Method | Path | Backend |
|--------|------|---------|
| POST | `/{kpi}` where `kpi` ∈ `pue\|wue\|cue` | `KpiCalculationService` |

## CIM Export (`/api/v1/cim-export`)

| Method | Path |
|--------|------|
| GET | `/json`, `/csv/{dataset}`, `/jsonld`, `/standards-crosswalk`, `/evidence-readiness`, `/provenance`, `/dcat-style` |
| POST | `/rocrate-style`, `/dcat-style` |

Read-only. Does not mutate registries.

## CIM Ingest — added in MS16C (`/api/v1/cim-ingest`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/metrics` | External org/RI metric payload → Registry Orchestrator |
| POST | `/scenarios/{A-E}` | Demo fixture convenience for integration validation |

Uses `RegistryOrchestratorService` (same path as Milestone 10 demonstrator). Unknown metrics are **never auto-approved**.

## Gaps (documented, not rewritten)

| Gap | Status |
|-----|--------|
| Authenticated multi-tenant org tokens | Not implemented — see `API_SECURITY_AND_AUTH_NOTES.md` |
| File upload over HTTP (multipart) | Not required; browser UI covers files |
| Legacy `/metrics/aws|gcp` on orchestrator | Left unchanged to preserve behaviour |
| Evidence fulfillment store via API | Requirements exported; fulfillment not persisted |
| Rate limiting / quotas | Not implemented |
