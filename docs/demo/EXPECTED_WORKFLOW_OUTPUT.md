# Expected Output — Scenario C (Workflow Reproducibility)

## Input

```text
workflow_energy_per_run = 0.42 kWh
workflow_id = wf-204
workflow_run_id / run_id = run-2026-001
```

## Expected orchestrator fields

| Field | Expected |
|-------|----------|
| `cim_namespace` | `cim:workflow.energy.per_run` |
| `unit_validation_status` | `valid` |
| `expected_quantity_kind` | `Energy` |
| `canonical_unit` | `kWh` |
| `lifecycle_stages` | includes `reproducibility`, `operation` |
| `standards_mappings` | PROV-O / RO-CRATE / SCHEMA-ORG / QUDT as `contextualMatch` when seeded |
| ISO/EN `exactMatch` | **must not** appear for this metric |
| `evidence_requirements` | includes PROV-O audit and/or RO-CRATE document (seeded) |
| `original_raw_metadata.workflow_id` | `wf-204` |
| `original_raw_metadata.run_id` | `run-2026-001` |
| `provenance_record_id` | set |
