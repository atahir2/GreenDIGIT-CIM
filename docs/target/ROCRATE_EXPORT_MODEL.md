# RO-Crate-style Export Model

> **Milestone 15** · **Partial** / RO-Crate-ready metadata package

## Status

This exporter produces an **RO-Crate-style** (also called **RO-Crate-ready**) JSON object:

- Uses `@context`: `https://w3id.org/ro/crate/1.1/context`
- Includes a `ro-crate-metadata.json` CreativeWork that *mentions* RO-Crate 1.1
- Does **not** write a crate directory, payload files, or run an RO-Crate validator
- Is **not** claimed as full RO-Crate 1.1 compliance

Profile: `ro-crate-style`. `compliance.full_standards_compliance` = `false`.

## Workflow run package

`export_rocrate_style(WorkflowRunExportRequest)` includes:

| Content | Where |
|---------|--------|
| Workflow ID | `@graph` workflow entity + `cim_payload.workflow_id` |
| Workflow run ID | run entity `@id` `#workflow-run/{id}` |
| Input / output references | `input_refs` / `output_refs` when supplied |
| Execution duration | `execution_duration` (seconds) |
| Workflow energy per run | `workflow_energy_per_run` + unit |
| Workflow carbon per run | `workflow_carbon_per_run` + unit |
| Source / asset / resource | optional request fields |
| Provenance records | `cim_payload.provenance_records` (run-matched when notes/inputs contain the run id) |
| Metric definitions | energy / carbon / duration catalogue rows |
| Standards mappings | seeded mappings for workflow energy (and carbon if any) |

## What is future work

- Physical crate layout (`ro-crate-metadata.json` + data files)
- RO-Crate 1.1 / 1.2 validation
- Workflow RO-Crate profile / Process Run Crate specialisation
- Automatic harvest of energy/carbon from stored samples (caller supplies values today)

## API

```text
POST /api/v1/cim-export/rocrate-style
{
  "workflow_id": "wf-204",
  "workflow_run_id": "run-2026-001",
  "energy_per_run": 0.42,
  "carbon_per_run": 0.11,
  "duration_seconds": 3600
}
```
