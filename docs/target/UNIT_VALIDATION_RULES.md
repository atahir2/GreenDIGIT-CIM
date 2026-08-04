# Unit Validation Rules

> **Milestone 5** · Status codes, severity, and caller contract

---

## Result shape (`UnitValidationResult`)

| Field | Meaning |
|-------|---------|
| `observed_unit` | Caller-supplied unit string (may be alias) |
| `normalized_unit` | Registry symbol after alias resolution |
| `canonical_unit` | Metric or quantity-kind canonical symbol |
| `expected_quantity_kind` | From metric definition |
| `observed_quantity_kind` | From resolved unit row |
| `validation_status` | See below |
| `severity` | `info` \| `warning` \| `error` |
| `message` | Human-readable reason |
| `ok` | True for `valid` / `normalized` / `not_required` |

---

## Status codes

| Status | When | Severity |
|--------|------|----------|
| `valid` | Observed unit matches expected kind and is the canonical (or only) symbol | `info` |
| `normalized` | Observed unit is a known alias/convertible unit of the same kind | `info` |
| `missing` | No unit provided but quantity kind requires one | `warning` |
| `incompatible` | Observed unit’s kind ≠ expected kind | `error` |
| `unknown` | Symbol/alias not in Unit Registry | `warning` |
| `not_required` | No expected kind, or validation not applicable | `info` |

---

## Key cases

| Case | Status |
|------|--------|
| Known metric + valid unit | `valid` |
| Known metric + convertible/alias unit | `normalized` |
| Known metric + missing required unit | `missing` (warning) |
| Known metric + incompatible unit | `incompatible` (error) |
| Dimensionless + no unit | `valid` |
| Dimensionless + `score` / `dimensionless` | `valid` or `normalized` |
| Unknown unit | `unknown` (warning) |
| Unknown metric (unresolved mapping) | No unit validation attached; M4 unresolved/candidate behaviour preserved |

---

## Caller contract

* Validation is **metadata**. Mapping `resolved` is independent of unit status.
* Default: validate only when `observed_unit` is passed.
* Set `validate_unit=True` to also check missing units.
* Legacy ingestion is not required to call this path yet.

---

## Alias handling

Informal tokens (`watts`, `kwh`, `gb`, `percent`, …) map through
`UNIT_ALIASES` before registry lookup. See
`cloud_metrics/registry/unit/aliases.py`.
