# Deployment Readiness Checklist

> **Milestone 11** · Gate before promoting registry-driven CIM to staging/production

Use one checklist per environment promotion (e.g. staging, then production).

## Pre-flight

- [ ] **Clean git state** — `git status` clean on the release commit/tag (or only approved release notes)
- [ ] **CI green** — GitHub Actions `pytest` job passed for the commit
- [ ] **Local tests passing** — `pytest -q` (or equivalent) on the release commit
- [ ] **Docs present** — MS1–MS10 development notes + MS10 demo docs + this deployment pack
- [ ] **No unintended architecture changes** — diff reviewed; legacy fallback retained; ingestion behavior unchanged

## Data protection

- [ ] **Database backup completed** — per [POSTGRES_MIGRATION_RUNBOOK.md](POSTGRES_MIGRATION_RUNBOOK.md)
- [ ] **Backup location recorded** — path/URI + timestamp
- [ ] **Rollback path confirmed** — downgrade to `a7708d6bee50` **or** restore-from-backup procedure owned

## Staging

- [ ] **Migration applied to staging** — `alembic upgrade c2f8a1b9e047`
- [ ] **Validation queries passed** — `cim_*` present; legacy tables intact
- [ ] **Seed data loaded** — `python -m cloud_metrics.scripts.seed_cim_registries`
- [ ] **Demo scenario validated** — at least Scenario A + B (+ E recommended)
  ```bash
  python -m cloud_metrics.scripts.run_cim_demo --scenario A
  pytest tests/test_cim_end_to_end_demo.py -q
  ```
- [ ] **Legacy smoke** — existing upload/API path still functions

## Production approval

- [ ] **Production approval recorded** — ticket/CAB/email reference: _______________
- [ ] **Maintenance window** communicated
- [ ] **On-call / rollback owner** named: _______________

## Production execution

- [ ] Backup completed immediately before upgrade
- [ ] `alembic upgrade c2f8a1b9e047`
- [ ] Seed loaded
- [ ] Post-migration validation queries + health checks
- [ ] Watch window complete with no P0/P1 registry defects

## Sign-off

| Role | Name | Date | Signature / ticket |
|------|------|------|--------------------|
| Implementer | | | |
| Reviewer | | | |
| Environment owner | | | |
