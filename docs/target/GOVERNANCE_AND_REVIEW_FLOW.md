# Governance and Review Flow

> **Milestone 9** · Soft governance in the registry orchestrator

```
resolve mapping → lifecycle/standards →
  [unresolved?] create extension candidate →
  evaluate rules → fetch evidence →
  record provenance →
  set review_required / governance_* fields
```

* Warnings and errors are additive; ingestion is not hard-blocked
* `review_required` when unresolved, candidate, fallback, extension, or blocking rule failures
* Candidate metrics never receive approved standards mappings (M8 policy retained)
