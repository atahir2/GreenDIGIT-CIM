# Unit Registry Integration

> **Milestone 5** · Wire ``cim_units`` / ``cim_quantity_kinds`` into registry-first mapping lookup

---

## Objective

Validate observed units against the Metric Registry’s expected quantity kind using
the CIM Unit Registry, and attach soft validation metadata to mapping lookup
results — without breaking ingestion or forcing hard failures on legacy callers.

---

## Services

| Component | Path |
|-----------|------|
| Unit Registry service | `cloud_metrics/registry/unit/service.py` |
| Aliases | `cloud_metrics/registry/unit/aliases.py` |
| Types | `UnitEntry`, `QuantityKindEntry`, `UnitValidationResult` |
| Legacy (unchanged) | `cloud_metrics/services/unit_registry_service.py` |

### Capabilities

* Look up units by symbol (case-insensitive) and alias
* Return canonical unit for a quantity kind
* Return quantity kind for a unit
* Validate observed unit vs expected quantity kind / metric namespace
* Convert values between units of the **same** quantity kind (CIM stack, session required)

Without a session, `list_entries()` remains empty (Milestone 1 skeleton contract).

---

## Mapping lookup integration

```python
from cloud_metrics.registry.mapping import resolve_raw_metric

result = resolve_raw_metric(
    "raw.node.power",
    session=session,
    observed_unit="kW",          # triggers validation by default
    validate_unit=None,          # None = only when observed_unit set
)
# result.resolved unchanged by unit issues
# result.unit_validation → UnitValidationResult
# result.expected_quantity_kind / result.canonical_unit
```

Flow:

1. Mapping Registry resolves CIM metric (registry-first, legacy fallback)
2. Metric definition supplies expected quantity kind + canonical unit
3. Unit Registry validates `observed_unit` (if requested)
4. Result includes `unit_validation` metadata
5. Caller still receives backward-compatible mapping fields

**Soft policy:** incompatible / unknown / missing units never flip `resolved` to
`False`. Severity is advisory (`info` / `warning` / `error`).

---

## Default vs explicit validation

| Call | Behaviour |
|------|-----------|
| No `observed_unit`, `validate_unit=None` | No unit validation (M4-compatible) |
| `observed_unit="W"` | Validate against resolved metric |
| `validate_unit=True`, no unit | Missing-unit check (or valid for Dimensionless/Count) |
| `validate_unit=False` | Never validate |

---

## What is not done

* Removing legacy `units` / `quantity_kinds` or `unit_registry_service`
* Forcing ingestion onto CIM unit validation
* Source/asset/lifecycle/provenance wiring
* Hard-blocking sample inserts on incompatible units
