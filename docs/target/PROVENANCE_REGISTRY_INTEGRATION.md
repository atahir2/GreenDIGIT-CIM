# Provenance Registry Integration

> **Milestone 9** · CIM `cim_provenance_records` for orchestration decisions

## Service

`ProvenanceRegistryService.record` / `record_activity` writes to **CIM** provenance tables (distinct from legacy `ProvenanceRecord`).

## Orchestrator events

`orchestration`, `registry_mapping_lookup`, `legacy_fallback`, `unit_validation`, `source_resolution`, `asset_resolution`, `lifecycle_mapping_retrieval`, `standards_mapping_retrieval`, `validation_rule_application`, `evidence_requirement_retrieval`, `extension_candidate_creation`, `unresolved_metric_handling`

Primary id exposed as `provenance_record_id` / `provenance_log_reference`.
