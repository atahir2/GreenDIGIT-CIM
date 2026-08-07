# Expected Output — Scenario A (Known Operational Metric)

## Input

```text
node_power_watts = 420 W
source = prometheus_node_exporter (monitoring_system)
node = hpc-node-07 / cluster-A / RI-site-1
```

## Expected orchestrator fields

| Field | Expected |
|-------|----------|
| `cim_namespace` | `cim:compute.node.power.draw` |
| `resolved` | `true` |
| `resolution_path` | `registry` |
| `fallback_used` | `false` |
| `mapping_status` | `approved` / `active` |
| `unit_validation_status` | `valid` |
| `expected_quantity_kind` | `Power` |
| `canonical_unit` | `W` |
| `source_resolution_status` | `resolved` or `candidate_created` |
| `asset_resolution_status` | `resolved` or `candidate_created` |
| `lifecycle_stages` | includes `operation`, `optimisation` (seeded) |
| `standards_relation_types` | `contextualMatch` / `closeMatch` / `inputToKPI` — **not** ISO/EN `exactMatch` |
| `provenance_record_id` | set |
| `extension_candidate_id` | `null` |

## Example summary line shape

```text
raw=node_power_watts
  cim_namespace=cim:compute.node.power.draw
  resolved=True path=registry status=approved fallback=False
  unit=W -> valid (expected Power/W)
  source=candidate_created id=<n>
  asset=candidate_created id=<n>
  lifecycle=['operation', 'optimisation', ...]
  standards_relations=['contextualMatch', 'closeMatch', 'inputToKPI', ...]
  provenance=cim_provenance_records:<n>
```
