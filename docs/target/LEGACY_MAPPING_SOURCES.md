# Legacy Mapping Sources

> **Milestone 4** · Inventory of existing raw→unified metric mapping sources  
> **Status**: Documented (sources themselves remain in place)

This document lists every known place where the current system maps a raw
telemetry / metric key to a unified ``gd.*`` namespace. Milestone 4 migrates
these into ``cim_metric_mappings`` (linked to ``cim_metric_definitions``)
without deleting or renaming the legacy sources.

---

## 1. File-based JSON maps

| Source | Path | Format | Approx. size | Runtime use |
|--------|------|--------|-------------:|-------------|
| Runtime mapping JSON | `cloud_metrics/mapping/metric_mapping.json` | `{ "gd.…": ["raw1", …] }` | ~25 unified keys, ~115 raw entries (includes noise); **22** unique raw keys retained after noise/dedupe | `map_raw_to_unified()`, `sync_metric_mapping()` |
| Export mapping JSON | `cloud_metrics/data/metric_mapping.json` | `{ mappings: { raw → {unified_key, last_seen} } }` | ~30 raw→unified pairs; **14** unique retained after dedupe | Rebuild/export via `exporters/rebuild_mapping_json.py` |

**Notes**

* The runtime JSON mixes real metric keys with site / placeholder noise
  (``datacenter_A``, ``30``, ``q``, ``ifca``, …). Migration filters these via
  `NOISE_RAW_KEYS` in `registry/migration/legacy_sources.py`.
* ``gd.uncategorized.unknown.unknown`` catch-all entries are skipped during
  migration (not trustworthy alignments).

---

## 2. Hardcoded dictionaries

| Source | Path | Content | Approx. size |
|--------|------|---------|-------------:|
| Alias classifier | `cloud_metrics/classifiers/alias_classifier.py` → `ALIASES` | `(category, subcategory, short) → [alias, …]` | 27 triples, ~111 alias strings; **92** unique after dedupe |
| Semantic classifier | `cloud_metrics/ingestion/semantic_classifier.py` → `STANDARDS_MAP` | suffix → `(org, domain, category, metric)` | 10 suffixes; **4** unique after dedupe |
| Taxonomy alias seeds | `cloud_metrics/scripts/seed_taxonomy_standards.py` → `ALIAS_SEEDS` | raw → ``gd.*`` | 20 pairs; **19** unique after dedupe |
| Category/subcategory aliases | `cloud_metrics/services/namespace_generator.py` | `CATEGORY_ALIASES`, `SUBCATEGORY_ALIASES` | ~13 groups (taxonomy only; not raw→metric) |

---

## 3. Namespace generation utilities

| Utility | Path | Role |
|---------|------|------|
| `ensure_gd_namespace()` | `cloud_metrics/registry/namespace_registry.py` | Ensures Category/Subcategory + ``gd.*`` key |
| `generate_namespace()` | `cloud_metrics/services/namespace_generator.py` | DB-driven namespace with alias support |
| `fallback_namespace_from_raw()` | `cloud_metrics/classifiers/fallbacks.py` | Last-resort ``gd.uncategorized.*`` |
| `map_raw_to_unified()` | `cloud_metrics/mapping/namespace_mapper.py` | Exact scan of mapping JSON |

These remain the runtime path for ingestion. Milestone 4 does **not** replace them.

---

## 4. Classifier output mappings

| Classifier | Path | Mapping behaviour |
|------------|------|-------------------|
| Ensemble | `cloud_metrics/classifiers/ensemble_classifier.py` | Priority 0: legacy `resolve_mapping()` on `CimMapping`; then semantic → alias → rules → embed |
| Automated mapper | `cloud_metrics/ingestion/automated_mapper.py` | Classification + `sync_metric_mapping()` + learn/register helpers |

Classifier output still writes legacy stores. Registry-first lookup is available
opt-in via `resolve_raw_metric()` / `MappingRegistryService`.

---

## 5. SQL / database-backed legacy mappings

| Table / model | Path | Status |
|---------------|------|--------|
| `cim_mappings` / `CimMapping` | `cloud_metrics/models/cim_mapping.py` | **Active** runtime mapping registry (Antigravity) |
| `metric_mappings` / `MetricMapping` | `cloud_metrics/models/metric_mapping.py` | Present; sparsely used |
| `metric_definitions` / `MetricDefinition` | `cloud_metrics/models/metric_definition.py` | Active ``gd.*`` definitions; `sources` JSON |
| `metric_keywords` / `metric_source_map` | Dropped in Alembic `a7708d6bee50` | Historical only |

**Target tables (Milestone 2+):**

| Table | Model |
|-------|-------|
| `cim_metric_definitions` | `CimMetricDefinition` |
| `cim_metric_mappings` | `CimMetricMapping` |

---

## 6. Test fixtures that assume old mapping behaviour

| Test | Assumption |
|------|------------|
| `tests/test_namespace_mapper.py` | `alpha.cpu` → `gd.performance.cpu.utilization`; `alpha.mem` → `gd.performance.memory.usage` |
| `tests/test_new_services.py` | Legacy `create_mapping` / `resolve_mapping` on `CimMapping` |
| `tests/test_registry_api.py` | `/mappings` propose/approve against `CimMapping` |
| `tests/test_registry_skeleton.py` | Mapping service without session still returns empty |

Milestone 4 adds `tests/test_mapping_registry_migration.py` and leaves the above fixtures unchanged.

---

## 7. Discovery entry point

```python
from cloud_metrics.registry.migration import discover_legacy_mappings

report = discover_legacy_mappings()
# report.records, report.by_source, report.skipped_noise, ...
```

CLI dry-run:

```bash
python -m cloud_metrics.scripts.migrate_legacy_mappings --dry-run -v
```

### Typical discovery totals (Milestone 4 baseline)

| Metric | Count |
|--------|------:|
| Unique raw keys after dedupe | **151** |
| Noise keys skipped | 68 |
| Uncategorized catch-all skipped | 13 |