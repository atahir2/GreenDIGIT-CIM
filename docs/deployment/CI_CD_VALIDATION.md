# CI/CD Validation

> **Milestone 11** · Automated test execution for the registry-driven CIM

## Workflow

| Item | Value |
|------|-------|
| File | `.github/workflows/ci.yml` |
| Triggers | `push` and `pull_request` on `master` / `main` |
| Runner | `ubuntu-latest` |
| Python | 3.11 |
| Dependencies | `requirements-ci.txt` (CI-trimmed; see below) |

## What runs automatically

1. **Install** — `pip install -r requirements-ci.txt`
2. **Full pytest** — `pytest --maxfail=1 --disable-warnings -q`  
   Covers registry, migration, orchestrator, governance, demo, and legacy tests under `tests/`.
3. **Migration smoke** — `tests/test_cim_registry_migration.py`  
   Confirms additive `cim_*` upgrade/downgrade (revision `c2f8a1b9e047`).
4. **E2E demo** — `tests/test_cim_end_to_end_demo.py`  
   Confirms Milestone 10 scenarios A–E.

## Environment variables in CI

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Required at import by `cloud_metrics.utils.config` (SQLite file in CI) |
| `CORS_ORIGINS` | Harmless default for settings load |
| `TRANSFORMERS_OFFLINE` / `HF_HUB_OFFLINE` | Prevent embedding model downloads |

Registry and migration tests create **isolated in-memory SQLite** sessions and do not use the CI `DATABASE_URL` for `cim_*` schema work.

## What does **not** run as a required gate

- `flake8`, `black --check`, `mypy` — listed under optional `dev` deps in `pyproject.toml`, but the legacy tree is not fully lint-clean. Do **not** treat local formatting debt as a CIM regression.
- Poetry — the previous CI used Poetry without a lockfile; Milestone 11 uses pip for reliability.
- Live PostgreSQL — production DB migration is a manual/staging runbook step ([POSTGRES_MIGRATION_RUNBOOK.md](POSTGRES_MIGRATION_RUNBOOK.md)).
- Streamlit UI / live Influx — out of CI scope.

## `requirements-ci.txt` vs `requirements.txt`

| Package | Full (`requirements.txt`) | CI |
|---------|---------------------------|-----|
| Core app + pytest + alembic | yes | yes |
| `sentence-transformers` | yes | **omitted** (optional classifier path) |
| `httpx` / `uvicorn` | often present via env | **explicit** (FastAPI TestClient) |
| `psycopg2-binary` | typically local | listed for Postgres parity |

## How to handle CI failure

1. Open the failed GitHub Actions job log; note the first failing test.
2. Reproduce locally:
   ```bash
   export DATABASE_URL=sqlite:///./ci_pytest.db   # Windows: set DATABASE_URL=...
   pip install -r requirements-ci.txt
   pytest --maxfail=1 -q
   ```
3. Classify the failure:
   - **Registry / orchestrator / demo** — fix under `cloud_metrics/registry/` or demo helpers; do not remove legacy fallback.
   - **Migration** — fix only additive `cim_*` migration issues; never drop legacy tables.
   - **Legacy tests** — preserve backward compatibility; prefer adapters over rewrites.
4. Re-run the full suite before pushing.
5. Do **not** merge with a red `pytest` job. Do not skip CI with empty commits or `--no-verify` for merge.

## Local parity commands

```bash
pytest -q
pytest tests/test_cim_registry_migration.py -q
pytest tests/test_cim_end_to_end_demo.py -q
python -m cloud_metrics.scripts.run_cim_demo --scenario A
```
