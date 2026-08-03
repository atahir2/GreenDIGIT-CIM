# Registry Schema Reference

> **Milestone 2** · Updated 2026-08-03  
> Column-level reference for additive ``cim_*`` tables. See also [REGISTRY_DATABASE_MODEL.md](REGISTRY_DATABASE_MODEL.md).

---

## Common governance fields

Present on every table below unless noted:

`status`, `review_status`, `confidence_score`, `version`, `created_at`, `updated_at`, `created_by`, `notes`

---

## `cim_quantity_kinds`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `name` | VARCHAR(128) | UNIQUE `uq_cim_quantity_kinds_name` |
| `description` | VARCHAR(512) | |
| `qudt_uri` | VARCHAR(256) | |

## `cim_units`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `symbol` | VARCHAR(64) | UNIQUE `uq_cim_units_symbol` |
| `name` | VARCHAR(128) | |
| `quantity_kind_id` | INTEGER | FK → `cim_quantity_kinds.id` |
| `si_base` | BOOLEAN | default false |
| `canonical_unit_id` | INTEGER | FK → `cim_units.id` |
| `conversion_factor` | FLOAT | default 1.0 |
| `conversion_offset` | FLOAT | default 0.0 |
| `qudt_uri` / `saref_uri` | VARCHAR(256) | |

## `cim_sources`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `name` | VARCHAR(128) | UNIQUE with `type` |
| `type` | VARCHAR(64) | UNIQUE with `name` (`uq_cim_sources_name_type`) |
| `protocol` / `format` / `schema_version` | VARCHAR(64) | |
| `capabilities` / `metadata_info` | JSON | |
| `auth_method` | VARCHAR(64) | default `none` |

## `cim_assets`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `identifier` | VARCHAR(255) | UNIQUE with `type` |
| `name` | VARCHAR(128) | indexed |
| `type` | VARCHAR(64) | UNIQUE with `identifier` |
| `parent_id` | INTEGER | FK → `cim_assets.id` |
| `location` / `provider` | VARCHAR | |
| `specifications` | JSON | |
| `lifecycle_stage_id` | INTEGER | FK → `cim_lifecycle_stages.id` |

## `cim_standards`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `code` | VARCHAR(128) | UNIQUE with `standard_version` |
| `name` | VARCHAR(255) | UNIQUE with `standard_version` |
| `standard_version` | VARCHAR(64) | External published version string |
| `url` / `description` | | |
| `vocabulary_type` / `namespace_prefix` / `namespace_uri` / `domain` | VARCHAR | |

> Note: mixin `version` (INTEGER) is the **registry row** version; `standard_version` is the **external standard** release label.

## `cim_standard_terms`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `standard_id` | INTEGER | FK → `cim_standards.id` ON DELETE CASCADE |
| `term_code` | VARCHAR(128) | UNIQUE with `standard_id` |
| `term_label` / `term_uri` / `description` | | |

## `cim_metric_definitions`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `namespace` | VARCHAR(255) | UNIQUE `uq_cim_metric_definitions_namespace` |
| `label` / `description` | | |
| `domain` / `category` / `subcategory` | VARCHAR | |
| `quantity_kind_id` | INTEGER | FK → `cim_quantity_kinds.id` |
| `canonical_unit_id` | INTEGER | FK → `cim_units.id` |
| `metric_type` | VARCHAR(64) | observed / calculated / derived / … |
| `tags` / `sources` | JSON | |

## `cim_metric_mappings`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `source_key` | VARCHAR(255) | UNIQUE with `source_id` |
| `source_id` | INTEGER | FK → `cim_sources.id` (nullable) |
| `metric_id` | INTEGER | FK → `cim_metric_definitions.id` |
| `standard_id` | INTEGER | FK → `cim_standards.id` |
| `standard_term_id` | INTEGER | FK → `cim_standard_terms.id` |
| `relation_type` | VARCHAR(64) | default `underReview` |
| `rationale` / `origin` | | |
| `approved_by` / `approved_at` | | |

## `cim_lifecycle_stages`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `name` | VARCHAR(128) | UNIQUE |
| `stage_key` | VARCHAR(64) | UNIQUE |
| `label` / `description` | | |
| `sequence` | INTEGER | indexed |

## `cim_metric_lifecycle_links`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `metric_id` | INTEGER | FK → metrics ON DELETE CASCADE |
| `lifecycle_stage_id` | INTEGER | FK → stages ON DELETE CASCADE |
| `relevance` | VARCHAR(64) | default `primary` |
| | | UNIQUE (`metric_id`, `lifecycle_stage_id`) |

## `cim_validation_rules`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `name` | VARCHAR(128) | UNIQUE |
| `description` | TEXT | |
| `rule_type` | VARCHAR(64) | required_field / range_check / … |
| `target_registry` | VARCHAR(64) | |
| `condition` | JSON | |
| `severity` | VARCHAR(32) | default `error` |

## `cim_evidence_requirements`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `standard_id` | INTEGER | FK → `cim_standards.id` |
| `metric_id` | INTEGER | FK → `cim_metric_definitions.id` |
| `evidence_type` | VARCHAR(64) | |
| `requirement_level` | VARCHAR(64) | default `recommended` |
| `reporting_period` / `aggregation_method` / `boundary` / `description` | | |
| | | UNIQUE (`standard_id`, `metric_id`, `evidence_type`) |

## `cim_provenance_records`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `entity_type` / `entity_id` | | indexed together |
| `activity` | VARCHAR(64) | ingestion / mapping / unit_conversion / … |
| `agent` | VARCHAR(128) | |
| `started_at` / `ended_at` | TIMESTAMPTZ | |
| `inputs` / `outputs` | JSON | |
| `method` / `prov_uri` | | |

## `cim_extension_metrics`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `metric_id` | INTEGER | FK → metrics ON DELETE CASCADE; UNIQUE |
| `proposed_standard` / `justification` | | |
| `proposed_by` / `proposed_at` / `reviewed_at` | | |

---

## Status / review vocabulary (recommended)

| Field | Suggested values |
|-------|------------------|
| `status` | `draft`, `candidate`, `approved`, `rejected`, `deprecated`, `retired`, `active` |
| `review_status` | `pending`, `under_review`, `approved`, `rejected` |
| Mapping `relation_type` | `exactMatch`, `closeMatch`, `broadMatch`, `narrowMatch`, `inputToKPI`, `derivedFrom`, `contextualMatch`, `extensionMetric`, `noMatch`, `underReview` |
| Mapping `origin` | `manual`, `auto-learned`, `seeded`, `imported` |
