# Candidate Mapping Flow (Ingestion)

> **Milestone 7** · How candidates and warnings appear during orchestrated ingestion

Builds on `CANDIDATE_MAPPING_POLICY.md` (Milestone 4). This doc covers **runtime** behaviour when the registry orchestrator is invoked.

---

## Mapping candidates

| Situation | Behaviour |
|-----------|-----------|
| Approved/active registry mapping | `mapping_status=approved` (or active), not a candidate |
| Legacy fallback hit | `mapping_status=candidate`, `fallback_used=true`; optional backfill when `create_candidate_on_fallback=True` |
| No registry + no legacy | `mapping_status=unresolved`, `candidate_flags.metric_unresolved=true` — **not** approved |

Unresolved metrics are never silently approved. Storage may still persist via the legacy ensemble path when the orchestrator does not resolve a key.

---

## Unit candidates / warnings

| Situation | Flag / warning |
|-----------|----------------|
| Unknown unit token | `unit_unknown`, warning |
| Incompatible quantity kind | `unit_incompatible`, warning (soft — does not block resolve) |
| Missing observed unit | warning when validation requested |

---

## Source candidates

| Situation | Behaviour |
|-----------|-----------|
| Known source | `source_resolution_status=resolved` |
| Sufficient metadata, unknown | `candidate_created` (status candidate, under review) |
| Missing metadata | `missing` + warning — does not crash ingestion |

---

## Asset candidates

| Situation | Behaviour |
|-----------|-----------|
| Known asset | `resolved` |
| Sufficient identifier + type | `candidate_created` |
| Insufficient metadata | `missing` — no invented hierarchy |

---

## Orchestrator `candidate_flags`

```
mapping_candidate
metric_unresolved
unit_unknown
unit_incompatible
source_missing
source_candidate
asset_missing
asset_candidate
```

These are returned on `OrchestratorResult` and embedded under `extra_meta.registry_orchestrator` when unified ingestion persists a sample.
