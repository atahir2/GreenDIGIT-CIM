# Standards Registry Integration

> **Milestone 8** · Metric ↔ standards mapping enrichment

---

## Service

`StandardsRegistryService` (`cloud_metrics/registry/standards/`)

* `list_entries()` / `get_by_code(code)` — standards catalogue
* `get_mappings_for_metric(namespace | metric_id, allow_approved=...)` — seeded mappings
* `register(entry)` — optional candidate catalogue insert (not auto-approved)

Mappings live on `cim_metric_mappings` rows with `standard_id` set (seed origin).

## Orchestrator fields

* `standards_mappings` — list of `{code, name, relation_type, confidence, review_status, notes, term}`
* `standards_relation_types`
* `standards_confidence_scores`
* `standards_review_status`
* `standards_notes`
* `no_direct_standard_match` — `True` when no `exactMatch` is present

## Candidate / unknown policy

Approved standards mappings are attached **only** when:

* mapping resolution is registry (not legacy fallback), and
* mapping status is approved/active, and
* metric definition status is approved/active

Otherwise: empty mappings + `no_direct_standard_match=True`.
