# CIM Demonstrator Narrative

> Research packaging · Milestone 15

## Story

A research infrastructure collects node power, GPU power, workflow energy, and facility energy/water/carbon. The CIM demonstrator shows how those observations become **governed information objects**: named, unit-checked, optionally standards-aligned, evidence-aware, and exportable.

## Scenarios (Milestone 10)

| Scenario | Input | Outcome |
|----------|-------|---------|
| A Known metrics | Prometheus-style node/GPU/CPU samples | Resolve to `cim:*` namespaces, valid units, lifecycle/standards enrichment |
| B Wrong unit | Power given in an incompatible unit | Soft warning on ingestion; mapping still resolves |
| C Workflow reproducibility | `workflow_energy_per_run` + workflow/run ids | `cim:workflow.energy.per_run`; PROV-O/RO-Crate **contextual** mappings; evidence requirements declared |
| D Facility KPI prep | Facility vs IT energy | PUE namespace + evidence; numeric PUE via Milestone 13 calculator (hard-block if incomplete) |
| E Unknown metric | Unrecognised raw key | Extension candidate, not approved, no borrowed exactMatch |

## Governance path (Milestones 12–14)

Reviewers inspect candidates in the admin portal, record provenance, inspect evidence readiness, and calculate PUE/WUE/CUE without writing `cim_*` rows from the UI.

## Dissemination path (Milestone 15)

The same registry state can be exported as:

- JSON / CSV for analysts
- Partial JSON-LD for linked-data experiments
- RO-Crate-style JSON for a workflow run
- DCAT-style catalogue metadata for dataset landing pages
- Standards crosswalk, evidence readiness, and provenance extracts for papers and audits

Partner `gd.*` JSON from ingestion remains available for existing downstream tools.

## How to replay

See `docs/demo/END_TO_END_CIM_DEMONSTRATOR.md` and `docs/demo/EXPORT_DEMO_GUIDE.md`.
