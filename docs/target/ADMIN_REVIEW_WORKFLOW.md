# Admin Review Workflow

> **Milestone 12** · Controlled review of registry candidates

## Service

`AdminReviewService` (`cloud_metrics/registry/review/`) — aliases: `RegistryReviewService`, `CandidateReviewService`.

```python
from cloud_metrics.registry.review import get_admin_review_service, ReviewEntityType

svc = get_admin_review_service(session)
pending = svc.list_pending()
decision = svc.approve(ReviewEntityType.MAPPING, mapping_id, reviewer="alice")
```

## Reviewable entities

| Entity type | Table |
|-------------|-------|
| `mapping` | `cim_metric_mappings` (no standard) |
| `standards_mapping` | `cim_metric_mappings` (with `standard_id`) |
| `extension` | `cim_extension_metrics` |
| `metric` | `cim_metric_definitions` |
| `source` | `cim_sources` |
| `asset` | `cim_assets` |
| `unit` | `cim_units` |
| `lifecycle_link` | `cim_metric_lifecycle_links` |

## Actions

`approve` · `reject` · `edit` · `merge` · `deprecate` · `promote_to_seed` · `request_changes` · `mark_under_review` · `reopen`

## CLI

```bash
python -m cloud_metrics.scripts.review_candidates list
python -m cloud_metrics.scripts.review_candidates approve mapping 12 --reviewer alice
python -m cloud_metrics.scripts.review_candidates reject extension 3 --reviewer alice --notes "needs unit"
python -m cloud_metrics.scripts.review_candidates merge mapping 12 --target cim:compute.node.power.draw --reviewer alice
python -m cloud_metrics.scripts.review_candidates promote mapping 12 --reviewer alice
```

## API (additive)

Prefix: `/api/v1/cim-review`

- `GET /candidates`
- `GET /candidates/{entity_type}/{entity_id}`
- `POST .../approve|reject|merge|promote|deprecate`

Does **not** replace legacy `/api/v1/registry` approve routes.

## Invariants

- No automatic approval during ingestion/orchestration
- Rejected → approved requires `reopen` (or equivalent) first
- Canonical seed files are never modified by `promote_to_seed`
- Every successful action writes provenance `activity=review_action`
