# Registry-Driven CIM Architecture: Implementation Sequence

This document maps out the 14-stage implementation sequence used to transition the Common Information Model (CIM) to a modular, registry-driven architecture. 

---

## Stage 1: Documentation and Cleanup of Current Architecture
* **Objective**: Establish baseline understanding of existing models and classifiers and identify clean boundaries.
* **Actions**:
  * Completed a technical audit and gap analysis of the codebase.
  * Identified legacy tables (`metric_keywords`, `metric_source_map`) and static configurations (`alias_classifier.py`, `seed_taxonomy_standards.py`) to be deprecated.
  * Prepared initial gap analysis and component mapping documentation.

## Stage 2: Introduce Registry Folder/Module Structure
* **Objective**: Restructure codebase modules to house core registry logic, services, and APIs.
* **Actions**:
  * Created `cloud_metrics/api/registry_api.py` for FastAPI endpoints.
  * Modularized registry services under `cloud_metrics/services/` (`unit_registry_service.py`, `mapping_registry_service.py`, `rule_registry_service.py`, `provenance_registry_service.py`).
  * Created `cloud_metrics/registry/` directory for high-level classification/namespace configurations.

## Stage 3: Add Database Models/Tables for Registries
* **Objective**: Implement SQLAlchemy models for the 11 target registries.
* **Actions**:
  * Created/expanded the following models:
    * **Metric Registry**: Expanded `MetricDefinition` in [metric_definition.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/metric_definition.py) with fields: `label`, `description`, `domain`, `quantity_kind`, `canonical_unit_id` (FK), `metric_type`, `status`, `version`.
    * **Unit Registry**: Created `QuantityKind` and `Unit` models in [unit.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/unit.py).
    * **Source Registry**: Created `Source` model in [source.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/source.py) (uses `metadata_info` field to avoid SQLAlchemy keyword collisions).
    * **Asset Registry**: Created hierarchical `Asset` model with `parent_id` self-referencing FK in [asset.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/asset.py).
    * **Standards Registry**: Utilized existing `Standard` in [standard_models.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/standard_models.py).
    * **Mapping Registry**: Created `CimMapping` model in [cim_mapping.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/cim_mapping.py) replacing legacy mapping tables.
    * **Provenance Registry**: Created `ProvenanceRecord` in [provenance.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/provenance.py) supporting activity and entity audits.
    * **Governance Registries (Lifecycle, Rule, Evidence, Extension)**: Linked dynamically using structural logic, validation rules, and columns across Metric and Asset tables.

## Stage 4: Migrate Existing Metric Mappings into Metric & Mapping Registries
* **Objective**: Extract hardcoded mappings, file-based maps, and legacy table data into database-backed registry entries.
* **Actions**:
  * Created database migration scripts and seed scripts.
  * Ported ~80 alias patterns from `alias_classifier.py` and taxonomy definitions into `CimMapping` rows.
  * Implemented [seed_registries.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/scripts/seed_registries.py) to populate standard quantity kinds, units, metrics, standards, and initial mappings.

## Stage 5: Refactor Namespace Generation to Use Metric Registry
* **Objective**: Remove static or heuristic namespace parsing, resolving metric schema formats strictly from DB definitions.
* **Actions**:
  * Retargeted namespace logic to query `MetricDefinition` directly.
  * Integrated fallback to `gd.uncategorized.*` using extension handling configurations.

## Stage 6: Refactor Unit Handling into the Unit Registry
* **Objective**: Replace regex parsing with strict Unit Registry lookups and automatic quantity kind mapping.
* **Actions**:
  * Implemented unit lookup, normalization, and conversion helper methods in [unit_registry_service.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/unit_registry_service.py).
  * Automated multiplier conversion (e.g., converting energy data sizes from `B` to `GB` or power from `W` to `kW` based on canonical references).

## Stage 7: Refactor Ingestion and Classification to Create Candidate Mappings
* **Objective**: Enable dynamic registry learning by creating `proposed` or `underReview` mapping entries when unknown metrics are ingested.
* **Actions**:
  * Updated [ensemble_classifier.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/classifiers/ensemble_classifier.py) to check `CimMapping` first.
  * Updated [automated_mapper.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/ingestion/automated_mapper.py) to insert candidate `CimMapping` entries when confidence is low or when a metric key is unrecognized.

## Stage 8: Add Standards Mapping Status and Confidence Scoring
* **Objective**: Integrate confidence metrics and mapping relations (`relation_type` like `exactMatch`, `closeMatch`, etc.) directly into the database.
* **Actions**:
  * Exposed confidence attributes in `CimMapping`.
  * Included rationale recording in mappings to detail classification reasoning.

## Stage 9: Add Lifecycle-Stage Linkage
* **Objective**: Connect assets and metrics to Research Infrastructure (RI) lifecycle stages.
* **Actions**:
  * Added `lifecycle_stage_id` columns to `assets` table.
  * Allowed grouping and retrieval of metrics relative to their respective stages (e.g., procurement vs operation).

## Stage 10: Add Validation Rules and Evidence Requirements
* **Objective**: Declare constraints (PUE thresholds, metric domains, percentage limits) in a rules service.
* **Actions**:
  * Implemented rule logic inside [rule_registry_service.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/rule_registry_service.py).
  * Enforced rule checks inside the automated ingestion runner, recording violations.

## Stage 11: Add Provenance Logging
* **Objective**: Map raw input streams to validated output results for end-to-end data lineage.
* **Actions**:
  * Created audit trails inside [provenance_registry_service.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/provenance_registry_service.py).
  * Integrated provenance logs inside `process_metric_sample()` to log `ingestion`, `unit_conversion`, and `classification` events.

## Stage 12: Add Extension Metric Handling
* **Objective**: Allow ingestion of metrics outside standard taxonomies using an extensible format.
* **Actions**:
  * Tagged unknown incoming metrics as `extensionMetric` relation types.
  * Saved them under the `gd.uncategorized.*` or custom namespace with proposal flags.

## Stage 13: Add Tests for All Registry Behavior
* **Objective**: Ensure coverage for all registry CRUD methods, unit conversions, rules validation, and API routes.
* **Actions**:
  * Created [test_new_services.py](file:///z:/GreenDIGIT_CIM_testing_v1/tests/test_new_services.py) and [test_registry_api.py](file:///z:/GreenDIGIT_CIM_testing_v1/tests/test_registry_api.py).
  * Resolved SQLite thread-safety configurations using `StaticPool` and `check_same_thread=False` during tests.

## Stage 14: Validate with Sample Datasets and Existing Workflows
* **Objective**: Ensure end-to-end telemetry workflows run error-free and verify UI dashboards.
* **Actions**:
  * Milestone 10: registry-driven CIM demonstrator with fixtures under `tests/fixtures/cim_demo/`, CLI `cloud_metrics.scripts.run_cim_demo`, and `tests/test_cim_end_to_end_demo.py`.
  * Refactored Streamlit Admin Dashboard and AWS/GCP ingestion scripts (prior work).
  * Executed pipeline queries on sample AWS CloudWatch and GCP datasets to verify correctness.
