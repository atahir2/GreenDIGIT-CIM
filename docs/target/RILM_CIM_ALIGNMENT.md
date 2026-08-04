# RILM ↔ CIM Alignment

> **Milestone 8** · Research Infrastructure Lifecycle Model stages linked to CIM metrics

---

## Seeded stages

`planning` → `design` → `procurement` → `deployment` → `operation` → `optimisation` → `reproducibility` → `reporting` → `continuous_improvement` → `decommissioning`

## Initial metric alignments

| CIM metric | Stages | Importance notes |
|------------|--------|------------------|
| `cim:energy.efficiency.pue` | operation, reporting, continuous_improvement | operation/reporting required; CI recommended |
| `cim:compute.node.power.draw` | operation, optimisation, reproducibility, reporting | reporting conditional |
| `cim:compute.gpu.power.average` | same as node power | reporting conditional |
| `cim:workflow.energy.per_run` | operation, reproducibility, reporting | reproducibility primary |
| `cim:carbon.emission.operational` | operation, reporting | both primary |
| `cim:water.usage.total` | operation, reporting | both primary |

## Policy

* Only seeded links are returned.
* Metrics without links return empty lifecycle lists.
* Asset-level `lifecycle_stage_id` remains separate from metric links.
