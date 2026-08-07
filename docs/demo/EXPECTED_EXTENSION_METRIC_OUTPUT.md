# Expected Output — Scenario E (Extension / Unknown Metric)

## Input

```text
workflow_green_score = 0.78 score
```

## Demonstrator note

Scenario E runs with **`use_fallback=False`**. With fallback enabled, the legacy alias classifier can fuzzy-match token `work` inside `workflow_*` to `gd.performance.work.total` (candidate), which is not the intended “unknown metric → extension” demonstration. Legacy fallback remains enabled elsewhere and is covered by dedicated tests.

## Expected orchestrator fields

| Field | Expected |
|-------|----------|
| `resolved` | `false` |
| `candidate_flags.metric_unresolved` | `true` |
| `mapping_status` | not `approved` / `active` |
| `cim_namespace` | `null` or `cim:extension.*` |
| `extension_candidate_id` | set |
| Extension `status` | `candidate` |
| Extension `review_status` | `candidate` / `pending` / `under_review` |
| `standards_mappings` | empty; no approved auto-attach |
| `no_direct_standard_match` | `true` |
| `review_required` | `true` |
| `provenance_record_id` | set |

Same pattern for `carbon_aware_scheduling_gain` and `experimental_efficiency_index` in the sample.
