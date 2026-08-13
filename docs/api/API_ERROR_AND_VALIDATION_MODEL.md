# API Error and Validation Model

> **Milestone 16C**

## HTTP layer

| Code | When |
|------|------|
| 200 | Orchestration completed (may still include validation issues / candidates) |
| 400 | Empty `metrics`, unknown scenario letter, bad KPI name on KPI API |
| 409 | Review action rejected by governance (candidate already terminal, etc.) |
| 500 | Unexpected server / DB error |

Important: **unit incompatibility does not return HTTP 4xx** on ingest. Soft validation reports issues in the JSON body so partners can see mapping + validation together. Reportable KPI calculation **does** hard-block invalid inputs in the `kpi` object.

## Ingest response statuses

| `status` | Meaning |
|----------|---------|
| `accepted` | All metrics resolved without critical issues |
| `accepted_with_validation_issues` | Resolved but unit/rule critical issues present |
| `accepted_with_candidates` | One or more unresolved / extension candidates |
| `rejected` | No metrics provided (service-level) |

## Per-metric validation signals

| Signal | Source |
|--------|--------|
| `unit_validation_status` | Unit Registry via orchestrator |
| `candidate_flags.unit_incompatible` | Soft unit gate |
| `validation_results` | Rule Registry |
| `governance_warnings` / `governance_errors` | Milestone 9 governance |
| `critical_issues` | MS16C rollup (failed critical rules + incompatible units + errors) |
| `accepted_as_valid` | `true` only if resolved and no critical issues |
| `extension_candidate_id` | Extension Registry |
| `review_required` | Governance / rules |

## KPI blocking (when `calculate_kpi` set)

| `calculation_status` | Typical cause |
|----------------------|---------------|
| `calculated` | Valid inputs + period + boundary |
| `invalid_unit` | Incompatible energy/water/carbon units |
| `blocked` | Zero/missing divisor, missing period/boundary |
| `missing_input` | Required field absent |
| `under_review` | Candidate/unapproved input metrics |

`reportable_approved` is `false` unless the KPI is fully reportable under policy.

## Review API errors

Review endpoints return 409 with `ReviewDecision` payload when transitions are illegal (e.g. approve incomplete extension without justification / unit / definition).

## Soft vs hard

| Path | Soft or hard? |
|------|----------------|
| Metric ingest orchestration | Soft — warns, still returns results |
| Reportable KPI calculation | Hard — no fake approved value |
| Admin approve extension | Hard — metadata gates |
| Unknown metric | Soft create candidate — never auto-approve |
