# Asset Registry Integration

> **Milestone 6** · Soft asset resolution in registry-first mapping lookup

---

## Service

`cloud_metrics/registry/asset/service.py` → `AssetRegistryService(session=...)`

| Method | Behaviour |
|--------|-----------|
| `get_by_identifier` / `get_by_id` | Lookup in `cim_assets` |
| `get_hierarchy` | Walk parents root←leaf reversed to root→leaf |
| `resolve_or_create` | Idempotent by `(identifier, type)` |
| `resolve_from_metadata` | Extract hints + optional hierarchy enrichment |

---

## Asset types

`site`, `data_centre`, `cluster`, `rack`, `node`, `server`, `cpu`, `gpu`,
`storage_system`, `network_device`, `virtual_machine`, `container`, `service`,
`workflow`, `workflow_run`, `dataset`, `experiment`

Aliases: `datacenter`→`data_centre`, `vm`→`virtual_machine`, `host`→`node`.

---

## Resolution result

`AssetResolutionResult`:

* `asset_id`, `asset_identifier`, `asset_type`, `parent_asset_id`
* `resolution_status`: `resolved` \| `candidate_created` \| `missing` \| `ambiguous` \| `unknown` \| `not_requested`
* `hierarchy`: optional list of `AssetEntry` created/resolved during enrichment
* `confidence_score`, `message`, `warnings`

---

## Mapping integration

```python
result = resolve_raw_metric(
    "gpu_power",
    session=session,
    context={
        "cluster": "cluster-A",
        "node": "hpc-node-07",
        "gpu_id": "gpu-0",
    },
)
# result.asset_resolution.asset_identifier == "gpu-0"
# result.asset_resolution.parent_asset_id → node
```

Missing asset metadata → `missing` warning, mapping still succeeds.
