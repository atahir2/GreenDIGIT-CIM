# Development Status and Remaining Work

> Updated: Milestone 16C (API-based external organization / RI integration)

## Completed (Milestones 1–16C)

| Milestone | Focus | Status |
|-----------|-------|--------|
| 1–15 | Registry-driven CIM through export | Approved |
| 16A | Browser workload validation | Completed / documented |
| 16B | Admin Portal browser validation | Planned / partial prior screenshots |
| 16C | API ingest for external orgs/RIs | Complete (this milestone) |

## Milestone 16C deliverables

| Artifact | Path |
|----------|------|
| Ingest service | `cloud_metrics/services/cim_api_ingest.py` |
| API router | `cloud_metrics/api/cim_ingest_api.py` |
| Tests | `tests/test_cim_api_ingest.py` |
| Docs | `docs/api/*` |

Endpoints:

- `POST /api/v1/cim-ingest/metrics`
- `POST /api/v1/cim-ingest/scenarios/{A-E}`

## What remains manual

- Human review / approval of extension candidates and mapping candidates
- Promoting demo raw→CIM mappings into permanent seed catalogues (if desired)
- **Production** application of `cim_*` migrations (staging/prod runbook is documented — see `docs/deployment/POSTGRES_MIGRATION_RUNBOOK.md`)
- Evidence *fulfillment* tracking (requirements are exported; fulfillment is not persisted unless supplied at export time)
- Full RO-Crate 1.1 crate directories, DCAT-AP validation, RDF/Turtle
- Admin portal download tab for exports (CLI/API exist)
- Signing the [DEPLOYMENT_READINESS_CHECKLIST.md](../deployment/DEPLOYMENT_READINESS_CHECKLIST.md) for each environment promotion
- Production API authentication / multi-tenant enforcement (see `docs/api/API_SECURITY_AND_AUTH_NOTES.md`)

## What remains candidate / under_review

- Metrics resolved only via legacy fallback (status `candidate`)
- Fuzzy alias hits that should become explicit Mapping Registry rows or be rejected
- Custom research metrics (`workflow_green_score`, etc.)
- Speculative lifecycle links for catalogue metrics not yet seeded with stages

## Known limitations

- Soft validation only on **ingestion** — incompatible units warn but do not hard-block samples
- Reportable KPI calculation **does** hard-block (Milestone 13); API ingest can optionally call it via `options.calculate_kpi`
- Unstructured text is parsed by legacy regex parser; not fully orchestrated
- Demo mappings are session helpers (`origin=demo`), not core seed data
- Some seeded metrics lack lifecycle/evidence links by design (avoid speculative claims)
- Legacy `/metrics/aws` and `/metrics/gcp` remain non-orchestrated GET triggers
- No production auth on FastAPI

## Recommended next development phase (consolidation)

1. **Final consolidation docs** — single operator runbook tying browser, admin, API, and export.
2. **Production auth** for `/api/v1/cim-ingest` and `/api/v1/cim-review`.
3. **Evidence fulfillment store** and mark-complete UI for mandatory PUE/WUE/CUE evidence.
4. **Wire KPI service into facility demo** paths consistently (UI + API already available).
5. **Promote stable demo mappings** into seed after explicit review + `promote_to_seed`.
6. **Deprecate duplicate legacy paths** only after dual-run observability period.

See also: [docs/api/CIM_API_INTEGRATION_GUIDE.md](../api/CIM_API_INTEGRATION_GUIDE.md), [EXPORT_LAYER.md](EXPORT_LAYER.md), [KPI_CALCULATION_SERVICE.md](KPI_CALCULATION_SERVICE.md).
