# Milestone 12 — Admin Review Workflow

Backend/service-level review for CIM candidates, extensions, and under-review mappings.

## Deliverables

- `cloud_metrics/registry/review/` — `AdminReviewService`, transitions, seed promotion
- CLI: `python -m cloud_metrics.scripts.review_candidates`
- API: `/api/v1/cim-review`
- Tests: `tests/test_admin_review_workflow.py`
- Docs: `ADMIN_REVIEW_WORKFLOW.md`, policies, audit trail, legacy handling

## Non-goals

Full UI · auto-approval · auto seed file edits · ingestion/orchestrator behavior changes

## Next

Streamlit / admin UI over `/api/v1/cim-review`, then optional hard-block policies.
