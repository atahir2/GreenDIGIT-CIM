# Legacy Governance and Review Handling

> **Milestone 9** · Baseline before Rule / Evidence / Provenance / Extension orchestration

---

## Pre–Milestone 9 state

| Concern | Location | Behaviour |
|---------|----------|-----------|
| Validation (legacy) | `services/rule_registry_service.validate_metric_sample` | Hard-coded string checks on `gd.*` keys; not CIM Rule Registry |
| Validation (seed) | `cim_validation_rules` | Declarative seed only; not evaluated by orchestrator |
| Evidence (seed) | `cim_evidence_requirements` | PUE/WUE/CUE/workflow seeds; skeleton service empty |
| Provenance (legacy) | `services/provenance_registry_service` → `ProvenanceRecord` | Used by `process_metric_sample` for ingestion/unit_conversion |
| Provenance (CIM) | `cim_provenance_records` | Bootstrap seed marker only |
| Extension | `cim_extension_metrics` | Table exists; no runtime candidate creation |
| Candidate mappings | Mapping Registry | Candidate on fallback; not auto-approved |
| Orchestrator (M7–8) | mapping/unit/source/asset/lifecycle/standards | No governance enrichment |

## Gaps closed in Milestone 9

* Session-backed Rule / Evidence / Provenance / Extension services under `cloud_metrics/registry/`
* Soft validation results (structured) during orchestration
* Evidence requirement lookup for reportable KPIs
* CIM provenance records for orchestration decisions
* Extension candidates for unknown / unresolved metrics
* Additive orchestrator fields; ingestion not hard-blocked

## Explicit non-goals (unchanged)

* Full admin review UI
* Blocking ingestion on warnings
* Replacing legacy `validate_metric_sample` / legacy `ProvenanceRecord`
