# Mapping Registry Migration

> **Milestone 4** · Migrate / synchronize legacy mappings into Metric & Mapping Registries

---

## Objective

Read existing raw→unified mapping definitions from file and hardcoded sources,
create or link rows in:

* ``cim_metric_definitions`` (Metric Registry)
* ``cim_metric_mappings`` (Mapping Registry)

…while preserving legacy files and runtime behaviour.

---

## Utility

| Artefact | Path |
|----------|------|
| Discovery | `cloud_metrics/registry/migration/legacy_sources.py` |
| ``gd.*`` → ``cim:*`` | `cloud_metrics/registry/migration/gd_to_cim.py` |
| Sync / upsert | `cloud_metrics/registry/migration/sync.py` → `migrate_legacy_mappings()` |
| CLI | `cloud_metrics/scripts/migrate_legacy_mappings.py` |

### CLI

```bash
# Discover only
python -m cloud_metrics.scripts.migrate_legacy_mappings --dry-run -v

# Seed approved metrics (Milestone 3) then migrate
python -m cloud_metrics.scripts.migrate_legacy_mappings --seed-first -v
```

### Programmatic

```python
from cloud_metrics.registry.migration import migrate_legacy_mappings
from cloud_metrics.registry.seed import seed_all
from cloud_metrics.utils.config import SessionLocal

with SessionLocal() as session:
    seed_all(session, commit=True)
    report = migrate_legacy_mappings(session, commit=True)
    print(report.as_dict())
```

---

## Per-mapping fields preserved

| Legacy field | Stored as |
|--------------|-----------|
| Raw source metric name | `cim_metric_mappings.source_key` |
| Source system / type | `notes` + `origin="migrated"`; optional `source_id` later |
| Existing unified namespace | Rationale text + `legacy` → `cim:*` via `gd_to_cim` |
| Category / subcategory | On linked / candidate `CimMetricDefinition` |
| Unit | Not always available in legacy sources; left null unless present |
| Description | Candidate metric `description` / mapping `notes` |
| Mapping confidence | `confidence_score` |
| Mapping status | `status` + `review_status` |
| Notes / assumptions | `notes`, `rationale` |

---

## Link vs candidate policy

1. **Trusted alignment** (`GD_TO_CIM`) and an **approved** metric already exists  
   → link mapping; set `status=approved`, `review_status=approved`.

2. **Namespace missing** or **untrusted** ``gd.*`` key  
   → create `CimMetricDefinition` with `status=candidate`,
   `review_status=under_review`; mapping stays `candidate` / `under_review`.

3. **Never** silently mark uncertain metrics as approved.

See [CANDIDATE_MAPPING_POLICY.md](./CANDIDATE_MAPPING_POLICY.md).

---

## Idempotency

Re-running migration:

* Skips existing `(source_key, source_id IS NULL)` rows → ``duplicate mapping skipped`` log
* Does not create duplicate metric namespaces
* Safe after Milestone 3 `seed_all()` (standards mappings use distinct `std:…` keys)

---

## What is intentionally not done

* Deleting / renaming `metric_mapping.json`, `ALIASES`, or `CimMapping`
* Rewiring ingestion / ensemble classifier to registry-only
* Unit validation, source/asset resolution, lifecycle, standards enrichment beyond linking
* Provenance / evidence logic

Those belong to later milestones.
