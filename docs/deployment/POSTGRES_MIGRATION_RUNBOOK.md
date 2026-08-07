# PostgreSQL Migration Runbook — CIM Registry Tables

> **Milestone 11** · Staging/production guidance for Alembic revision `c2f8a1b9e047`

This runbook applies the **additive** `cim_*` registry schema. It does **not** drop legacy / Antigravity tables.

## Revision summary

| Item | Value |
|------|-------|
| Revision | `c2f8a1b9e047` |
| Revises | `a7708d6bee50` |
| File | `migrations/versions/c2f8a1b9e047_add_cim_registry_tables.py` |
| Behavior | Creates `cim_*` tables only |
| Downgrade | Drops `cim_*` tables created by this revision; legacy tables untouched |

### Tables created (additive)

`cim_quantity_kinds`, `cim_units`, `cim_sources`, `cim_assets`, `cim_standards`, `cim_standard_terms`, `cim_metric_definitions`, `cim_metric_mappings`, `cim_lifecycle_stages`, `cim_metric_lifecycle_links`, `cim_validation_rules`, `cim_evidence_requirements`, `cim_provenance_records`, `cim_extension_metrics`

## Assumptions

1. Prior Alembic head on the target DB is `a7708d6bee50` (or an ancestor that can reach it).
2. Application code that *writes* to `cim_*` is deployed only after upgrade (or is soft-fail safe).
3. Operators have Postgres privileges to `CREATE TABLE` / indexes in the target schema.
4. `DATABASE_URL` uses a SQLAlchemy URL with a Postgres driver, e.g. `postgresql+psycopg2://USER:PASS@HOST:PORT/DBNAME`.
5. Seed catalogues are loaded separately via `python -m cloud_metrics.scripts.seed_cim_registries` (idempotent).

## Prerequisite checks

```bash
# 1) Working tree / release tag known
git status
git rev-parse HEAD

# 2) Tests green on the release commit
pytest -q

# 3) Env loaded
echo "$DATABASE_URL"   # must be set; do not print secrets in shared logs

# 4) Alembic can see the DB
alembic current
alembic history | head

# 5) Confirm expected parent revision present (staging)
# Expected: a7708d6bee50 (or already at c2f8a1b9e047 if re-run)
```

## Environment variables

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABASE_URL` | yes | Postgres SQLAlchemy URL |
| `MAPPING_JSON_PATH` / `METRIC_MAPPING_JSON_PATH` | optional | Mapping file location |
| Influx vars | optional | Not required for `cim_*` DDL |

Driver: install `psycopg2-binary` (or equivalent) in the migration environment.

## Backup (placeholder — replace with site policy)

```bash
# EXAMPLE ONLY — adapt host/user/db to your environment
pg_dump --format=custom --file="backup_pre_cim_${TIMESTAMP}.dump" "$PGDATABASE"
# or:
# pg_dump "$DATABASE_URL_PLAIN" > "backup_pre_cim_${TIMESTAMP}.sql"
```

Store the backup in the approved durable location before staging or production upgrade.

## Staging migration steps

1. Announce maintenance window (if staging shared).
2. Take backup (above).
3. Deploy the release commit that contains `c2f8a1b9e047`.
4. Run upgrade:
   ```bash
   alembic upgrade c2f8a1b9e047
   # or: alembic upgrade head
   ```
5. Seed registries (idempotent):
   ```bash
   python -m cloud_metrics.scripts.seed_cim_registries
   ```
6. Run validation queries (next section).
7. Run demo smoke:
   ```bash
   python -m cloud_metrics.scripts.run_cim_demo --scenario A --use-db
   # or offline: python -m cloud_metrics.scripts.run_cim_demo --scenario A
   pytest tests/test_cim_end_to_end_demo.py -q
   ```

## Validation queries

```sql
-- Alembic version
SELECT version_num FROM alembic_version;

-- Additive tables exist
SELECT tablename FROM pg_tables
WHERE schemaname = 'public' AND tablename LIKE 'cim_%'
ORDER BY 1;

-- Legacy tables still present (examples — adjust to your inventory)
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('metric_definitions', 'cim_mappings', 'units', 'sources')
ORDER BY 1;

-- Seed sanity (after seed_cim_registries)
SELECT COUNT(*) AS metrics FROM cim_metric_definitions;
SELECT COUNT(*) AS units FROM cim_units;
SELECT COUNT(*) AS lifecycle_stages FROM cim_lifecycle_stages;
```

Expect: `alembic_version` = `c2f8a1b9e047`; fourteen `cim_*` tables; legacy tables **not** removed.

## Rollback strategy (non-production / staged)

```bash
# Rolls back ONLY the Milestone 2 cim_* revision
alembic downgrade a7708d6bee50
```

Effects:

- Drops `cim_*` tables created by `c2f8a1b9e047`.
- Does **not** drop legacy tables.
- Destroys seed / orchestrator data stored in `cim_*` (re-seed after re-upgrade).

**Production rollback:** prefer restore-from-backup if `cim_*` already contains irreplaceable operational provenance/extension rows. Downgrade is acceptable only when `cim_*` data loss is approved.

## Production migration checklist

- [ ] Change ticket / CAB approval recorded
- [ ] Backup completed and restore tested (or restore procedure verified)
- [ ] Staging migrated and validated successfully on the **same** commit
- [ ] `alembic upgrade c2f8a1b9e047` executed
- [ ] Seed loaded
- [ ] Validation queries passed
- [ ] Application health checks passed
- [ ] Demo / smoke scenarios passed
- [ ] Rollback owner and procedure named
- [ ] Monitoring watch window agreed

## Post-migration validation

1. `alembic current` → `c2f8a1b9e047`
2. SQL counts for seeded metrics/units > 0
3. API / Streamlit still serve legacy paths
4. Registry orchestrator path: known metric maps; wrong unit flagged; unknown → extension candidate (see Milestone 10 demo)
5. Confirm no unexpected table drops in Postgres logs

## Related docs

- [DATABASE_MIGRATION_PLAN.md](../target/DATABASE_MIGRATION_PLAN.md)
- [DEPLOYMENT_READINESS_CHECKLIST.md](DEPLOYMENT_READINESS_CHECKLIST.md)
- [CI_CD_VALIDATION.md](CI_CD_VALIDATION.md)
