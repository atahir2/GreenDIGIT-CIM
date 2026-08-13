# UI Manual Validation Checklist

Streamlit UI tests are not in CI. Use this list after `streamlit run cloud_metrics/scripts/admin_panel.py`.

## Navigation

- [ ] Sidebar lists six sections
- [ ] Switching away from Unknown metrics does not require unknown samples (no blank `st.stop` on CIM pages)
- [ ] Legacy unknown-metrics page still lists uncategorized keys when present

## Registry browser

- [ ] Each of the 11 registries loads without error
- [ ] Status / review / search filters reduce rows
- [ ] Detail JSON shows the selected id

## Candidate review

- [ ] Empty queue shows a success/info message (not a crash)
- [ ] Approve calls backend: status becomes approved; provenance id shown
- [ ] Reject sets rejected
- [ ] Merge without target namespace fails with a service error (not a raw SQL write)
- [ ] Promote on an approved mapping writes a seed proposal path when allowed

## Evidence readiness

- [ ] PUE / WUE / CUE / workflow energy appear
- [ ] PUE shows ISO-IEC-30134 mandatory evidence
- [ ] Missing fulfillment count equals mandatory count (no fulfillment store)

## KPI calculation

- [ ] Valid PUE 1200/800 kWh monthly/facility → calculated 1.5
- [ ] Facility unit `W` → `invalid_unit`, value empty
- [ ] IT energy `0` → `blocked`
- [ ] Empty period → `blocked`
- [ ] Provenance id shown after run

## Provenance timeline

- [ ] Recent records list after KPI or review
- [ ] Detail shows activity, agent, inputs/outputs

## Compatibility

- [ ] Legacy Approve mapping on unknown samples still works
- [ ] Maintenance buttons (rebuild JSON / clear cache) still present on the legacy page
