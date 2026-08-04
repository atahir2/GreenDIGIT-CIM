# Legacy Unit Handling

> **Milestone 5** · Inventory of existing unit parsing, conversion, and validation  
> **Status**: Documented (legacy paths remain in place)

---

## 1. Hardcoded unit parsing

| Location | Behaviour |
|----------|-----------|
| `cloud_metrics/ingestion/unit_normalizer.py` → `extract_numeric_and_unit()` | Regex extracts `%`, `mb`/`mib`, `gb`/`gib`, `w`/`watts`. **Currently unused** by callers. |
| `cloud_metrics/ingestion/automated_mapper.py` → `_infer_unit_from_key()` | Infers lowercase unit tokens from raw key substrings (`kwh`, `wh`, `kw`, `w`, `bytes`, `gco2e`, `s`, …). |
| `cloud_metrics/parsers/unstructured_parser.py` | Matches `%`, `gb`, `w`/`watts`, `mbps`, `°c` then **discards** units (returns float only). |
| `cloud_metrics/parsers/structured_parser.py` | Numeric only; no unit extraction. |
| `cloud_metrics/classifiers/fallbacks.py` | Unit-hint nudges for namespace fallback (largely unreachable). |

---

## 2. Normalization and conversion

| Location | Stack | Role |
|----------|-------|------|
| `cloud_metrics/services/unit_registry_service.py` | Legacy `units` / `quantity_kinds` | `get_unit_by_symbol`, `get_canonical_unit`, `validate_unit_for_quantity`, `convert_value` |
| `cloud_metrics/ingestion/automated_mapper.py` | Uses legacy service | Converts sample values toward `MetricDefinition.canonical_unit_id`; failures are logged, ingestion continues |

Conversion formula: `canon = value * factor + offset`, then invert for target.

---

## 3. Database unit fields

| Model | Table | Notes |
|-------|-------|-------|
| `QuantityKind` / `Unit` | `quantity_kinds` / `units` | Legacy Antigravity stack (still used at runtime) |
| `CimQuantityKind` / `CimUnit` | `cim_quantity_kinds` / `cim_units` | Milestone 2+ additive registry (seeded in M3) |
| `MetricDefinition` | `metric_definitions` | `quantity_kind_id`, `canonical_unit_id` → legacy |
| `CimMetricDefinition` | `cim_metric_definitions` | Same FKs → `cim_*` |
| `MetricMapping.unit` | `metric_mappings` | Optional string; sparsely used |
| `CimMetricMapping` | `cim_metric_mappings` | **No** unit column |

---

## 4. Runtime validation (legacy)

`cloud_metrics/services/rule_registry_service.py` → `validate_metric_sample()`:

* Warns on missing unit
* Heuristic key checks (`energy` → Energy/Percentage, `power` → Power)
* Does **not** block sample insert

Seeded declarative rules in `cim_validation_rules` (e.g. `numeric_metric_requires_unit`, `energy_distinguishes_power_vs_energy`) are **not executed** by an engine yet.

---

## 5. Naming drift

| Legacy seed (`seed_registries.py`) | CIM seed (`registry/seed/data.py`) |
|------------------------------------|------------------------------------|
| `Percentage` | `Ratio` |
| `Temperature`, `DataRate` | Not in CIM catalogue |
| Extra units (`MWh`, `bps`, `°C`, …) | Strict 23-symbol CIM set |

Milestone 5 validation targets the **CIM** catalogue. Legacy conversion remains available for ingestion.

---

## 6. Tests assuming old behaviour

| Test | Assumption |
|------|------------|
| `tests/test_new_services.py` | Legacy `Percentage`, `convert_value`, `validate_unit_for_quantity` |
| `tests/test_registry_api.py` | Legacy Unit/QuantityKind CRUD |
| `tests/test_cim_registry_seed.py` | CIM symbol set and QK linkage |

Milestone 5 adds `tests/test_unit_registry_validation.py` without changing these fixtures.
