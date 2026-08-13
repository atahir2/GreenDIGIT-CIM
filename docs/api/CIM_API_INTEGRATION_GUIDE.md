# CIM API Integration Guide

> **Milestone 16C** · How an external organization or Research Infrastructure connects to CIM via API

## 1. Purpose

External systems send metric payloads to CIM over HTTP. Each metric is processed by the **Registry Orchestrator**, which consults Mapping, Unit, Source, Asset, Lifecycle, Standards, Rule, Evidence, Provenance, and Extension registries. Responses return normalized CIM namespaces and governance metadata — not silent approvals of unknown metrics.

## 2. Prerequisites

```text
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m cloud_metrics.scripts.seed_cim_registries
.venv\Scripts\python.exe -m uvicorn cloud_metrics.main:app --host 127.0.0.1 --port 8000
```

Required env: `DATABASE_URL` (Postgres). Influx optional.

OpenAPI: http://127.0.0.1:8000/docs

## 3. Primary endpoint

```http
POST /api/v1/cim-ingest/metrics
Content-Type: application/json
```

### Minimal curl

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/cim-ingest/metrics ^
  -H "Content-Type: application/json" ^
  -d "{\"organization_id\":\"ri-demo\",\"source\":\"prometheus_node_exporter\",\"source_type\":\"monitoring_system\",\"timestamp\":\"2026-08-07T10:15:00Z\",\"asset\":{\"node\":\"hpc-node-07\",\"site\":\"RI-site-1\"},\"metrics\":[{\"name\":\"node_power_watts\",\"value\":420,\"unit\":\"W\"}]}"
```

### Python

```python
import requests

r = requests.post(
    "http://127.0.0.1:8000/api/v1/cim-ingest/metrics",
    json={
        "organization_id": "ri-demo",
        "source": "prometheus_node_exporter",
        "source_type": "monitoring_system",
        "timestamp": "2026-08-07T10:15:00Z",
        "asset": {"node": "hpc-node-07", "site": "RI-site-1"},
        "metrics": [{"name": "node_power_watts", "value": 420, "unit": "W"}],
        "options": {"ensure_demo_mappings": True},
    },
    timeout=60,
)
print(r.status_code, r.json()["results"][0]["cim_namespace"])
```

## 4. What the orchestrator returns (per metric)

| Field | Meaning |
|-------|---------|
| `cim_namespace` | Canonical CIM id when resolved |
| `resolved` / `resolution_path` | registry / legacy_fallback / unresolved |
| `unit_validation_status` | valid / incompatible / … |
| `source_resolution_status` / `asset_resolution_status` | resolved or candidate |
| `lifecycle_stages` | linked stages |
| `standards_relation_types` | exactMatch / closeMatch / contextualMatch / inputToKPI / … |
| `evidence_readiness_status` | declared readiness |
| `provenance_record_id` | audit trail |
| `extension_candidate_id` | set when unresolved → extension |
| `critical_issues` | unit/rule problems (soft on ingest) |
| `accepted_as_valid` | false when critical issues or unresolved |

## 5. Options

| Option | Default | Use |
|--------|---------|-----|
| `ensure_demo_mappings` | true | Ensure known demo raw→CIM rows exist (local/demo) |
| `use_fallback` | true | Allow legacy fallback; set **false** for unknown-only (Scenario E) |
| `create_extension_on_unresolved` | true | Create/reuse extension candidates |
| `persist_samples` | false | Also write `metric_samples` via `process_metric_sample` |
| `calculate_kpi` | null | After ingest, run `pue` / `wue` / `cue` |

## 6. Related APIs

| Need | Endpoint |
|------|----------|
| Review candidates | `/api/v1/cim-review/candidates` |
| Calculate KPI only | `/api/v1/cim-kpi/{pue\|wue\|cue}` |
| Export catalogue | `/api/v1/cim-export/json` |
| Evidence readiness | `/api/v1/cim-export/evidence-readiness` |

## 7. Demo scenarios helper

```http
POST /api/v1/cim-ingest/scenarios/A
POST /api/v1/cim-ingest/scenarios/B
...
POST /api/v1/cim-ingest/scenarios/E
```

Loads `tests/fixtures/cim_demo/*` through the same ingest service. Scenario E disables fallback. Scenario D requests PUE calculation.

## 8. Invariants

1. Same orchestrator as browser/demo — no parallel mapping rules.
2. Unknown / custom metrics → extension candidate, **not** approved.
3. Wrong units → flagged `incompatible`; not silently treated as valid.
4. Browser/UI behaviour unchanged.
5. Review / approval only via Admin Review Service (API or portal).

See also: [API_PAYLOAD_EXAMPLES.md](API_PAYLOAD_EXAMPLES.md), [API_RESPONSE_EXAMPLES.md](API_RESPONSE_EXAMPLES.md), [ORGANIZATION_ONBOARDING_FLOW.md](ORGANIZATION_ONBOARDING_FLOW.md).
