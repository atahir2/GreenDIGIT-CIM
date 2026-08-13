# Admin Portal UI

> **Milestone 14** · Streamlit CIM admin portal

## Run

```bash
streamlit run cloud_metrics/scripts/admin_panel.py
```

Sidebar **Section** switcher:

| Section | Purpose |
|---------|---------|
| Unknown metrics (legacy) | Existing uncategorized `MetricSample` review (unchanged) |
| Registry browser | Read-only `cim_*` catalogues |
| Candidate review | `AdminReviewService` queue and actions |
| Evidence readiness | Declared vs missing fulfillment for reportable KPIs |
| KPI calculation | `KpiCalculationService` PUE / WUE / CUE |
| Provenance timeline | `cim_provenance_records` |

**Reviewer** in the sidebar is required for review actions.

## Backend only

- Review: `perform_review_action` → `AdminReviewService.apply`
- KPI: `KpiCalculationService`
- Evidence / standards / lifecycle / provenance: existing registry services
- Browser lists: read-only ORM (no writes)

## Helpers

`cloud_metrics/ui/cim_portal.py` — testable without launching Streamlit.
