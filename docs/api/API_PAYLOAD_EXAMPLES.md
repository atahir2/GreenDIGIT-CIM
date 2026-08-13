# API Payload Examples

> **Milestone 16C** · Request bodies for `POST /api/v1/cim-ingest/metrics`

## Scenario A — known operational metric

```json
{
  "organization_id": "ri-org-a",
  "source": "prometheus_node_exporter",
  "source_type": "monitoring_system",
  "timestamp": "2026-08-07T10:15:00Z",
  "source_metadata": {
    "job": "node_exporter",
    "instance": "hpc-node-07:9100"
  },
  "asset": {
    "node": "hpc-node-07",
    "host": "hpc-node-07",
    "cluster": "cluster-A",
    "site": "RI-site-1"
  },
  "metrics": [
    { "name": "node_power_watts", "value": 420, "unit": "W" }
  ],
  "options": { "ensure_demo_mappings": true }
}
```

## Scenario B — wrong unit

```json
{
  "organization_id": "ri-org-b",
  "source": "prometheus_node_exporter",
  "source_type": "monitoring_system",
  "timestamp": "2026-08-07T10:20:00Z",
  "asset": { "node": "hpc-node-07", "site": "RI-site-1" },
  "metrics": [
    { "name": "node_power_watts", "value": 420, "unit": "kWh" }
  ]
}
```

## Scenario C — workflow / reproducibility

```json
{
  "organization_id": "ri-org-c",
  "source": "workflow_energy_profiler",
  "source_type": "workflow_instrumentation",
  "workflow_id": "wf-204",
  "run_id": "run-2026-001",
  "formula_or_derivation_method": "sum_of_node_energy_over_run_window",
  "timestamp": "2026-08-07T11:00:00Z",
  "asset": {
    "node": "hpc-node-07",
    "cluster": "cluster-A",
    "site": "RI-site-1",
    "allocated_cores": 32
  },
  "metrics": [
    { "name": "workflow_energy_per_run", "value": 0.42, "unit": "kWh" },
    { "name": "workflow_carbon_per_run", "value": 0.11, "unit": "kgCO2e" }
  ]
}
```

## Scenario D — facility / KPI inputs

```json
{
  "organization_id": "ri-org-d",
  "source": "facility_bms",
  "source_type": "building_management_system",
  "aggregation_period": "monthly",
  "boundary": "facility",
  "timestamp": "2026-07-31T23:59:59Z",
  "asset": { "site": "RI-site-1", "facility": "RI-site-1-main" },
  "metrics": [
    { "name": "total_facility_energy", "value": 1200, "unit": "kWh" },
    { "name": "it_equipment_energy", "value": 800, "unit": "kWh" },
    { "name": "water_usage_total", "value": 2.5, "unit": "m3" },
    { "name": "carbon_emission_operational", "value": 250, "unit": "kgCO2e" }
  ],
  "options": { "calculate_kpi": "pue" }
}
```

## Scenario E — unknown / custom metric

```json
{
  "organization_id": "ri-org-e",
  "source": "research_scheduler",
  "source_type": "experimental_tooling",
  "timestamp": "2026-08-07T12:00:00Z",
  "metrics": [
    { "name": "workflow_green_score", "value": 0.78, "unit": "score" }
  ],
  "options": {
    "use_fallback": false,
    "create_candidate_on_fallback": false,
    "create_extension_on_unresolved": true
  }
}
```

## Persist samples (optional)

Add `"persist_samples": true` under `options` to also write Postgres `metric_samples` through `process_metric_sample(..., use_registry_orchestrator=True)`.
