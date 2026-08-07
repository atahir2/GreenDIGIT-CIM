# Legacy Review and Candidate Handling

> **Milestone 12** · Pre-admin-review baseline (how candidates existed before the review service)

## Status fields (`CimGovernanceMixin`)

| Field | Typical values |
|-------|----------------|
| `status` | `draft`, `candidate`, `approved`, `rejected`, `deprecated`, `retired`, `active` (+ extension: `accepted`, `merged`) |
| `review_status` | `pending`, `under_review`, `approved`, `rejected` |

## How candidates were created (pre-M12)

| Entity | Creation path | Default status |
|--------|---------------|----------------|
| Mapping | `MappingRegistryService.propose` / fallback backfill | `candidate` / `under_review` |
| Extension | `ExtensionRegistryService.propose_from_raw` via orchestrator | `candidate` / `under_review` |
| Source / Asset | `resolve_or_create(..., create_candidate=True)` | `candidate` / `under_review` |
| Metric (fallback) | created when mapping needs a target | often `candidate` |
| Standards / lifecycle | mostly seeded approved; uncertain rows use `underReview` relation | varies |

## What existed before Milestone 12

- Extension `approve()` / `reject()` / `merge()` placeholders (accepted ≠ catalogue-approved).
- Legacy API `POST /api/v1/registry/mappings/{id}/approve` for **Antigravity** `CimMapping` only.
- Streamlit `admin_panel.py` for legacy `gd.uncategorized.*` unknowns.
- Soft orchestrator `review_required` flag; no hard block; provenance for orchestration, not human review.

## Gaps filled by Milestone 12

- Unified `AdminReviewService` across CIM `cim_*` entities
- Enforced transitions + unsafe-transition guards
- Provenance `activity=review_action` for human decisions
- Seed **proposal** export without auto-editing `seed/data.py`
- CIM review CLI + `/api/v1/cim-review` routes
