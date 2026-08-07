# Registry-Driven CIM — Final Architecture (Milestone 10)

> Status after Milestones 1–10: **demonstrator-validated registry-driven CIM**

## Architecture overview

```text
Raw metric input (JSON / ingestion)
        │
        ▼
RawMetricContext
        │
        ▼
RegistryOrchestratorService.process()
        │
        ├── Mapping Registry ──► registry-first resolve
        │         └── legacy fallback (JSON / CimMapping / alias)  [retained]
        ├── Metric Registry (definition, quantity kind, canonical unit)
        ├── Unit Registry (soft validation)
        ├── Source Registry (resolve / candidate)
        ├── Asset Registry (resolve / candidate)
        ├── Lifecycle Registry (stages, purposes)
        ├── Standards Registry (safe relations only)
        ├── Rule Registry (soft validation results)
        ├── Evidence Registry (KPI / reproducibility requirements)
        ├── Provenance Registry (orchestration decision trail)
        └── Extension Registry (unknown → candidate)
        │
        ▼
OrchestratorResult (+ to_metadata())
        │
        └── Adapters → legacy gd.* storage keys / existing sinks
```

## Design principles (preserved)

1. **Additive** — `cim_*` tables alongside legacy models.
2. **Soft enrichment** — unit/source/asset/governance never hard-block ingestion in current milestones.
3. **Registry-first, fallback-second** — Mapping Registry before legacy JSON/alias.
4. **No silent over-claim** — ISO/EN `exactMatch` only where seeded and approved (e.g. PUE).
5. **Candidates for unknowns** — extension / mapping candidates, not false approvals.

## Module map

| Area | Path |
|------|------|
| Orchestrator | `cloud_metrics/registry/orchestrator/` |
| Registries 1–11 | `cloud_metrics/registry/{metric,mapping,unit,source,asset,lifecycle,standards,rule,evidence,provenance,extension}/` |
| Seed | `cloud_metrics/registry/seed/` |
| Models | `cloud_metrics/models/cim_registry.py` |
| Migration | `migrations/versions/c2f8a1b9e047_add_cim_registry_tables.py` |
| Demo | `cloud_metrics/demo/`, `cloud_metrics/scripts/run_cim_demo.py` |
| Fixtures | `tests/fixtures/cim_demo/` |

## Demonstrator role

Milestone 10 validates the architecture with realistic samples and e2e tests. It does **not** replace `process_metric_sample` or remove legacy mapping modules.
