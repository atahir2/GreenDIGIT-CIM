# Seeded Metric Catalogue

> **Milestone 3** · Initial approved metrics in ``cim_metric_definitions``

All seeded metrics have `status=approved`, `review_status=approved`, `version=1`.

| Namespace | Label | Domain | Quantity kind | Unit | Type |
|-----------|-------|--------|---------------|------|------|
| `cim:energy.power.total` | Total power | energy | Power | W | observed |
| `cim:energy.consumption.total` | Total energy consumption | energy | Energy | kWh | observed |
| `cim:compute.node.power.draw` | Compute node power draw | energy | Power | W | observed |
| `cim:compute.gpu.power.average` | GPU average power | energy | Power | W | observed |
| `cim:facility.energy.consumption.total` | Facility total energy | energy | Energy | kWh | observed |
| `cim:facility.it.energy.consumption` | IT equipment energy | energy | Energy | kWh | observed |
| `cim:compute.cpu.utilisation` | CPU utilisation | performance | Ratio | % | observed |
| `cim:compute.memory.usage` | Memory usage | performance | DataSize | B | observed |
| `cim:storage.capacity.used` | Storage capacity used | storage | DataSize | B | observed |
| `cim:network.traffic.ingress` | Network ingress traffic | network | DataSize | B | observed |
| `cim:network.traffic.egress` | Network egress traffic | network | DataSize | B | observed |
| `cim:carbon.emission.operational` | Operational carbon emission | environment | CarbonEmission | kgCO2e | calculated |
| `cim:carbon.intensity.location_based` | Location-based carbon intensity | environment | CarbonIntensity | gCO2e/kWh | observed |
| `cim:water.usage.total` | Total water usage | environment | WaterVolume | L | observed |
| `cim:workflow.execution.duration` | Workflow execution duration | performance | Time | s | observed |
| `cim:workflow.energy.per_run` | Workflow energy per run | energy | Energy | kWh | calculated |
| `cim:workflow.carbon.per_run` | Workflow carbon per run | environment | CarbonEmission | kgCO2e | calculated |
| `cim:energy.efficiency.pue` | Power Usage Effectiveness | energy | Ratio | ratio | calculated_kpi |
| `cim:energy.efficiency.wue` | Water Usage Effectiveness | environment | Ratio | ratio | calculated_kpi |
| `cim:energy.efficiency.cue` | Carbon Usage Effectiveness | environment | Ratio | ratio | calculated_kpi |

## Lifecycle links (seeded subset)

| Metric | Stages (relevance) |
|--------|--------------------|
| `cim:compute.node.power.draw` | operation (primary), optimisation (secondary), reproducibility (secondary), reporting (conditional) |
| `cim:compute.gpu.power.average` | operation, optimisation, reproducibility, reporting (conditional) |
| `cim:workflow.energy.per_run` | operation, reproducibility, reporting |
| `cim:energy.efficiency.pue` | operation, reporting, continuous_improvement |
| `cim:carbon.emission.operational` | operation, reporting |
| `cim:water.usage.total` | operation, reporting |

Other seeded metrics are catalogue-ready but not yet linked to lifecycle stages (deferred to avoid speculative links).
