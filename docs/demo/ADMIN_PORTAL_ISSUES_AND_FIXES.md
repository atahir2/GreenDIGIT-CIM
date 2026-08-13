# Milestone 16B — Issues and Fixes

Issues found while validating the Admin Portal in Chrome. The admin portal was **not** rewritten. No direct database mutation from the UI.

---

## Issues found (validation / automation)

### I1 — Streamlit BaseWeb select automation flaky — **limitation** — not a product rewrite

- **Symptom**: Playwright `get_by_role("option", …)` and typed select values often fail to change Registry / Entity type / KPI / Select entry.
- **Impact**: Pass-1 registry cycle timed out; pass-2 registry screenshots often still showed `metric`; picking a specific `ms16b.demo.*` mapping row from a long queue was unreliable.
- **Mitigation**:
  - Confirmed section landing pages and default registry detail in Chrome.
  - Confirmed all 11 registries load via `load_registry_rows` against live Postgres.
  - Demo approve / reject / merge / promote executed through `perform_review_action` (identical to UI backend path).
- **Not fixed in product**: Would require admin UI changes (e.g. `key=` + simpler widgets) — out of MS16B scope.

### I2 — Candidate queue crowded by prior workload candidates — **observation**

- **Symptom**: After MS16A orchestrator uploads, pending queue ~50+ entries; demo rows not first in the select list.
- **Mitigation**: Seeded uniquely named `ms16b.demo.*` candidates; documented service companion actions with provenance IDs.

### I3 — Extension approve UI cannot supply full metadata — **product limitation** (documented)

- **Symptom**: UI only has “Edit justification”; Chrome approve of extension-linked **metric** candidate fails with `metric approval requires quantity_kind_id` when quantity kind is unset.
- **Why correct**: Matches `AdminReviewService` gates (no silent approve).
- **Full path**: Service `edits` with justification + quantity_kind + unit + definition + source_context succeeds (M12 tests + companion).
- **Recommendation for later**: Optional admin form fields for extension metadata (not done in MS16B).

### I4 — Companion script substring bug (`complete` ⊂ `incomplete`) — **test harness** — fixed in script

- **Symptom**: `ms16b_review_actions_service.py` matched `incomplete_extension` when searching `complete_extension`.
- **Fix**: Prefer exact / `ms16b_demo_{fragment}` matching in the companion script.
- **Not a CIM product bug**.

### I5 — Evidence fulfillment never stored — **by design**

- Mandatory evidence shows as missing fulfillment; readiness `declared`.
- Matches Milestone 14 / evidence docs. Not a defect for MS16B.

### I6 — Browser console noise — **non-blocking**

- Occasional 404 for a static asset; BaseWeb Popper `preventOverflow` warnings from Streamlit.

---

## Fixes made during MS16B

| ID | Change | Scope |
|----|--------|-------|
| — | No admin portal code rewrite | constraint |
| H1 | Added `docs/demo/ms16b_seed_demo_candidates.py` | demo seed via registry services |
| H2 | Added Chrome runners `ms16b_browser_runner.py` / `_pass2.py` | validation only |
| H3 | Added `ms16b_review_actions_service.py` using `perform_review_action` | same backend as UI |
| H4 | Tightened companion extension lookup matching | harness |

No migration / orchestrator / review-service logic changes were required for MS16B gates to work.

---

## Remaining limitations

1. Playwright ↔ Streamlit select reliability.
2. Extension review UI lacks full metadata editors.
3. Evidence fulfillment store still absent (declared-only readiness).
4. Provenance timeline shows a large mixed list; filtering by entity type via text input is easy to miss in automation.
5. WUE/CUE calculator forms exist but were not fully exercised in Chrome after select flakiness (PUE scenarios fully covered).

---

## Recommendation

**Proceed to API integration validation** for `/api/v1/cim-review`, `/api/v1/cim-kpi`, and export routes. MS16B confirms the Admin Portal exposes the registry surfaces and that review/KPI actions go through backend services with provenance, not direct DB edits.
