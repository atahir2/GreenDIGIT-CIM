# Sample Datasets (CIM Demo)

Fixtures live under `tests/fixtures/cim_demo/`.

## Schema

Each JSON sample:

```json
{
  "scenario": "...",
  "description": "...",
  "context": { "source": "...", "asset_labels": {}, "timestamp": "..." },
  "metrics": [{ "name": "...", "value": 0, "unit": "..." }]
}
```

Facility sample additionally includes `pue_preparation` for PUE input readiness.

## Files

| File | Metrics (summary) |
|------|-------------------|
| `known_metrics_sample.json` | `node_power_watts` 420 W, `gpu_avg_power` 185 W, `cpu_utilisation` 73 %, `memory_used` 64 GB, `network_ingress` 1.2 GB; source `prometheus_node_exporter`; node `hpc-node-07` / cluster-A / RI-site-1 |
| `wrong_units_sample.json` | Power as kWh, energy as W, carbon intensity as kgCO2e |
| `workflow_run_metrics_sample.json` | Duration 3600 s, energy 0.42 kWh, carbon 0.11 kgCO2e; `wf-204` / `run-2026-001` |
| `facility_kpi_sample.json` | Facility 1200 kWh, IT 800 kWh, water 2.5 m3, carbon 250 kgCO2e; monthly / facility boundary; prepared PUE = 1.5 |
| `unknown_metrics_sample.json` | `workflow_green_score`, `carbon_aware_scheduling_gain`, `experimental_efficiency_index` |
| `unstructured_metrics_sample.txt` | Free-text for existing `parse_unstructured_text()` |

## Demo raw → CIM mappings

Created idempotently by `ensure_demo_mappings()` (origin=`demo`):

| Raw key | CIM namespace |
|---------|--------------|
| `node_power_watts` | `cim:compute.node.power.draw` |
| `gpu_avg_power` | `cim:compute.gpu.power.average` |
| `cpu_utilisation` | `cim:compute.cpu.utilisation` |
| `memory_used` | `cim:compute.memory.usage` |
| `network_ingress` | `cim:network.traffic.ingress` |
| `energy_consumption` | `cim:energy.consumption.total` |
| `carbon_intensity` | `cim:carbon.intensity.location_based` |
| `workflow_*` | corresponding `cim:workflow.*` |
| `total_facility_energy` | `cim:facility.energy.consumption.total` |
| `it_equipment_energy` | `cim:facility.it.energy.consumption` |
| `water_usage_total` | `cim:water.usage.total` |
| `carbon_emission_operational` | `cim:carbon.emission.operational` |
| `energy_efficiency_pue` | `cim:energy.efficiency.pue` |

Unknown metrics are **not** pre-mapped.
