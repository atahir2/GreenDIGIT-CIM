# Milestone 16B — Admin Portal Run Log

> **Run window**: 2026-08-13 ~16:20–16:43 UTC  
> **Machine**: Windows 10, Google Chrome, project `.venv` Python 3.13  
> **Raw JSON**: `docs/demo/logs/ms16b/browser_run_results.json`, `browser_run_results_pass2.json`, `review_actions_service.json`

---

## 1. Startup sequence

1. Confirmed Postgres listening on `localhost:5433`.
2. API and admin were **down**; started:
   - uvicorn `cloud_metrics.main:app` → `127.0.0.1:8000`
   - Streamlit `admin_panel.py` → `127.0.0.1:8502` (headless)
3. Health: `GET /health` → `{"status":"ok"}`; admin TCP port open.
4. Seeded demo candidates via registry services (not raw SQL):

```text
.venv\Scripts\python.exe docs/demo/ms16b_seed_demo_candidates.py
```

Created:

| Role | Key / namespace | IDs |
|------|----------------|-----|
| approve mapping | `ms16b.demo.approve_power` | mapping 98 |
| merge mapping | `ms16b.demo.merge_cpu` | mapping 99 |
| reject mapping | `ms16b.demo.reject_wue` | mapping 100 |
| incomplete extension | `cim:extension.ms16b_demo_incomplete_extension` | extension 1 / metric 33 |
| complete extension | `cim:extension.ms16b_demo_complete_extension` | extension 2 / metric 34 |
| reject extension | `cim:extension.ms16b_demo_reject_extension` | extension 3 / metric 35 |

Pending queue total at seed time: ~51 entries (workload leftovers + demo).

5. Chrome runners:

```text
.venv\Scripts\python.exe docs/demo/ms16b_browser_runner.py          # ~10.5 min
.venv\Scripts\python.exe docs/demo/ms16b_review_actions_service.py   # service path
.venv\Scripts\python.exe docs/demo/ms16b_browser_runner_pass2.py     # ~3 min
```

---

## 2. URLs tested

| URL | Result |
|-----|--------|
| http://127.0.0.1:8000/health | ok |
| http://127.0.0.1:8000/docs | Swagger visible |
| http://127.0.0.1:8502 | Admin portal sections all open |

---

## 3. Section walk (Chrome pass 1)

| Section | OK | Notes |
|---------|----|-------|
| Landing | Yes | Legacy unknown keys still listed from MS16A uploads |
| Unknown metrics (legacy) | Yes | 8 unknown raw keys |
| Registry browser | Yes | metric catalogue 35/35 + detail JSON |
| Candidate review | Yes | Queue + action buttons; AdminReviewService caption |
| Evidence readiness | Yes | PUE ISO-IEC-30134 mandatory + missing fulfillment |
| KPI calculation | Yes | Form defaults monthly/facility/1200/800 |
| Provenance timeline | Yes | Orchestration records visible |

---

## 4. KPI scenarios (Chrome)

| Scenario | Status | Provenance |
|----------|--------|------------|
| PUE 1200/800 kWh monthly facility | calculated 1.5 | 307 |
| Facility unit `W` | invalid_unit | 308 |
| Empty aggregation period | blocked | 309 |

---

## 5. Review actions (`perform_review_action` companion)

Same entry point as the UI (`cim_portal.perform_review_action`).

| Action | Entity | OK | Provenance | Notes |
|--------|--------|----|------------|-------|
| approve | mapping 98 | yes | 310 | demo approve_power |
| promote_to_seed | mapping 98 | yes | 311 | proposal in `generated/seed_promotion/` |
| reject | mapping 100 | yes | 312 | demo reject_wue |
| merge | mapping 99 | yes | 313 | → `cim:compute.node.power.draw` |
| approve incomplete extension | extension 1 | **no** | — | placeholder justification blocked |
| approve with full edits | extension 1* | yes | 314 | *companion substring bug matched incomplete; still proves metadata gate+approve |
| reject extension | extension 3 | yes | 315 | |
| UI reject extension metric | metric 35 | yes | 316 | Chrome pass 2 |
| UI approve extension metric without qk | metric 34 | **no** | — | `requires quantity_kind_id` |

---

## 6. Console / backend notes

- Browser console: occasional static 404; repeated BaseWeb Popper `preventOverflow` warnings (Streamlit).
- Admin stderr: `datetime.utcnow()` deprecation warnings (pre-existing).
- No admin portal rewrite; no direct `cim_*` SQL writes from validation scripts.

---

## 7. Artifacts

- Screenshots: `docs/demo/screenshots/ms16b/`
- Logs: `docs/demo/logs/ms16b/`
- Index: `docs/demo/ADMIN_PORTAL_SCREENSHOT_INDEX.md`
- Issues: `docs/demo/ADMIN_PORTAL_ISSUES_AND_FIXES.md`
