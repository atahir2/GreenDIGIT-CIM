# Registry-Driven CIM Refactoring Plan

This document outlines the detailed refactoring plan to transition the Common Information Model (CIM) codebase from a fragmented, hardcoded, file-based mapping configuration to a modular, registry-driven architecture.

---

## 1. Objectives & Goals
* **Modularization**: Decouple metric classification, namespace generation, unit validation, and conversion rules into separate database-backed registries.
* **Declarative Validation**: Transition from hardcoded logic/heuristics to user-defined SQL tables for validation rules, metadata checks, and unit mapping.
* **Audit and Lineage**: Capture every ingestion activity, automated classification, unit conversion, and rule violation via a structured Provenance Registry.
* **Robust Telemetry Ingestion**: Modernize pipeline controllers to support automated unit normalization (e.g. converting Watt-hours `Wh` to the canonical `kWh`) and auto-learning mappings with confidence thresholds.

---

## 2. Refactoring Milestones

### Milestone 1: Core Registries & Schema Setup
Introduce database tables and SQLAlchemy models for the primary registries:
* **Metric Registry**: Controlled metric definitions, namespaces, and domains.
* **Unit Registry**: Quantity kinds, conversion rules, and unit validation.
* **Source Registry**: Telemetry origins, API integrations, and protocols.
* **Asset Registry**: Resource mapping, hierarchies, and datacenters.
* **Standards Registry**: Interoperability standards (e.g. SAREF, QUDT, OTel).

### Milestone 2: Mapping & Rule Registries
Consolidate mappings and logic:
* **Mapping Registry**: Unified `CimMapping` table to link raw keys to metric definitions.
* **Rule Registry**: Extensible rules for validating metrics (percentage limits, PUE ranges, unit conflicts).
* **Provenance Registry**: Audit records logging the origin, conversion, and validation of ingested telemetry.

### Milestone 3: Ingestion Pipeline Refactoring
Update `process_metric_sample` and ingestion scripts (`realtime_ingestor.py`, `unified_ingestion.py`, `aws.py`, `gcp.py`) to:
1. Dynamically resolve raw keys via the Mapping Registry.
2. Normalize raw units to canonical ones.
3. Validate metrics against the Rule Registry.
4. Record lineage via the Provenance Registry.

### Milestone 4: API, UI & Cleanup
* Expose CRUD routers for administrative operations on registries.
* Retarget the Streamlit Admin Portal to edit mappings in `CimMapping` and view assets.
* Safely drop legacy tables and files.

---

## 3. Files to be Created

| File Path | Description |
| :--- | :--- |
| `cloud_metrics/api/registry_api.py` | FastAPI router for listing and modifying registries. |
| `cloud_metrics/models/asset.py` | Asset model supporting hierarchy trees. |
| `cloud_metrics/models/source.py` | Source model supporting telemetry protocol configurations. |
| `cloud_metrics/models/unit.py` | QuantityKind and Unit conversion schemas. |
| `cloud_metrics/models/cim_mapping.py` | Unified mappings table replacing legacy tables. |
| `cloud_metrics/models/provenance.py` | Audit records mapping inputs to outputs. |
| `cloud_metrics/services/unit_registry_service.py` | Unit conversion and canonical unit validation. |
| `cloud_metrics/services/mapping_registry_service.py` | Mapping proposal, resolution, and approval logic. |
| `cloud_metrics/services/rule_registry_service.py` | Rules validation engine. |
| `cloud_metrics/services/provenance_registry_service.py` | Provenance log recorder. |
| `tests/test_registry_api.py` | API client test suite. |

---

## 4. Files to be Modified

| File Path | Description |
| :--- | :--- |
| `cloud_metrics/main.py` | Mount the new `registry_api` router. |
| `cloud_metrics/ingestion/automated_mapper.py` | Adapt pipeline to normalize units, validate, and write provenance. |
| `cloud_metrics/ingestion/realtime_ingestor.py` | Pipeline routing through the automated mapper. |
| `cloud_metrics/ingestion/unified_ingestion.py` | Asset lookup instead of static datacenter IDs. |
| `cloud_metrics/classifiers/ensemble_classifier.py` | Resolve mappings via the Mapping Registry before fallback classifiers. |
| `cloud_metrics/scripts/admin_panel.py` | Connect approvals to `CimMapping` table updates. |

---

## 5. Files to be Deprecated or Removed

* `cloud_metrics/models/metric_keyword.py`: Legacy keyword dictionary cache table.
* `cloud_metrics/models/metric_source_map.py`: Legacy raw-to-unified per-DC mapping table.
