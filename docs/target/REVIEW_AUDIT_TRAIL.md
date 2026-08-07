# Review Audit Trail

> **Milestone 12**

Every successful `AdminReviewService` action records:

| Field | Value |
|-------|-------|
| Table | `cim_provenance_records` |
| `entity_type` | `cim_<entity>` e.g. `cim_mapping`, `cim_extension` |
| `entity_id` | reviewed row id |
| `activity` | `review_action` |
| `agent` | reviewer id/name |
| `method` | `AdminReviewService.apply` |
| `inputs` | previous status/review_status + action |
| `outputs` | new status/review_status + extras (merge target, seed path) |
| `notes` | reviewer notes / message |

Retrieve with:

```python
from cloud_metrics.registry.provenance import ProvenanceRegistryService
ProvenanceRegistryService(session).get_chain("cim_mapping", mapping_id)
```

Orchestrator provenance (`activity=orchestration`, …) remains separate and unchanged.
