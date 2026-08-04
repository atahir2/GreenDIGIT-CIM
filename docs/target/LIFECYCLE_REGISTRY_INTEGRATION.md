# Lifecycle Registry Integration

> **Milestone 8** · Metric ↔ RILM lifecycle stage enrichment

---

## Service

`LifecycleRegistryService` (`cloud_metrics/registry/lifecycle/`)

* `list_entries()` / `get_by_stage(stage)` — catalogue of seeded stages
* `get_links_for_metric(namespace | metric_id)` — links for a CIM metric
* Does **not** invent stages or auto-link metrics

## Output fields

Per link:

| Field | Source |
|-------|--------|
| `stage_key` | `cim_lifecycle_stages.stage_key` |
| `usage_purpose` | Derived from stage (e.g. operation → `operational_monitoring`) |
| `importance` | Mapped from `relevance`: primary→required, secondary→recommended, conditional→conditional |
| `review_status` / `status` | Link governance columns |

## Orchestrator

When a metric resolves to a `cim:*` namespace, `RegistryOrchestratorService` attaches:

* `lifecycle_stages`
* `lifecycle_usage_purposes`
* `lifecycle_importance`
* `lifecycle_review_status`
* `lifecycle_links` (structured)

Missing links → empty lists; ingestion continues.
