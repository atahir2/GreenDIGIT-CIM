# Registry Seed Data

> **Milestone 3** · Updated 2026-08-03  
> Controlled initial catalogues for additive ``cim_*`` tables.

---

## Summary

| Catalogue | Count | Storage |
|-----------|------:|---------|
| Quantity kinds | 10 | `cim_quantity_kinds` |
| Units | 23 | `cim_units` |
| Metrics | 20 | `cim_metric_definitions` |
| Lifecycle stages | 10 | `cim_lifecycle_stages` |
| Standards | 15 | `cim_standards` |
| Metric↔lifecycle links | 18 | `cim_metric_lifecycle_links` |
| Safe standards mappings | 13 | `cim_metric_mappings` |
| Validation rules | 8 | `cim_validation_rules` |
| Evidence requirements | 6 | `cim_evidence_requirements` |
| Bootstrap source | 1 | `cim_sources` |
| Bootstrap provenance marker | 1 | `cim_provenance_records` |

Source of truth in code:

* `cloud_metrics/registry/seed/data.py` — catalogues
* `cloud_metrics/registry/seed/loader.py` — idempotent loader (`seed_all`)
* `cloud_metrics/scripts/seed_cim_registries.py` — CLI

---

## Design rules

1. Seeds write **only** to `cim_*` tables (Milestone 2 schema).
2. Loader is **idempotent** (unique natural keys; re-run creates zero duplicates).
3. Metrics use the `cim:` namespace prefix (registry-driven), distinct from legacy `gd.*`.
4. Standards mappings are intentionally conservative (`exactMatch` only where safe).
5. Relation types are a **controlled vocabulary** in code (`RELATION_TYPES`), not a DB table.
6. Ingestion / legacy mapping / namespace generation are **not** modified.

---

## Intentionally unseeded

* Full raw-key → CIM mapping migration from `metric_mapping.json` / legacy tables
* Asset hierarchy population from `datacenters`
* Extension metrics (`cim_extension_metrics`)
* Exhaustive standard terms for every vocabulary
* Runtime dual-write from ingestion into `cim_*`

See also:

* [REGISTRY_BOOTSTRAP_PROCESS.md](REGISTRY_BOOTSTRAP_PROCESS.md)
* [SEEDED_METRIC_CATALOGUE.md](SEEDED_METRIC_CATALOGUE.md)
* [SEEDED_STANDARDS_AND_RELATIONS.md](SEEDED_STANDARDS_AND_RELATIONS.md)
* [SEEDED_VALIDATION_AND_EVIDENCE_RULES.md](SEEDED_VALIDATION_AND_EVIDENCE_RULES.md)
