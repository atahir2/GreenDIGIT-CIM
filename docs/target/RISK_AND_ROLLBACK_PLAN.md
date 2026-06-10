# Registry-Driven CIM Architecture: Risk & Rollback Plan

This document outlines the risks associated with the registry-driven Common Information Model refactoring, detailed mitigations, rollback protocols, and success metrics.

---

## 1. Risk Matrix

| Risk | Likelihood | Impact | Severity | Mitigation |
|:---|:---:|:---:|:---:|:---|
| **R1: Schema Migration Error** | Medium | Critical | High | Explicit Alembic constraint naming + pre-migration database snapshots. |
| **R2: Mapping Regression** | High | Critical | High | Pre-migration data snapshots, script-driven data migrations, and automated checks. |
| **R3: InfluxDB Data Mismatch** | Low | Medium | Medium | Maintain the exact `gd.*` namespace keys to preserve time-series query parity. |
| **R4: UI Dashboard Breakage** | Medium | Medium | Medium | Keep backward-compatible service API signatures, refactoring endpoints before modifying UI bindings. |
| **R5: Circular Imports** | Medium | Medium | Medium | Use lazy imports and model relationship configurations referencing string table names rather than import hooks. |
| **R6: Query Performance Degradation** | Low | Medium | Low | Index `cim_mappings.source_key` and optimize foreign key joins. |
| **R7: Seed Data Conflicts** | Medium | Medium | Medium | Automated unique key validation and deduplication inside database seed actions. |
| **R8: Coexistence Conflict (Old/New)** | Medium | Medium | Medium | Clear deprecation phase: drop legacy files only after validating tests. |
| **R9: Auto-Learning Degradation** | Low | Medium | Low | Migrate keyword learning logic directly to `CimMapping` auto-learning proposals. |
| **R10: Broken Test Harness** | Medium | Medium | Medium | Port/write isolated mock fixtures using SQLite in-memory databases with StaticPool configurations. |

---

## 2. Detailed Rollback Strategies

### 2.1 Database Schema Rollback
* **Scenario**: Migration failure or corrupted database state after running migrations on production database.
* **Rollback Action**:
  1. Abort the pipeline execution.
  2. Restore the pre-migration database snapshot (e.g. via `pg_restore` or AWS RDS snapshot recovery).
  3. Demote the schema version in Alembic:
     ```bash
     alembic downgrade <previous_revision_id>
     ```

### 2.2 Classification Regression
* **Scenario**: The automated classification pipeline begins returning incorrect, mismatched, or low-confidence namespaces for incoming telemetry metrics.
* **Rollback Action**:
  1. Toggle feature flags (or revert code changes in [ensemble_classifier.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/classifiers/ensemble_classifier.py)) to revert classification logic to use the legacy static alias dictionaries and keyword sets.
  2. Re-verify classifications using regression test suites.

### 2.3 Dashboard Integration Issues
* **Scenario**: Streamlit administrative uploader or admin panel crashes because of changes in model names or parameters.
* **Rollback Action**:
  1. Revert UI scripts (`streamlit_uploader.py` and `admin_panel.py`) to the latest working commit.
  2. Verify endpoint data compatibility through `/api/v1/registry/` routes.

---

## 3. Success Criteria

The refactoring is considered successful only when:
* All 11 registry domains have corresponding SQLAlchemy models, services, and tests.
* **100% Regression Safety**: Verification scripts confirm that all known raw telemetry keys match the exact same unified namespaces as the legacy system.
* **Test Parity**: 21/21 test cases execute and pass successfully.
* **Data Auditing**: Ingestion events successfully trace from inputs to outputs inside the `provenance_records` table.
