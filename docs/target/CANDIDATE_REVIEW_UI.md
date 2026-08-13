# Candidate Review UI

Queue from `AdminReviewService.list_pending`.

Actions (all via `AdminReviewService.apply`):

approve · reject · edit · merge · promote_to_seed · deprecate · request_changes · mark_under_review · reopen

Optional: justification edit, merge target namespace, allow exactMatch (standards mappings only).

On success the UI shows previous → new status and `provenance_record_id`.
