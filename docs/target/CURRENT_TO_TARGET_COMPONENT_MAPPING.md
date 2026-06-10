# Current-to-Target Component Mapping

> **Generated**: 2026-06-10 · **Scope**: Per-component disposition analysis

---

## Classification Key

| Disposition | Meaning |
|-------------|---------|
| **Reuse as-is** | Component works correctly and fits target design without changes |
| **Refactor** | Component has the right intent but needs internal restructuring |
| **Move** | Component needs relocation to a different module/package |
| **Extend** | Component is a good foundation but needs additional fields/capabilities |
| **Replace** | Component's approach is fundamentally wrong for the target; replace with new implementation |
| **Remove** | Component is dead code, duplicated, or no longer needed |
| **Create new** | No current component exists; must be built from scratch |

---

## 1. Models (Database Layer)

| Current Component | File | Target Registry | Disposition | Rationale |
|-------------------|------|----------------|-------------|-----------|
| `MetricDefinition` | [metric_definition.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/metric_definition.py) | Metric Registry | **Extend** | Good foundation. Add: label, description, domain, quantity_kind, canonical_unit, metric_type, status, version, updated_at |
| `Category` | [namespace_models.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/namespace_models.py) | Metric Registry | **Refactor** | Keep concept but merge into Metric Registry as a field. Remove FK to `standards` (standards linkage moves to Mapping Registry) |
| `Subcategory` | [namespace_models.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/namespace_models.py) | Metric Registry | **Refactor** | Same — merge into Metric Registry as a field |
| `Standard` | [standard_models.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/standard_models.py) | Standards Registry | **Extend** | Add: vocabulary_type, namespace_prefix, namespace_uri, version, domain, status. Add missing standards (SAREF, QUDT, PROV-O, etc.) |
| `MetricStandardMap` | [standard_models.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/standard_models.py) | Mapping Registry | **Move + Extend** | Move to Mapping Registry. Add: relation_type (exactMatch, broadMatch, etc.), approved_by, status |
| `MetricSample` | [metric_sample.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/metric_sample.py) | Metric Registry + Provenance | **Refactor** | Keep as observation store. Move ri_id/node_id/vm_id/host to Asset Registry FK. Move clf_confidence/clf_rationale to Provenance Registry |
| `MetricKeyword` | [metric_keyword.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/metric_keyword.py) | Mapping Registry | **Move + Refactor** | Merge into Mapping Registry as a source→CIM mapping entry with `relation_type=exactMatch` and origin='auto-learned' |
| `MetricMapping` | [metric_mapping.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/metric_mapping.py) | Mapping Registry | **Replace** | Correct concept but unused. Replace with full Mapping Registry model including relation_type, source_id, standard_id |
| `MappingProposal` | [metric_mapping.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/metric_mapping.py) | Mapping Registry | **Replace** | Merge proposal workflow into Mapping Registry with status field (proposed→approved→rejected) |
| `MappingEvent` | [metric_mapping.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/metric_mapping.py) | Provenance Registry | **Move + Extend** | Correct concept, wrong location. Move to Provenance Registry with PROV-O alignment |
| `MetricSourceMap` | [metric_source_map.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/metric_source_map.py) | Mapping Registry | **Move + Refactor** | Merge into Mapping Registry. Add source_id FK instead of datacenter_id |
| `Datacenter` | [datacenter.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/datacenter.py) | Asset Registry | **Move + Extend** | Becomes one asset_type in the Asset Registry hierarchy. Add type, parent_id, specifications, lifecycle_stage, status |
| `FileUploadLog` | [upload_log.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/upload_log.py) | Provenance Registry | **Move** | Becomes a provenance record with activity='ingestion' |
| `Base` | [db_models.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/db_models.py) | — | **Refactor** | Update to `DeclarativeBase` (SQLAlchemy 2.0 style) |
| *(new)* | — | Unit Registry | **Create new** | Complete new model: units, quantity_kinds, conversion rules |
| *(new)* | — | Lifecycle Registry | **Create new** | Complete new model: stages, metric-stage links, asset-stage links |
| *(new)* | — | Rule Registry | **Create new** | Complete new model: rules, conditions, severities |
| *(new)* | — | Evidence Registry | **Create new** | Complete new model: evidence types, reporting requirements |
| *(new)* | — | Extension Registry | **Create new** | Complete new model: proposed extensions, justifications |

---

## 2. Classifiers

| Current Component | File | Target Role | Disposition | Rationale |
|-------------------|------|-------------|-------------|-----------|
| `ensemble_classifier.py` | [ensemble_classifier.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/classifiers/ensemble_classifier.py) | Classification Service | **Refactor** | Good architecture. Refactor to: (1) query Mapping Registry first, (2) fall back to fuzzy/embedding, (3) output relation_type along with classification |
| `alias_classifier.py` | [alias_classifier.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/classifiers/alias_classifier.py) | Mapping Registry seed data | **Move** | The ~80 aliases should be migrated to Mapping Registry rows with relation_type=exactMatch/closeMatch. Fuzzy matching logic stays as a classification service |
| `semantic_classifier.py` | [semantic_classifier.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/ingestion/semantic_classifier.py) | Mapping Registry seed data | **Move** | The 10 STANDARDS_MAP entries become Mapping Registry rows. The lookup logic merges into the unified classifier |
| `fallbacks.py` | [fallbacks.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/classifiers/fallbacks.py) | Classification Service | **Replace** | Dead code after line 19. Replace with proper fallback that outputs relation_type=noMatch or underReview |

---

## 3. Ingestion Pipeline

| Current Component | File | Target Role | Disposition | Rationale |
|-------------------|------|-------------|-------------|-----------|
| `automated_mapper.py` | [automated_mapper.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/ingestion/automated_mapper.py) | Ingestion Service (orchestrator) | **Refactor** | Remove duplicate `_classify_to_parts()`. Restructure `process_metric_sample()` to: (1) resolve source via Source Registry, (2) classify via Mapping Registry → Classification Service, (3) normalize via Unit Registry, (4) validate via Rule Registry, (5) persist with Provenance |
| `unified_ingestion.py` | [unified_ingestion.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/ingestion/unified_ingestion.py) | Ingestion Service | **Refactor** | Remove hardcoded datacenter_id=1. Use Source Registry for source resolution. Keep file-based ingestion flow |
| `realtime_ingestor.py` | [realtime_ingestor.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/ingestion/realtime_ingestor.py) | Ingestion Service | **Refactor** | Same fixes as unified_ingestion. Add Source Registry resolution |
| `decision.py` | [decision.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/ingestion/decision.py) | Classification Service | **Extend** | Add relation_type field to MappingDecision |
| `unit_normalizer.py` | [unit_normalizer.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/ingestion/unit_normalizer.py) | Unit Registry Service | **Refactor** | Replace regex-only extraction with Unit Registry lookup + conversion |
| `aws.py` | [aws.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/ingestion/aws.py) | Source Registry entry | **Replace** | Stub. Replace with proper AWS CloudWatch source connector registered in Source Registry |
| `gcp.py` | [gcp.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/ingestion/gcp.py) | Source Registry entry | **Replace** | Stub. Replace with proper GCP Monitoring source connector registered in Source Registry |

---

## 4. Parsers

| Current Component | File | Target Role | Disposition | Rationale |
|-------------------|------|-------------|-------------|-----------|
| `structured_parser.py` | [structured_parser.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/parsers/structured_parser.py) | Parser Service | **Reuse as-is** | Solid multi-format parser. Works well for JSON/YAML/XML/CSV |
| `unstructured_parser.py` | [unstructured_parser.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/parsers/unstructured_parser.py) | Parser Service | **Reuse as-is** | Simple regex extraction. Limited but functional for PoC |
| `ingest_any.py` | [ingest_any.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/utils/ingest_any.py) | Ingestion Service | **Refactor** | Good universal loader. Refactor PartnerMeta to use Asset Registry + Source Registry. Consolidate with other PartnerMeta classes |
| `partner_payload.py` | [partner_payload.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/utils/partner_payload.py) | Parser Service | **Refactor** | Merge PartnerMeta into single class. Keep parsing logic |
| `metadata.py` | [metadata.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/utils/metadata.py) | Parser Service | **Remove** | Superseded by `ingest_any.py`. IngestMeta duplicates PartnerMeta |

---

## 5. Registry / Namespace

| Current Component | File | Target Role | Disposition | Rationale |
|-------------------|------|-------------|-------------|-----------|
| `namespace_registry.py` | [namespace_registry.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/registry/namespace_registry.py) | Metric Registry Service | **Refactor** | `ensure_gd_namespace()` — refactor to validate against Metric Registry instead of just creating taxonomy rows |
| `mapping_registry.py` | [mapping_registry.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/registry/mapping_registry.py) | Mapping Registry Service | **Refactor** | `register_mapping()` — refactor to write Mapping Registry entries with relation_type and provenance |
| `namespace_generator.py` | [namespace_generator.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/namespace_generator.py) | — | **Remove** | Superseded by `namespace_registry.py`. Legacy code with alias maps that belong in Mapping Registry |

---

## 6. Services

| Current Component | File | Target Role | Disposition | Rationale |
|-------------------|------|-------------|-------------|-----------|
| `influx_service.py` | [influx_service.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/influx_service.py) | Time-Series Service | **Reuse as-is** | Solid InfluxDB client. No changes needed |
| `insert_datacenter.py` | [insert_datacenter.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/insert_datacenter.py) | Asset Registry Service | **Move + Extend** | Becomes `create_asset()` in Asset Registry service |
| `insert_mapped_metric.py` | [insert_mapped_metric.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/insert_mapped_metric.py) | Metric Registry Service | **Refactor** | Good upsert logic. Refactor to use Metric Registry model directly. Remove JSON sync (handled by Mapping Registry) |
| `insert_metric_definition.py` | [insert_metric_definition.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/insert_metric_definition.py) | — | **Remove** | Simple insert without upsert. Superseded by `insert_mapped_metric.py` |
| `insert_metric_sample.py` | [insert_metric_sample.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/insert_metric_sample.py) | Observation Service | **Refactor** | Remove duplicate MetricSourceMap upsert. Add asset_id FK instead of inline metadata fields. Add Provenance write |
| `insert_file_upload_log.py` | [insert_file_upload_log.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/insert_file_upload_log.py) | Provenance Registry Service | **Move** | Becomes a provenance record creation |
| `keyword_learning.py` | [keyword_learning.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/keyword_learning.py) | Mapping Registry Service | **Move + Refactor** | Learning logic moves to Mapping Registry service. Creates mapping entries with relation_type and auto-learned flag |
| `registry_service.py` | [registry_service.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/registry_service.py) | Mapping Registry Service | **Refactor** | `resolve_unified_key()` queries Mapping Registry instead of unused `metric_mappings` table |
| `standards_registry.py` | [standards_registry.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/standards_registry.py) | Standards Registry Service | **Extend** | Good seed data + rule-based linking. Extend seed with missing standards. Move linkage rules to Mapping Registry |

---

## 7. Exporters

| Current Component | File | Target Role | Disposition | Rationale |
|-------------------|------|-------------|-------------|-----------|
| `external_json.py` | [external_json.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/exporters/external_json.py) | Export Service | **Refactor** | Add support for RDF/Linked Data export, CSV export. Use Metric Registry for label lookup. Use Standards Registry for annotation |
| `rebuild_mapping_json.py` | [rebuild_mapping_json.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/exporters/rebuild_mapping_json.py) | Mapping Registry export | **Refactor** | Source from Mapping Registry instead of MetricSourceMap/MetricKeyword. Single source of truth |

---

## 8. Utilities

| Current Component | File | Target Role | Disposition | Rationale |
|-------------------|------|-------------|-------------|-----------|
| `config.py` | [config.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/utils/config.py) | Configuration | **Reuse as-is** | Solid pydantic-settings config. No changes needed |
| `unified_key.py` | [unified_key.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/utils/unified_key.py) | Metric Registry utility | **Reuse as-is** | `to_gd()` normalization is still needed |
| `mapping_sync.py` | [mapping_sync.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/utils/mapping_sync.py) | — | **Remove** | JSON file sync is replaced by Mapping Registry as single source of truth |
| `debug_config.py` | [debug_config.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/utils/debug_config.py) | — | **Reuse as-is** | Dev utility, no change needed |

---

## 9. API Layer

| Current Component | File | Target Role | Disposition | Rationale |
|-------------------|------|-------------|-------------|-----------|
| `metrics.py` | [metrics.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/api/metrics.py) | Ingestion API | **Replace** | Stub endpoints. Replace with proper ingestion API that accepts multi-format payloads, resolves via Source Registry |
| `query.py` | [query.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/api/query.py) | Query API | **Extend** | Add: query by asset, filter by standard, filter by lifecycle stage, pagination |
| `main.py` | [main.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/main.py) | Application | **Extend** | Add new registry API routers, registry admin endpoints |
| *(new)* | — | Registry CRUD API | **Create new** | REST endpoints for all 11 registries: CRUD + search + bulk operations |

---

## 10. Scripts & UI

| Current Component | File | Target Role | Disposition | Rationale |
|-------------------|------|-------------|-------------|-----------|
| `streamlit_uploader.py` | [streamlit_uploader.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/scripts/streamlit_uploader.py) | Ingestion UI | **Refactor** | Remove ~270 lines of commented-out code. Integrate Source Registry + Asset Registry selection |
| `admin_panel.py` | [admin_panel.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/scripts/admin_panel.py) | Admin UI | **Extend** | Add registry management views, evidence tracking, lifecycle stage assignment |
| `seed_namespace.py` | [seed_namespace.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/scripts/seed_namespace.py) | Seed script | **Refactor** | Merge into unified seed script that populates all registries |
| `seed_taxonomy_standards.py` | [seed_taxonomy_standards.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/scripts/seed_taxonomy_standards.py) | Seed script | **Refactor** | Merge into unified seed script |
| `backfill_standards.py` | [backfill_standards.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/scripts/backfill_standards.py) | Migration script | **Remove** | One-time migration. Replace with proper Alembic migration |
| `create_schema.py` | [create_schema.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/scripts/create_schema.py) | Schema management | **Replace** | Replace with Alembic migrations |
| `rebuild_mapping_json.py` (script) | [rebuild_mapping_json.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/scripts/rebuild_mapping_json.py) | Export script | **Refactor** | Source from Mapping Registry |

---

## 11. Tests

| Current Component | File | Target Role | Disposition | Rationale |
|-------------------|------|-------------|-------------|-----------|
| `test_api_endpoints.py` | [test_api_endpoints.py](file:///z:/GreenDIGIT_CIM_testing_v1/tests/test_api_endpoints.py) | API tests | **Refactor** | Update for new API structure |
| `test_influx_service.py` | [test_influx_service.py](file:///z:/GreenDIGIT_CIM_testing_v1/tests/test_influx_service.py) | Service tests | **Reuse as-is** | Solid test, no changes |
| `test_namespace_mapper.py` | [test_namespace_mapper.py](file:///z:/GreenDIGIT_CIM_testing_v1/tests/test_namespace_mapper.py) | Mapping tests | **Replace** | Broken — expects old keys. Replace with Mapping Registry tests |
| `test_sql_service.py` | [test_sql_service.py](file:///z:/GreenDIGIT_CIM_testing_v1/tests/test_sql_service.py) | Service tests | **Replace** | Broken — imports nonexistent module. Replace with registry service tests |

---

## 12. Disposition Summary

| Disposition | Count | Components |
|-------------|-------|------------|
| **Reuse as-is** | 7 | structured_parser, unstructured_parser, influx_service, config, unified_key, debug_config, test_influx |
| **Refactor** | 18 | MetricDefinition, Category, Subcategory, ensemble_classifier, automated_mapper, unified_ingestion, realtime_ingestor, ingest_any, partner_payload, namespace_registry, mapping_registry, insert_mapped_metric, insert_metric_sample, registry_service, external_json, rebuild_mapping_json, streamlit_uploader, test_api |
| **Move** | 5 | MetricStandardMap, MetricKeyword, insert_datacenter, insert_file_upload_log, keyword_learning |
| **Move + Extend** | 2 | MappingEvent, Datacenter |
| **Extend** | 5 | Standard, decision.py, standards_registry, query.py, admin_panel |
| **Replace** | 7 | MetricMapping, MappingProposal, fallbacks.py, aws.py, gcp.py, metrics.py (API), test_sql, test_namespace |
| **Remove** | 5 | namespace_generator, insert_metric_definition, metadata.py, mapping_sync.py, backfill_standards |
| **Create new** | 8 | Unit Registry, Source Registry, Asset Registry, Lifecycle Registry, Rule Registry, Evidence Registry, Extension Registry, Registry CRUD API |
