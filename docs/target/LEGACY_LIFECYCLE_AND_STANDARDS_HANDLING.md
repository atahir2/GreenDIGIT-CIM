# Legacy Lifecycle and Standards Handling

> **Milestone 8** · Baseline before lifecycle/standards orchestration integration

---

## Current state (pre–Milestone 8 wiring)

### Lifecycle

| Layer | Location | Behaviour |
|-------|----------|-----------|
| DB model | `cim_lifecycle_stages`, `cim_metric_lifecycle_links` | Seeded stages + metric↔stage links with `relevance` |
| Seed | `cloud_metrics/registry/seed/data.py` | RILM-oriented stages (planning → decommissioning) and links for key metrics |
| Skeleton service | `cloud_metrics/registry/lifecycle/` | Placeholder (`list_entries` empty without this milestone) |
| Legacy wrapper | `cloud_metrics/services/lifecycle_registry_service.py` | Delegates to skeleton |
| Asset FK | `cim_assets.lifecycle_stage_id` | Optional asset-level stage only |
| Orchestrator (M7) | `RegistryOrchestratorService` | **Did not** return lifecycle metadata |

Relevance values in seed: `primary`, `secondary`, `conditional` (mapped in M8 to importance `required` / `recommended` / `conditional`).

### Standards

| Layer | Location | Behaviour |
|-------|----------|-----------|
| DB model | `cim_standards`, `cim_standard_terms`, `cim_metric_mappings.standard_id` | Catalogue + mappings via Mapping Registry rows |
| Seed | `STANDARD_MAPPINGS` in seed data | Safe relations (`exactMatch` only for PUE↔ISO/EN, etc.) |
| Skeleton service | `cloud_metrics/registry/standards/` | Placeholder |
| Legacy | `cloud_metrics/services/standards_registry.py` | Older attach helpers for non-`cim_*` path |
| Orchestrator (M7) | — | **Did not** return standards mapping metadata |

### What was *not* done before M8

* No orchestrator enrichment for lifecycle or standards
* No API enforcing “no false exactMatch”
* Candidate metrics could theoretically be joined to approved standard rows if queried naively

---

## Seeded lifecycle links (already present)

| Metric | Stages (relevance) |
|--------|-------------------|
| `cim:energy.efficiency.pue` | operation (primary), reporting (primary), continuous_improvement (secondary) |
| `cim:compute.node.power.draw` | operation, optimisation, reproducibility, reporting (conditional) |
| `cim:compute.gpu.power.average` | same pattern as node power |
| `cim:workflow.energy.per_run` | operation, reproducibility, reporting |
| `cim:carbon.emission.operational` | operation, reporting |
| `cim:water.usage.total` | operation, reporting |

---

## Milestone 8 change

Lifecycle and Standards registry services become session-backed look-ups. The Registry Orchestrator attaches additive metadata after mapping resolution. Missing links never break ingestion.
