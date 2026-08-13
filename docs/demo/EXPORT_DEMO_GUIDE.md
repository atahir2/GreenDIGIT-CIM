# Export Demo Guide

> **Milestone 15** · How to produce interoperability packages from a seeded CIM database

## Prerequisites

1. Schema + seed (same as earlier milestones):

```bash
alembic upgrade head
python -m cloud_metrics.scripts.seed_registries
```

2. Optional: calculate a reportable KPI so provenance and `kpi_results` have something to attach:

```bash
python -m cloud_metrics.scripts.calculate_kpi pue --facility 1200 --it 800 --period monthly --boundary facility --json
```

## CLI examples

```bash
python -m cloud_metrics.scripts.export_cim json --out /tmp/cim_registry.json
python -m cloud_metrics.scripts.export_cim csv metrics --out /tmp/metrics.csv
python -m cloud_metrics.scripts.export_cim csv mappings --out /tmp/mappings.csv
python -m cloud_metrics.scripts.export_cim csv standards --out /tmp/crosswalk.csv
python -m cloud_metrics.scripts.export_cim csv evidence --out /tmp/evidence.csv
python -m cloud_metrics.scripts.export_cim jsonld --namespace cim:energy.efficiency.pue --out /tmp/pue.jsonld
python -m cloud_metrics.scripts.export_cim rocrate --workflow-id wf-204 --run-id run-2026-001 --energy 0.42 --carbon 0.11 --duration 3600 --out /tmp/workflow_crate.json
python -m cloud_metrics.scripts.export_cim dcat --publisher "Example RI" --out /tmp/catalog.json
python -m cloud_metrics.scripts.export_cim evidence --namespace cim:energy.efficiency.pue
python -m cloud_metrics.scripts.export_cim provenance --entity-type kpi_calculation
```

Use `--seed-first` only on an empty local database.

## API examples

With uvicorn running (`uvicorn cloud_metrics.main:app`):

- `GET /api/v1/cim-export/json`
- `GET /api/v1/cim-export/csv/mappings`
- `GET /api/v1/cim-export/jsonld?namespace=cim:energy.efficiency.pue`
- `POST /api/v1/cim-export/rocrate-style` with workflow JSON body
- `GET /api/v1/cim-export/dcat-style`
- `GET /api/v1/cim-export/standards-crosswalk`
- `GET /api/v1/cim-export/evidence-readiness?namespace=cim:energy.efficiency.pue`
- `GET /api/v1/cim-export/provenance`

## What to look for

| Check | Expected |
|-------|----------|
| PUE JSON-LD | `identifier=cim:energy.efficiency.pue`, `unitCode=ratio`, `quantityKind=Ratio`, at least one `exactMatch` |
| Workflow crate | `workflow_energy_per_run`, `workflow_carbon_per_run`, provenance list, `full_standards_compliance: false` |
| Crosswalk CSV | `relation_type` and `review_status` columns |
| Candidate metric | `status=candidate` in JSON / JSON-LD; no borrowed `exactMatch` |
| Partner JSON | Still written by ingestion to `cloud_metrics/data/exports/` — unchanged |

## Honesty labels

JSON-LD, RO-Crate-style, and DCAT-style payloads all set `compliance.full_standards_compliance` to `false`. Do not present them as certified Linked Data, RO-Crate 1.1, or DCAT-AP in papers without additional validation.
