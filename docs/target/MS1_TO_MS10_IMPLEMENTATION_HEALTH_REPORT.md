# MS1–MS10 Implementation Health Report

> **Milestone 11** · Stabilization snapshot of the registry-driven CIM

## Verdict

The registry-driven CIM through Milestone 10 is **functionally complete for demonstrator and soft-enrichment ingestion**. Milestone 11 adds CI automation and deployment runbooks; it does not add CIM product features.

## Operational registries (11/11)

| # | Registry | Status |
|---|----------|--------|
| 1 | Metric | Operational (seeded catalogue) |
| 2 | Mapping | Operational (registry-first + legacy fallback) |
| 3 | Unit | Operational (soft validation) |
| 4 | Source | Operational (resolve / candidate) |
| 5 | Asset | Operational (resolve / candidate) |
| 6 | Lifecycle | Operational (seeded links subset) |
| 7 | Standards | Operational (conservative relations) |
| 8 | Rule | Operational (soft evaluation) |
| 9 | Evidence | Operational (KPI / workflow requirements) |
| 10 | Provenance | Operational (orchestrator decision trail) |
| 11 | Extension | Operational (unknown → candidate) |

## Integrated services

- `RegistryOrchestratorService.process(RawMetricContext)` coordinates mapping → unit → source/asset → lifecycle/standards → rules/evidence/provenance/extension.
- `unified_ingestion` can invoke the orchestrator (`use_registry_orchestrator=True`).
- Lower-level `process_metric_sample` remains opt-in for orchestrator use (default preserves legacy callers).
- Milestone 10 demo: `cloud_metrics.scripts.run_cim_demo` + `tests/test_cim_end_to_end_demo.py`.

## Remaining legacy fallback

Still active (intentionally):

1. `metric_mapping.json` / `namespace_mapper.map_raw_to_unified`
2. Legacy `CimMapping` registry service
3. Alias classifier fuzzy matches

Unresolved unknowns can become mapping candidates or extension candidates depending on flags. Scenario E of the demonstrator disables fallback to avoid fuzzy false hits (e.g. `work` inside `workflow_*`).

## Candidate / under_review behavior

- Legacy fallback resolutions are marked **candidate**, not silently approved.
- Extension metrics: `status=candidate`, `review_status=under_review` (or pending/candidate).
- Source/asset missing context may create **candidates**.
- No automatic approved ISO/EN `exactMatch` for unknowns or operational inputs that are only `inputToKPI` / `contextualMatch`.

## Known limitations

- Soft unit/governance validation — does not hard-block ingestion.
- No KPI calculation engine (PUE inputs prepared in demo only).
- Demo raw→CIM mappings are helper rows (`origin=demo`), not permanent seed by default.
- Unstructured parser is legacy regex; not fully orchestrated.
- Admin review UI for candidates not built.
- Evidence requirements returned; fulfillment tracking not built.
- Lint/type strictness not a CI gate (legacy formatting debt).

## Migration readiness

| Check | Result |
|-------|--------|
| Additive `cim_*` revision `c2f8a1b9e047` | Present |
| Upgrade/downgrade covered by tests | `tests/test_cim_registry_migration.py` |
| Legacy tables dropped by MS2 revision | **No** |
| Staging/production procedure | [POSTGRES_MIGRATION_RUNBOOK.md](../deployment/POSTGRES_MIGRATION_RUNBOOK.md) |

## Test / CI posture (Milestone 11)

- GitHub Actions workflow: `.github/workflows/ci.yml` (pytest + migration smoke + e2e demo).
- CI deps: `requirements-ci.txt`.
- Guidance: [CI_CD_VALIDATION.md](../deployment/CI_CD_VALIDATION.md).

## Next recommended phase (post-MS11)

1. Admin review queue for extension + mapping candidates.
2. Optional hard-block policy for incompatible units on reportable KPIs.
3. KPI calculation service (PUE/WUE/CUE) with provenance.
4. Promote stable demo mappings into permanent seed after review.
5. Registry browser / evidence readiness / provenance UI.
6. Dual-run observability period before any legacy-path deprecation.
