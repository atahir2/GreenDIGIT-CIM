# Legacy Admin UI Handling

> **Milestone 14** · Behaviour of `admin_panel.py` before CIM portal pages

## Entry point

```bash
streamlit run cloud_metrics/scripts/admin_panel.py
```

Single-page Streamlit app titled **CIM Admin Portal for Unknown Metrics Review**. There are no `pages/` modules.

## What it did

| Area | Behaviour |
|------|-----------|
| Data source | Legacy `MetricSample` rows whose `unified_key` is `gd.uncategorized.*` or `gd.*.unknown.*` |
| Filters | Datacenter (`Asset` type=datacenter), look-back days, raw_key search, max rows |
| Suggestion | `classify_metric()` ensemble + taxonomy pickers (`Category` / `Subcategory`) |
| Approve | Writes **legacy** `MetricDefinition` + `CimMapping` via `mapping_registry_service`, optional keyword learn, `sync_metric_mapping` JSON, optional retrofix of samples |
| Maintenance | Rebuild mapping JSON; clear classifier cache |
| Empty state | `st.stop()` when no unknown keys — later sections would not render |

## What it did **not** do

- Browse `cim_*` registries
- Call `AdminReviewService` (Milestone 12)
- Show evidence readiness or KPI calculation
- Show `cim_provenance_records` timelines
- Review extension candidates / CIM mapping candidates

## Compatibility rule (Milestone 14)

The unknown-metrics review page is **preserved**. New CIM pages are added via sidebar navigation so `st.stop()` only applies to the legacy page.
