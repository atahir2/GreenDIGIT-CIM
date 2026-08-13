# Organization Onboarding Flow

> **Milestone 16C** · How an external organization / RI joins CIM via API

## Overview

```text
register source → send sample payload → review candidates →
approve stable mappings → repeated ingestion → export / report
```

## Step 1 — Register organization / source

Identify the organization and the technical source that will push metrics.

| Field | Example |
|-------|---------|
| `organization_id` | `ri-site-1` / `org-acme-hpc` |
| `source` | `prometheus_node_exporter` |
| `source_type` | `monitoring_system`, `workflow_instrumentation`, `building_management_system`, `api` |

On first ingest, Source and Asset registries resolve existing rows or create **candidates** (`status=candidate`, `review_status=under_review`). Nothing is auto-approved.

Optional legacy registry create (not required for CIM path):

```http
POST /api/v1/registry/sources
POST /api/v1/registry/assets
```

## Step 2 — Define source type and asset labels

Include enough context for governance:

- `source_metadata` (job, instance, collector)
- `asset` / `asset_labels` (node, site, cluster, facility)
- For workflows: `workflow_id`, `run_id`
- For facility KPIs: `aggregation_period`, `boundary`

## Step 3 — Send a sample payload

```http
POST /api/v1/cim-ingest/metrics
```

Start with known operational metrics (Scenario A). Confirm:

- `cim_namespace` resolved
- `unit_validation_status` valid
- `provenance_record_id` present

Then send one unknown metric (Scenario E style) with `use_fallback: false` to verify extension candidate creation.

## Step 4 — Review candidate mappings / extensions

```http
GET /api/v1/cim-review/candidates
GET /api/v1/cim-review/candidates/extension/{id}
```

Or use Admin Portal → Candidate review (http://127.0.0.1:8502).

All decisions go through **AdminReviewService** (approve / reject / merge / request_changes / promote_to_seed).

## Step 5 — Approve stable mappings

Only after human review:

```http
POST /api/v1/cim-review/candidates/mapping/{id}/approve
{
  "reviewer": "ri-admin",
  "notes": "Stable Prometheus power mapping"
}
```

`promote_to_seed` writes a **proposal file**, never silently mutates canonical seed.

## Step 6 — Enable repeated ingestion

Once mappings are approved:

- Same raw keys resolve via Mapping Registry (`resolution_path=registry`)
- Units continue to validate
- Provenance continues to record orchestration events
- Optional `persist_samples: true` stores observations in `metric_samples`

Recommended production cadence: batch or streaming POST of metrics with org/source/timestamp.

## Step 7 — Export / report results

| Goal | Endpoint |
|------|----------|
| Full catalogue JSON | `GET /api/v1/cim-export/json` |
| Evidence readiness | `GET /api/v1/cim-export/evidence-readiness?namespace=cim:energy.efficiency.pue` |
| Standards crosswalk | `GET /api/v1/cim-export/standards-crosswalk` |
| Provenance | `GET /api/v1/cim-export/provenance` |
| Workflow package | `POST /api/v1/cim-export/rocrate-style` |
| KPI | `POST /api/v1/cim-kpi/pue` |

## Roles

| Role | Responsibility |
|------|----------------|
| RI integrator | Sends payloads, monitors `critical_issues` |
| CIM reviewer | Approves/rejects candidates in portal or review API |
| Operator | Seeds registries, runs migrations, manages secrets |

## Do not

- Auto-approve unknowns in the integrator client
- Bypass Admin Review with direct SQL
- Treat `incompatible` unit results as reportable KPIs
- Expect legacy `/metrics/aws` GET triggers to carry org payloads
