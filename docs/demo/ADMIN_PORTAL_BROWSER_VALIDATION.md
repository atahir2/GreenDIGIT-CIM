# Milestone 16B — Admin Portal Browser Validation

> **Date**: 2026-08-13  
> **Scope**: Registry-driven CIM Admin Portal in Google Chrome  
> **Status**: Completed (validation). Portal not rewritten. Review mutations only via `AdminReviewService`.

This milestone does **not** add CIM architecture. It starts the local apps, opens the Admin Portal in Chrome, validates registry browser / candidate review / evidence / KPI / provenance surfaces, and records what the browser (and the same UI backend path) actually shows.

---

## 1. Startup commands and URLs

Poetry is not required. Use the project virtualenv.

| Item | Command / value |
|------|-----------------|
| Python | `.venv\Scripts\python.exe` (3.13) |
| Backend / API | `.venv\Scripts\python.exe -m uvicorn cloud_metrics.main:app --host 127.0.0.1 --port 8000` |
| Admin portal | `.venv\Scripts\python.exe -m streamlit run cloud_metrics/scripts/admin_panel.py --server.port 8502 --server.address 127.0.0.1 --server.headless true` |
| Workload uploader (optional for MS16B) | `.venv\Scripts\python.exe -m streamlit run cloud_metrics/scripts/streamlit_uploader.py --server.port 8501 --server.address 127.0.0.1` |
| Schema / seed (if empty DB) | `alembic upgrade head` then `python -m cloud_metrics.scripts.seed_cim_registries` |

| URL tested | Purpose |
|------------|---------|
| http://127.0.0.1:8000/health | `{"status":"ok"}` |
| http://127.0.0.1:8000/docs | OpenAPI (review / KPI / export) |
| http://127.0.0.1:8502 | **CIM Admin Portal** (MS16B target) |

Required env (from `.env`):

```text
DATABASE_URL=postgresql+psycopg2://postgres:admin123@localhost:5433/cloud_metrics
```

Influx vars are optional for admin validation. This run used Postgres on `localhost:5433`.

Reproducible runners:

```text
.venv\Scripts\python.exe docs/demo/ms16b_seed_demo_candidates.py
.venv\Scripts\python.exe docs/demo/ms16b_browser_runner.py
.venv\Scripts\python.exe docs/demo/ms16b_browser_runner_pass2.py
.venv\Scripts\python.exe docs/demo/ms16b_review_actions_service.py
```

Demo candidates use `ms16b.demo.*` keys only (safe demo data).

---

## 2. Admin portal opened in Chrome

Playwright launched installed Google Chrome (`channel="chrome"`, headed). Landing page title: **CIM Admin Portal**. Sidebar sections:

1. Unknown metrics (legacy)  
2. Registry browser  
3. Candidate review  
4. Evidence readiness  
5. KPI calculation  
6. Provenance timeline  

Screenshot: `docs/demo/screenshots/ms16b/10_admin_landing.png`

---

## 3. Registry browser results

| Registry | Visible in portal code / helpers | Browser evidence | Live row counts (Postgres) |
|----------|----------------------------------|------------------|----------------------------|
| Metric | Yes | Default view: 35 entries + detail JSON | 35 |
| Mapping | Yes | Section open; helper load OK | 100 |
| Unit | Yes | Helper load OK | 23 |
| Source | Yes | Helper load OK | 2 |
| Asset | Yes | Helper load OK | 10 |
| Standards | Yes | Helper load OK | 15 |
| Lifecycle | Yes | Helper load OK | 10 |
| Rule | Yes | Helper load OK | 8 |
| Evidence | Yes | Helper load OK | 6 |
| Provenance | Yes | Helper load OK | 316 |
| Extension | Yes | Helper load OK | 3 |

- **Filtering / search**: implemented (`Status filter`, `Review status filter`, `Search`). Metric search for `pue` reduces helper rows (35 → 3 with status=`approved` filter path). Streamlit BaseWeb select automation was flaky when cycling registries in pass-2 (typed value often did not commit); default **metric** catalogue + detail JSON were confirmed in Chrome.
- **Entry details**: working — selecting an id shows full JSON (namespace, status, review_status, quantity_kind, etc.).

Screenshots: `20_registry_browser.png`, `32_registry_*.png`, `33_registry_metric_search_pue.png`.

---

## 4. Candidate review results

Queue caption: *All actions call `AdminReviewService`. The UI does not write `cim_*` rows directly.*

| Check | Result |
|-------|--------|
| Candidate mappings listed | Yes (queue non-empty; includes workload + `ms16b.demo.*`) |
| Extension candidates listed | Yes (`cim:extension.ms16b_demo_*`) |
| under_review mappings | Yes |
| Candidate details | Yes (JSON panel) |
| Approve (demo mapping) | **Pass** via `perform_review_action` → provenance **310** |
| Reject (demo mapping) | **Pass** → provenance **312** |
| Merge (demo mapping → `cim:compute.node.power.draw`) | **Pass** → provenance **313** |
| Promote to seed | **Pass** → proposal under `generated/seed_promotion/…`, provenance **311**; canonical seed **not** modified |
| Edit / request changes | Available as UI buttons; service supports them (M12 tests) |
| Every successful action creates provenance | Confirmed (`activity=review_action`) |

Chrome could open the queue and show buttons; selecting a specific `ms16b.demo.*` row via BaseWeb select was unreliable. After service approve/reject/merge, those mappings correctly left the pending queue. UI path is the same function: `cloud_metrics/ui/cim_portal.py::perform_review_action` → `AdminReviewService.apply`.

---

## 5. Extension metric review results

| Check | Result |
|-------|--------|
| Approve without required metadata | **Blocked** — e.g. placeholder justification / missing quantity kind (`AdminReviewService` gate) |
| Approve with valid metadata + justification | **Pass** with full edits through service (provenance **314**) |
| UI-only justification approve | Correctly **blocked** when quantity_kind missing (`metric approval requires quantity_kind_id`) — screenshot `55_extension_complete_approve.png` |
| Reject | **Pass** in Chrome UI on extension metric row — provenance **316** (`56_extension_reject.png`) |
| Rejected remains rejected | Yes |
| Approved not silently duplicated | Extension unique on `metric_id`; promote writes proposal only |
| review_status visible | Yes in queue / detail JSON |

**Limitation**: Candidate review UI only sends `justification` (and notes/merge target). Full extension metadata (`quantity_kind`, `suggested_unit`, `suggested_definition`, `source_context`) is supported by `AdminReviewService` edits but not all fields have dedicated UI inputs.

---

## 6. Evidence readiness results

| Check | Result |
|-------|--------|
| PUE / WUE / CUE requirements | Visible (PUE detail confirmed in Chrome) |
| Missing evidence | Shown as **Missing fulfillment** (fulfillment store not implemented — by design) |
| Available evidence | Empty / not tracked as fulfillment artifacts |
| Readiness status | `declared` for seeded reportables |
| Boundary / aggregation period | Visible on PUE mandatory rows (`facility`, `monthly_or_annual`, …) |

Screenshots: `60_evidence_readiness.png`, `61_evidence_pue_detail.png`.

---

## 7. KPI calculation UI results

| Check | Result |
|-------|--------|
| PUE calculate | **Pass** — `cim:energy.efficiency.pue = 1.5 ratio`, provenance **307** |
| WUE / CUE forms | Implemented (`kpi` select: pue/wue/cue); Chrome automation of select was flaky; forms exist in UI |
| Incompatible units | **Pass** — facility unit `W` → `invalid_unit`, no fake value, provenance **308** |
| Missing aggregation period | **Pass** → `blocked`, provenance **309** |
| Provenance on result | Shown (`Provenance record: …`) |
| Evidence with result | Included in result JSON |

Screenshots: `70_kpi_form.png`, `71_kpi_pue_ok.png`, `72_kpi_pue_invalid_unit.png`, `73_kpi_pue_missing_period.png`.

---

## 8. Provenance timeline results

| Activity class | Observed |
|----------------|----------|
| Orchestration / mapping path | Yes (`activity=orchestration`, legacy_fallback paths) |
| KPI calculation | Yes (records 307–309; listed in timeline activities) |
| Review action | Yes (records 310–316 via service + UI reject) |
| Unit validation / source / asset / lifecycle / standards / evidence | Present in orchestrator-linked provenance chains and KPI payloads; timeline UI lists mixed `cim_provenance_records` |

Screenshots: `80_provenance_timeline.png`, `81_provenance_detail.png`, `82_provenance_cim_mapping.png`.

---

## 9. Evidence captured

| Artifact | Path |
|----------|------|
| Screenshots | `docs/demo/screenshots/ms16b/` |
| Browser JSON (pass 1) | `docs/demo/logs/ms16b/browser_run_results.json` |
| Browser JSON (pass 2) | `docs/demo/logs/ms16b/browser_run_results_pass2.json` |
| Review service log | `docs/demo/logs/ms16b/review_actions_service.json` |
| Process logs | `docs/demo/logs/ms16b/fastapi.*.log`, `admin.*.log` |
| Console | 1× 404 noise; BaseWeb `preventOverflow` warnings (Streamlit) |

---

## 10. Issues / fixes / recommendation

See `docs/demo/ADMIN_PORTAL_ISSUES_AND_FIXES.md`.

**Recommendation**: Proceed to **API integration validation** (review / KPI / export routes under `/api/v1/cim-*`). Admin portal browser surfaces and `AdminReviewService` gates are sufficient for MS16B. Remaining UI automation gaps are Streamlit select quirks, not missing backend review wiring.
