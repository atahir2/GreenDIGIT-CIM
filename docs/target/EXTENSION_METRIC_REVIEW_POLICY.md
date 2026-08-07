# Extension Metric Review Policy

> **Milestone 12** (extends Milestone 9 policy)

## Create

- Unknown metrics → extension **candidates** (`cim:extension.<slug>`).
- Never auto-approved by orchestrator.

## Approve (catalogue promotion)

`AdminReviewService.approve(extension, ...)` requires:

| Requirement | Notes |
|-------------|-------|
| Real justification | Placeholder orchestrator text is insufficient |
| Quantity kind and/or unit | Via metric columns or approval `edits` |
| Definition / description | On linked `CimMetricDefinition` |
| Source context | `edits.source_context` or justification supplied at approval time |

On success:

- Extension `status=approved`, `review_status=approved`
- Linked metric definition also set to approved
- Provenance `review_action` recorded

## Reject / merge

- Reject → `rejected` / `rejected`
- Merge into an **approved** target namespace → extension `merged` (linked metric marked merged; target unchanged)

## Placeholder `ExtensionRegistryService.approve`

Still marks `accepted` / `under_review` only. Full catalogue approval goes through `AdminReviewService`.
