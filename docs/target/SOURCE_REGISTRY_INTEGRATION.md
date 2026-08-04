# Source Registry Integration

> **Milestone 6** · Soft source resolution in registry-first mapping lookup

---

## Service

`cloud_metrics/registry/source/service.py` → `SourceRegistryService(session=...)`

| Method | Behaviour |
|--------|-----------|
| `get_by_name` / `get_by_id` | Lookup in `cim_sources` |
| `resolve_or_create` | Idempotent find; optional candidate create |
| `resolve_from_metadata` | Uses `extract_source_hints()` |
| `list_entries` | All rows (empty without session) |

Legacy `services/unit`-style facade and `models.source.Source` remain unchanged.

---

## Source types

`file`, `api`, `monitoring_system`, `workflow_engine`, `manual_input`, `database`, `cloud_api`  
(+ aliases: `prometheus`/`opentelemetry` → `monitoring_system`, `file_upload` → `file`, …)

---

## Resolution result

`SourceResolutionResult`:

* `source_id`, `source_name`, `source_type`
* `resolution_status`: `resolved` \| `candidate_created` \| `missing` \| `ambiguous` \| `unknown` \| `not_requested`
* `confidence_score`, `message`, `warnings`

Candidates use `status=candidate`, `review_status=under_review`.

---

## Mapping integration

```python
result = resolve_raw_metric(
    "cpu_usage",
    session=session,
    context={"job": "node_exporter", "source_type": "prometheus"},
)
# result.source_resolution → SourceResolutionResult
```

Default: resolve source only when `context` is provided (or `resolve_source=True`).  
Never flips `resolved` to `False`.
