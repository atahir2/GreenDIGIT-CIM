# Refactoring Implementation Guardrails & Safety Policies

This document establishes the mandatory safety policies, command restrictions, backward compatibility rules, and quality control guardrails governing all modifications to the Common Information Model (CIM) codebase.

---

## 1. Prohibited & Restricted Commands Policy

To protect project history, database integrity, and uncommitted context, strict boundaries are enforced regarding command execution:

### 1.1 Strictly Prohibited Commands (Without Prior Explicit User Approval)
The following commands **must never be executed** autonomously by any agent:

* ❌ `git reset --hard` (destroys working tree changes)
* ❌ `git clean -fd` (removes untracked files without review)
* ❌ `git push --force` or `git push -f` (overwrites remote repository history)
* ❌ `git rebase` on public/shared branches
* ❌ `DROP DATABASE` or `DROP TABLE` SQL statements outside of verified Alembic downgrade scripts
* ❌ Deletion of existing test suites or test assertions to pass a broken build

### 1.2 Required Pre-Execution Verifications
* Before running database migration commands (`alembic upgrade` / `alembic downgrade`), confirm database connection parameters in `.env`.
* Before pushing commits to GitHub, verify that local unit tests pass 100%.

---

## 2. Preservation of Existing Functionality & Backward Compatibility

### 2.1 The Non-Disruption Mandate
Refactoring must introduce new architecture **incrementally and transparently**. Existing external clients, UI dashboards, and ingestion scripts must continue operating without breaking changes.

### 2.2 Backward Compatibility Rules
1. **API Signatures**: If an existing function signature (e.g. `process_metric_sample()`) is updated, new parameters must provide default values (e.g., `captured_at=None`, `ri_id=None`).
2. **Schema Evolution**: Column removals or table drops (such as legacy `metric_keywords` or `metric_source_map`) may only occur after replacement tables (`cim_mappings`) are fully populated and tested.
3. **Database Fallbacks**: Model imports for legacy tables should include graceful `try...except ImportError` handles to prevent script crashes on cleaned schemas.

---

## 3. Data & Testing Isolation Guardrails

### 3.1 Test Suite Isolation
* All unit and integration tests must run against an **isolated in-memory SQLite database** (`sqlite:///:memory:`).
* Tests must never execute against the live PostgreSQL production/development database.
* SQLite connections in tests must be configured with `StaticPool` and `connect_args={"check_same_thread": False}` to guarantee multi-thread safety during Starlette `TestClient` API testing.

### 3.2 Alembic Migration Safety
* All foreign keys and constraints created in Alembic migrations must be **explicitly named** (e.g., `fk_metric_definitions_canonical_unit_id_units`).
* Migrations modifying existing tables must support SQLite batch mode (`render_as_batch=True`) for local test compatibility.

---

## 4. Multi-Agent Change Control & Scope Boundaries

1. **Strict File Scoping**: Each milestone must modify only the files required for its specific stage. Sweeping refactors across unrelated directories are prohibited.
2. **Code Codebase vs. Documentation Codebase**:
   * Implementation code modifications (`cloud_metrics/`, `migrations/`, `tests/`) are driven by milestone goals.
   * Development control docs (`docs/development/`) and architectural docs (`docs/target/`) serve as authoritative specifications.
3. **Audit Readiness**: Every code change must be verifiable via unit tests (`pytest`) and reproducible via documented command sequences.
