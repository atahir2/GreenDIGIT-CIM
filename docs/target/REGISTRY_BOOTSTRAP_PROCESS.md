# Registry Bootstrap Process

> **Milestone 3** · How to load the initial ``cim_*`` seed set

---

## Prerequisites

1. Milestone 2 migration applied (revision `c2f8a1b9e047`) so all `cim_*` tables exist.
2. Application `DATABASE_URL` configured in `.env`.
3. Do **not** point tests at production — tests use isolated SQLite.

---

## Apply schema (if needed)

```bash
alembic upgrade c2f8a1b9e047
```

---

## Run the seed

```bash
python -m cloud_metrics.scripts.seed_cim_registries
# or JSON report:
python -m cloud_metrics.scripts.seed_cim_registries --json
```

Programmatic:

```python
from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.registry.seed import seed_all

with SessionLocal() as session:
    report = seed_all(session)  # commits by default
    print(report.as_dict())
```

---

## Idempotency

Natural keys used for get-or-create:

| Entity | Key |
|--------|-----|
| Quantity kind | `name` |
| Unit | `symbol` |
| Metric | `namespace` |
| Lifecycle stage | `stage_key` |
| Standard | `code` (+ `standard_version`) |
| Source | `(name, type)` |
| Lifecycle link | `(metric_id, lifecycle_stage_id)` |
| Standards mapping | `(source_key, source_id)` |
| Validation rule | `name` |
| Evidence requirement | `(standard_id, metric_id, evidence_type)` |
| Provenance marker | `(entity_type, activity, agent, method)` |

Re-running the seed must not raise uniqueness errors or double row counts.

---

## Verification

```bash
pytest tests/test_cim_registry_seed.py -q
pytest tests/ -q
```

---

## Safety boundaries

* Does not call ingestion (`process_metric_sample`, unified ingestion, etc.).
* Does not modify legacy `metric_definitions` / `cim_mappings` / JSON maps.
* Does not change namespace generation.
* Legacy script `seed_registries.py` (Antigravity, non-`cim_*`) remains separate and unused by this bootstrap.
