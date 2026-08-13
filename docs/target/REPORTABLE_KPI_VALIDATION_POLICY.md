# Reportable KPI Validation Policy

> **Milestone 13**

## Two tracks

| Track | Where | Unit / completeness policy |
|-------|--------|----------------------------|
| Operational ingestion | Orchestrator / `process_metric_sample` | Soft: incompatible units **warn**; sample is not hard-blocked |
| Reportable KPI calculation | `KpiCalculationService` | Hard-block: incompatible or missing data **must not** produce an approved KPI |

## Hard-block rules (`reportable=True`, default)

| Condition | `calculation_status` |
|-----------|----------------------|
| Required input value missing | `missing_input` |
| Observed unit missing, unknown, or wrong quantity kind | `invalid_unit` |
| IT energy zero, negative, or missing after normalize | `blocked` |
| Aggregation period missing | `blocked` |
| Calculation boundary missing | `blocked` |
| Any input metric/mapping `candidate` / `under_review` / `draft` / `rejected` | `under_review` (value may be computed for review; `reportable_approved=False`) |

`allow_candidate_inputs=True` is an explicit review-policy override and still records provenance.

`reportable=False` skips period/boundary gates (operational preview only; not an approved reportable result unless other gates pass). Prefer leaving `reportable=True` for published KPIs.

## What is never done

- Silent calculation from Power units on Energy inputs
- Auto-approval of candidate facility/IT/water/carbon metrics as reportable KPIs
- Inventing ISO/EN `exactMatch` for WUE/CUE when not seeded
- Changing ingestion to hard-block operational samples
