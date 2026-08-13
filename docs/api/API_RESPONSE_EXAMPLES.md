# API Response Examples

> **Milestone 16C** · Illustrative responses from `POST /api/v1/cim-ingest/metrics`  
> Field shapes match `OrchestratorResult.to_metadata()` plus MS16C wrappers.

## Scenario A — known operational (abbreviated)

```json
{
  "status": "accepted",
  "organization_id": "ri-org-a",
  "source": "prometheus_node_exporter",
  "metrics_processed": 1,
  "resolved_count": 1,
  "unresolved_count": 0,
  "validation_issue_count": 0,
  "results": [
    {
      "raw_metric_name": "node_power_watts",
      "observed_value": 420,
      "observed_unit": "W",
      "cim_namespace": "cim:compute.node.power.draw",
      "resolved": true,
      "resolution_path": "registry",
      "mapping_status": "approved",
      "unit_validation_status": "valid",
      "canonical_unit": "W",
      "expected_quantity_kind": "Power",
      "source_resolution_status": "candidate_created",
      "asset_resolution_status": "candidate_created",
      "lifecycle_stages": ["operation", "optimisation"],
      "standards_relation_types": ["inputToKPI", "contextualMatch"],
      "evidence_readiness_status": "declared",
      "provenance_record_id": 12,
      "extension_candidate_id": null,
      "critical_issues": [],
      "accepted_as_valid": true
    }
  ],
  "kpi": null,
  "orchestrator": "RegistryOrchestratorService"
}
```

## Scenario B — wrong unit (abbreviated)

```json
{
  "status": "accepted_with_validation_issues",
  "organization_id": "ri-org-b",
  "metrics_processed": 1,
  "validation_issue_count": 1,
  "results": [
    {
      "raw_metric_name": "node_power_watts",
      "observed_value": 420,
      "observed_unit": "kWh",
      "cim_namespace": "cim:compute.node.power.draw",
      "resolved": true,
      "unit_validation_status": "incompatible",
      "canonical_unit": "W",
      "candidate_flags": { "unit_incompatible": true },
      "critical_issues": ["unit_incompatible"],
      "accepted_as_valid": false
    }
  ]
}
```

Mapping may still resolve; the payload is **not** treated as unit-valid.

## Scenario C — workflow (abbreviated)

```json
{
  "status": "accepted",
  "organization_id": "ri-org-c",
  "metrics_processed": 2,
  "results": [
    {
      "raw_metric_name": "workflow_energy_per_run",
      "cim_namespace": "cim:workflow.energy.per_run",
      "resolved": true,
      "lifecycle_stages": ["reproducibility", "operation"],
      "standards_relation_types": ["contextualMatch"],
      "provenance_record_id": 44
    },
    {
      "raw_metric_name": "workflow_carbon_per_run",
      "cim_namespace": "cim:workflow.carbon.per_run",
      "resolved": true
    }
  ]
}
```

Workflow metrics keep `workflow_id` / `run_id` in orchestrator context. Seeded standards use contextual/close relations — not false ISO/EN `exactMatch`.

## Scenario D — facility + PUE (abbreviated)

```json
{
  "status": "accepted",
  "organization_id": "ri-org-d",
  "metrics_processed": 4,
  "results": [
    {
      "raw_metric_name": "total_facility_energy",
      "cim_namespace": "cim:facility.energy.consumption.total",
      "resolved": true
    },
    {
      "raw_metric_name": "it_equipment_energy",
      "cim_namespace": "cim:facility.it.energy.consumption",
      "resolved": true
    }
  ],
  "kpi": {
    "kpi_namespace": "cim:energy.efficiency.pue",
    "calculation_status": "calculated",
    "value": 1.5,
    "unit": "ratio",
    "reportable_approved": true,
    "provenance_record_id": 90,
    "aggregation_period": "monthly",
    "boundary": "facility"
  }
}
```

If facility energy unit is `W` instead of `kWh`, KPI returns `calculation_status: "invalid_unit"` (or `blocked`) and `reportable_approved: false`.

## Scenario E — unknown extension (abbreviated)

```json
{
  "status": "accepted_with_candidates",
  "organization_id": "ri-org-e",
  "unresolved_count": 1,
  "results": [
    {
      "raw_metric_name": "workflow_green_score",
      "cim_namespace": null,
      "resolved": false,
      "resolution_path": "unresolved",
      "mapping_status": "unresolved",
      "extension_candidate_id": 3,
      "review_required": true,
      "accepted_as_valid": false
    }
  ]
}
```

Status remains candidate / under_review. No approved standards mapping is created automatically.
