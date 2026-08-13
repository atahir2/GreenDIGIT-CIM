# UI Demo Guide

```bash
# Optional: seed catalogues if using a live Postgres
python -m cloud_metrics.scripts.seed_cim_registries

streamlit run cloud_metrics/scripts/admin_panel.py
```

1. **Registry browser** — open Metric; search `pue`; open details.
2. **Candidate review** — if the queue is empty, ingest an unknown metric or create a candidate via the demo (`python -m cloud_metrics.scripts.run_cim_demo --scenario E --use-db`). Approve/reject with Reviewer=`admin`.
3. **Evidence readiness** — open `cim:energy.efficiency.pue`; confirm ISO mandatory rows and missing fulfillment.
4. **KPI calculation** — PUE 1200/800 kWh, period `monthly`, boundary `facility` → 1.5. Then set facility unit to `W` → `invalid_unit`, no fake value.
5. **Provenance timeline** — after KPI or review, filter `entity_type=kpi_calculation` or `mapping`.
6. **Unknown metrics (legacy)** — confirm existing uncategorized sample review still works.
