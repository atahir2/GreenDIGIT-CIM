# Candidate Mapping Policy

> **Milestone 4** · When mappings and metrics are approved vs candidate

---

## Rules

### Approved mapping

All of the following must hold:

1. Target metric exists in ``cim_metric_definitions``.
2. Metric `status ∈ {approved, active}` and `review_status == approved`.
3. Alignment is trusted (`GD_TO_CIM` explicit map) **or** an equivalent human-approved seed.
4. Migration origin is a known legacy source (JSON / aliases / seeds).

Then:

* Mapping `status = approved`, `review_status = approved`
* `relation_type = exactMatch`
* `origin = migrated`
* `approved_by = milestone4_migration`

### Candidate metric definition

Created when a migrated mapping points at a ``cim:*`` namespace that is **not**
already present (or is not a trusted alignment to an approved seed):

* `status = candidate`
* `review_status = under_review`
* `created_by = milestone4_migration`
* Notes include the legacy ``gd.*`` key and source

### Candidate mapping

Whenever the linked metric is not approved:

* Mapping `status = candidate`
* `review_status = under_review`
* `relation_type = underReview`

### Fallback backfill (optional)

When `create_candidate_on_fallback=True` and legacy resolution succeeds:

* Create candidate metric if missing
* Create candidate mapping for later review
* Do **not** auto-approve

### Unresolved

Unknown raw keys return `status=unresolved` without inserting rows
(unless a future milestone opts into auto-proposal during ingestion).

---

## Forbidden

* Silently marking uncertain / heuristic-only metrics as `approved`
* Overwriting approved seed metrics during migration
* Deleting legacy sources to “force” registry-only behaviour

---

## Review queue

1. Run migration (optionally `--seed-first`).
2. Query candidates:

```sql
SELECT namespace, status, review_status, notes
FROM cim_metric_definitions
WHERE status = 'candidate';

SELECT source_key, status, review_status, rationale
FROM cim_metric_mappings
WHERE status = 'candidate';
```

3. Promote after human review (later admin / API milestone).
