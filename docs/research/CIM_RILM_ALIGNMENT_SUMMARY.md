# CIM ↔ RILM Alignment Summary

> Research packaging · Milestone 15

## Research Infrastructure Lifecycle Model (RILM) stages

Seeded sequence:

`planning` → `design` → `procurement` → `deployment` → `operation` → `optimisation` → `reproducibility` → `reporting` → `continuous_improvement` → `decommissioning`

## Metric–stage links (curated, not inferred)

| Metric | Stages (importance) |
|--------|---------------------|
| PUE | operation, reporting (required); continuous improvement (recommended) |
| Node / GPU power | operation (primary); optimisation, reproducibility; reporting (conditional) |
| Workflow energy per run | operation, reproducibility (primary); reporting |
| Operational carbon / water | operation, reporting (primary) |

Links are stored in `cim_metric_lifecycle_links` with `relevance` mapped to required / recommended / conditional. Metrics without seed links export **empty** lifecycle lists.

## Reproducibility packaging

Workflow energy is the RILM **reproducibility** exemplar. The RO-Crate-style exporter packages workflow id, run id, duration, energy per run, carbon per run, provenance, and conservative standards mappings (PROV-O / RO-Crate as `contextualMatch`, not ISO KPI identity).

## Limits

- Asset `lifecycle_stage_id` is separate from metric–stage links.
- No automatic assignment of stages during ingestion.
- Export of lifecycle mappings is a CIM table dump, not an RILM ontology.

Detail: `docs/target/RILM_CIM_ALIGNMENT.md`.
