# Milestone 7 — Registry-Orchestrated Ingestion

> Control note for Stage / Milestone 7 implementation

## Scope delivered

* Documented legacy ingestion entry points (`LEGACY_INGESTION_FLOW.md`).
* Added `RegistryOrchestratorService` under `cloud_metrics/registry/orchestrator/`.
* Wired **unified file ingestion** (`ingest_from_file`) to opt into the orchestrator by default.
* Left real-time / API / Streamlit on the legacy classifier path.
* Preserved Mapping Registry legacy fallback and soft unit/source/asset enrichment.
* Tests in `tests/test_registry_orchestrator.py`; full suite green.

## Non-goals (deferred)

* Rewiring all ingestion paths
* Removing legacy fallback or old ingestion functions
* Lifecycle / standards / evidence / provenance governance expansion
* Full rewrite of `process_metric_sample`

## Recommended next milestone

Extend orchestrator opt-in to `ingest_from_api` / Streamlit once unified-path coverage and review queues are stable; then tighten storage to prefer CIM namespaces end-to-end.
