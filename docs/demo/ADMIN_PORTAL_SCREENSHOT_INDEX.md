# Milestone 16B — Admin Portal Screenshot Index

Screenshots: `docs/demo/screenshots/ms16b/`. Captured from Google Chrome (Playwright `channel="chrome"`, headed) on 2026-08-13.

| File | What it shows |
|------|----------------|
| `00_api_health.png` | `GET /health` → `{"status":"ok"}` |
| `01_api_docs.png` | FastAPI Swagger (review / KPI / export routes) |
| `10_admin_landing.png` | CIM Admin Portal landing (legacy unknown metrics default) |
| `20_unknown_metrics_legacy.png` | Legacy unknown-key queue from prior workload uploads |
| `20_registry_browser.png` | Metric registry: 35 entries + detail JSON |
| `20_candidate_review.png` | Candidate queue + Approve/Reject/Merge/Promote buttons |
| `20_evidence_readiness.png` | PUE evidence mandatory + missing fulfillment |
| `20_kpi_calculation.png` | KPI calculator form (PUE defaults) |
| `20_provenance_timeline.png` | Provenance list + orchestration detail |
| `31_registry_*_error.png` | Pass-1 BaseWeb select timeouts while cycling registries |
| `32_registry_*.png` | Pass-2 registry browser captures (select automation flaky; metric content dominant) |
| `33_registry_metric_search_pue.png` | Metric search filter attempt |
| `34_registry_metric_status_approved.png` | Status filter attempt |
| `40_candidate_queue.png` | Candidate queue landing |
| `45_extension_queue.png` | Extension filter attempt (pass 1) |
| `46_candidate_queue_pass2.png` | Candidate queue after service demo actions |
| `53_extension_queue_pass2.png` | Extension / metric candidates still listed |
| `55_extension_complete_approve.png` | UI approve blocked: `metric approval requires quantity_kind_id` |
| `56_extension_reject.png` | UI reject success + provenance 316 |
| `60_evidence_readiness.png` | Evidence readiness summary/detail |
| `61_evidence_pue_detail.png` | PUE boundary + reporting_period requirements |
| `70_kpi_form.png` | KPI form before calculate |
| `71_kpi_pue_ok.png` | PUE = 1.5, provenance 307, evidence in payload |
| `72_kpi_pue_invalid_unit.png` | `invalid_unit` when facility unit is `W` |
| `73_kpi_pue_missing_period.png` | `blocked` when aggregation period empty |
| `76_kpi_wue_form.png` | WUE select attempt |
| `77_kpi_cue_form.png` | CUE select attempt |
| `80_provenance_timeline.png` | Timeline with orchestration activities |
| `81_provenance_detail.png` | Single provenance record JSON |
| `82_provenance_cim_mapping.png` | Timeline after review actions |
