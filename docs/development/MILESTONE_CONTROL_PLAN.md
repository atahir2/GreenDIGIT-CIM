# Milestone Control & Execution Plan

This document outlines the governance rules, milestone tracking structure, clean state criteria, and verification procedures required for the registry-driven Common Information Model (CIM) refactoring.

---

## 1. Incremental Milestone Sequence

The refactoring process follows a 14-stage incremental sequence defined in [IMPLEMENTATION_SEQUENCE.md](file:///z:/GreenDIGIT_CIM_testing_v1/docs/target/IMPLEMENTATION_SEQUENCE.md). Stages must be executed sequentially to prevent architectural regressions.

| Stage | Focus Area | Primary Deliverables | Execution Rule |
| :---: | :--- | :--- | :--- |
| **Stage 1** | Audit & Documentation | Audit current code, map missing components, document target design. | Completed |
| **Stage 2** | Registry Folder & Module Structure | Set up directory layout, base interfaces, CRUD schemas, placeholder services. | Completed (formalized as Milestone 1 — see MILESTONE_1_REGISTRY_SKELETON.md) |
| **Stage 3** | Database Models & Migrations | Alembic DDLs for Unit, Source, Asset, Mapping, Provenance, Rules registries. | Completed (formalized as Milestone 2 — see MILESTONE_2_DATABASE_SCHEMA.md; additive `cim_*` tables) |
| **Stage 4** | Mapping Migration | Port legacy JSON/aliases into `cim_metric_mappings` + registry-first lookup with fallback. | Completed (see MILESTONE_4_MAPPING_MIGRATION.md) |
| **Stage 5** | Namespace Generation | Refactor namespace generation to resolve via Metric Registry. | Completed |
| **Stage 6** | Unit Handling | Integrate CIM Unit Registry validation into registry-first mapping lookup. | Completed (see MILESTONE_5_UNIT_REGISTRY.md) |
| **Stage 7** | Ingestion & Candidate Proposals | Create `proposed` / `underReview` mapping entries for unknown metrics. | Completed |
| **Stage 8** | Standards Status & Confidence | Add `relation_type`, `confidence`, and rationale scoring. | Completed |
| **Stage 9** | Lifecycle Stage Linkage | Connect infrastructure assets and metrics to RI lifecycle stages. | Completed (Milestone 8) |
| **Stage 10** | Validation Rules & Evidence | Enforce declarative rules (`rule_registry_service.py`) during ingestion. | Completed (Milestone 9) |
| **Stage 11** | Provenance Logging | Audit data lineage (`provenance_registry_service.py`) across pipeline events. | Completed (Milestone 9) |
| **Stage 12** | Extension Metrics | Route non-standard metrics to extension candidates with proposal flags. | Completed (Milestone 9) |
| **Stage 13** | Registry Test Suite | Maintain unit and integration tests across all registry services. | Completed |
| **Stage 14** | Workflow & Dataset Validation | E2E verification across sample datasets and demo runner. | Completed (Milestone 10 demonstrator) |

**Milestone 11 (Stabilization):** CI workflow (`.github/workflows/ci.yml`), `docs/deployment/*` runbooks, and implementation health report — no new CIM features.

**Milestone 12 (Admin Review):** `AdminReviewService` + CLI/API for candidate/extension/mapping review with provenance and seed-proposal export — ingestion/orchestrator unchanged.

---

## 2. Milestone Entry & Exit Criteria

### 2.1 Entry Criteria (Pre-Milestone Checklist)
Before initiating any milestone execution, the following conditions **must** be met:
1. **Clean Git Working Tree**: `git status` must show no pending uncommitted changes or untracked temporary files.
2. **Baseline Test Pass**: Existing unit tests must pass 100% (`pytest`).
3. **Approved Plan**: The scope of changes for the specific stage must align with [REGISTRY_CIM_REFACTORING_PLAN.md](file:///z:/GreenDIGIT_CIM_testing_v1/docs/target/REGISTRY_CIM_REFACTORING_PLAN.md).

### 2.2 Exit Criteria (Post-Milestone Checklist)
A milestone cannot be declared complete until all of the following conditions are satisfied:
1. **Implementation Complete**: All planned code changes for the milestone are written without breaking legacy features.
2. **Tests Added & Passing**: Corresponding unit/integration tests are added, and `pytest` returns zero failures.
3. **Documentation Updated**: Target architectural documentation (`docs/target/` and `README.md`) reflects newly introduced features or schemas.
4. **Clean Commit Executed**: Changes are committed to Git with a conventional commit message.
5. **Milestone Summary Delivered**: A formal summary report is generated.

---

## 3. Standardized Milestone Summary Template

Every completed milestone must conclude with a structured summary formatted as follows:

```markdown
### Milestone [X] Execution Summary

- **Stage**: Stage [X] - [Stage Title]
- **Status**: Completed / Verified

#### 1. Files Created
- `path/to/new_file_1.py`: Brief description
- `path/to/new_file_2.py`: Brief description

#### 2. Files Modified
- `path/to/modified_file_1.py`: Key changes description
- `path/to/modified_file_2.py`: Key changes description

#### 3. Tests Added
- `tests/test_feature.py::test_case_name`: Coverage goal

#### 4. Test Execution Results
- Total Tests: X
- Passed: X
- Failed: 0
- Command Output: `pytest` output summary

#### 5. Identified Risks & Technical Notes
- Risk item or compatibility consideration

#### 6. Next Recommended Step
- Proceed to Stage [X+1]: [Next Stage Title] as defined in IMPLEMENTATION_SEQUENCE.md
```

---

## 4. Change Control & Backward Compatibility

1. **No System-Wide Sweeps**: Changes must be isolated to the targeted stage. Unrelated modules must not be refactored simultaneously.
2. **Wrapper Pattern**: When replacing legacy services (e.g., `insert_metric_sample.py`), keep the original public functions as thin wrappers pointing to the new registry services.
3. **Schema Preservation**: Database column additions must use `NULL` defaults or server defaults to prevent breaking existing queries.
