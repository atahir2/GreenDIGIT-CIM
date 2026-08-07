# Candidate Approval Policy

> **Milestone 12**

1. Candidates remain invisible to registry-first **approved** lookup until `status ∈ {approved, active}`.
2. Approval is a human action via `AdminReviewService` (CLI/API), never the orchestrator.
3. Mapping approval requires the target metric to already be approved.
4. Duplicate approved mappings for the same `source_key` (any source_id) are rejected.
5. Rejected entries cannot be approved until `reopen` / `mark_under_review`.
6. Demo mappings (`origin=demo`) are not promoted to seed without an explicit `promote_to_seed` after approval.
7. Standards `exactMatch` requires `allow_exact_match=True`.
8. All decisions are audited in `cim_provenance_records`.
