# Development Status and Remaining Work

> Updated: Milestone 13 (KPI calculation service)

## Completed (Milestones 1–13)

| Milestone | Focus | Status |
|-----------|-------|--------|
| 1 | Registry skeleton (11 registries) | Approved |
| 2 | SQLAlchemy `Cim*` models + `cim_*` tables | Approved |
| 3 | Initial seed catalogues | Approved |
| 4 | Legacy mapping migration + registry-first lookup | Approved |
| 5 | Unit Registry validation | Approved |
| 6 | Source + Asset resolution | Approved |
| 7 | Registry Orchestrator | Approved |
| 8 | Lifecycle + Standards enrichment | Approved |
| 9 | Rule / Evidence / Provenance / Extension | Approved |
| 10 | End-to-end demonstrator + fixtures + docs | Approved |
| 11 | CI/CD, migration runbook, deployment readiness | Approved |
| 12 | Admin review workflow for candidates / extensions | Approved |
| 13 | KPI calculation (PUE / WUE / CUE) with provenance | Complete (this milestone) |

## What remains manual

- Human review / approval of extension candidates and mapping candidates
- Promoting demo raw→CIM mappings into permanent seed catalogues (if desired)
- **Production** application of `cim_*` migrations (staging/prod runbook is documented — see `docs/deployment/POSTGRES_MIGRATION_RUNBOOK.md`)
- Evidence *fulfillment* tracking (requirements are returned; fulfillment UI not built)
- Streamlit / admin UI surfaces for registry review queues
- Signing the [DEPLOYMENT_READINESS_CHECKLIST.md](../deployment/DEPLOYMENT_READINESS_CHECKLIST.md) for each environment promotion

## What remains candidate / under_review

- Metrics resolved only via legacy fallback (status `candidate`)
- Fuzzy alias hits that should become explicit Mapping Registry rows or be rejected
- Custom research metrics (`workflow_green_score`, etc.)
- Speculative lifecycle links for catalogue metrics not yet seeded with stages

## Known limitations

- Soft validation only on **ingestion** — incompatible units warn but do not hard-block samples
- Reportable KPI calculation **does** hard-block (Milestone 13); not yet wired into the facility demo runner
- Unstructured text is parsed by legacy regex parser; not fully orchestrated
- Demo mappings are session helpers (`origin=demo`), not core seed data
- Some seeded metrics lack lifecycle/evidence links by design (avoid speculative claims)

## Recommended next development phase

1. **Admin UI** over `/api/v1/cim-review` (Streamlit or web) for extension + mapping queues.
2. **Wire KPI service into the facility demo** (Scenario D) without changing operational ingestion.
3. **Evidence fulfillment tracking** — mark mandatory PUE/WUE/CUE evidence complete.
4. **Promote stable demo mappings** into seed after explicit review + `promote_to_seed`.
5. **Registry browser** — evidence readiness, provenance timeline, calculated KPIs.
6. **Deprecate duplicate legacy paths** only after dual-run observability period.

See also: [KPI_CALCULATION_SERVICE.md](KPI_CALCULATION_SERVICE.md), [ADMIN_REVIEW_WORKFLOW.md](ADMIN_REVIEW_WORKFLOW.md).
