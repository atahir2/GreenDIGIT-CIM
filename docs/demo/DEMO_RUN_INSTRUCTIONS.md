# Demo Run Instructions

## Prerequisites

- Project virtualenv with dependencies installed
- CIM tables available via Alembic migration `c2f8a1b9e047` (in-memory for default demo)
- Seed catalogues loaded by `seed_all` (automatic in demo CLI)

## Run all scenarios (in-memory SQLite)

```bash
python -m cloud_metrics.scripts.run_cim_demo
```

## Single scenario

```bash
python -m cloud_metrics.scripts.run_cim_demo --scenario A
python -m cloud_metrics.scripts.run_cim_demo --scenario B
python -m cloud_metrics.scripts.run_cim_demo --scenario C
python -m cloud_metrics.scripts.run_cim_demo --scenario D
python -m cloud_metrics.scripts.run_cim_demo --scenario E
```

## JSON output

```bash
python -m cloud_metrics.scripts.run_cim_demo --json
python -m cloud_metrics.scripts.run_cim_demo --scenario A --json
```

## Use configured application database

```bash
python -m cloud_metrics.scripts.run_cim_demo --use-db
```

Requires `cim_*` tables migrated and writable. Still idempotent for demo mappings.

## Tests

```bash
pytest tests/test_cim_end_to_end_demo.py -q
pytest tests/ -q
```

## What success looks like

- Scenario A: `node_power_watts` → `cim:compute.node.power.draw`, unit `valid`, source/asset resolved or candidate, lifecycle includes operation/optimisation, provenance id set.
- Scenario B: mapping may succeed; `unit_validation_status=incompatible`; warnings present; not treated as valid.
- Scenario C: `workflow_energy_per_run` mapped; reproducibility lifecycle; PROV-O/RO-Crate evidence; no ISO/EN exactMatch.
- Scenario D: facility metrics mapped; prepared PUE 1.5; PUE evidence for ISO/IEC 30134.
- Scenario E: unresolved + extension candidate (`under_review` / `candidate`); no approved standards auto-attached.
