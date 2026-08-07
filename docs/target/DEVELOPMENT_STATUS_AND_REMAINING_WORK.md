# Development Status and Remaining Work

> Updated: Milestone 11 (stabilization / CI/CD)

## Completed (Milestones 1–11)

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
| 11 | CI/CD, migration runbook, deployment readiness | Complete (this milestone) |

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

- Soft validation only — incompatible units warn but do not hard-block ingestion
- No KPI calculation engine (PUE/WUE/CUE computed values not derived in-pipeline)
- Unstructured text is parsed by legacy regex parser; not fully orchestrated
- Demo mappings are session helpers (`origin=demo`), not core seed data
- Some seeded metrics lack lifecycle/evidence links by design (avoid speculative claims)

## Recommended next development phase

1. **Admin review queue** for extension + mapping candidates (approve / reject / promote).
2. **Hardening policy toggle** — optional hard-block on incompatible units for reportable KPIs.
3. **KPI calculation service** — PUE/WUE/CUE from prepared facility inputs with provenance.
4. **Promote stable demo mappings** into seed / migration sync once reviewed.
5. **UI dashboards** — registry browser, evidence readiness, provenance timeline.
6. **Deprecate duplicate legacy paths** only after dual-run observability period (do not remove yet).

See also: [MS1_TO_MS10_IMPLEMENTATION_HEALTH_REPORT.md](MS1_TO_MS10_IMPLEMENTATION_HEALTH_REPORT.md), [CI_CD_VALIDATION.md](../deployment/CI_CD_VALIDATION.md).
