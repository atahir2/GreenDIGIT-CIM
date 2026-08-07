# Expected Output — Scenario B (Wrong Unit)

## Input

```text
node_power_watts = 420 kWh   # Energy unit on a Power metric
```

## Expected orchestrator fields

| Field | Expected |
|-------|----------|
| `cim_namespace` | `cim:compute.node.power.draw` (mapping may still succeed) |
| `resolved` | `true` (soft validation — does not hard-block) |
| `unit_validation_status` | **`incompatible`** |
| `observed_unit` | `kWh` |
| `expected_quantity_kind` | `Power` |
| `canonical_unit` | `W` |
| `candidate_flags.unit_incompatible` | `true` |
| `warnings` | includes incompatible / unit message |
| `provenance_record_id` | set (validation issue recorded in provenance events) |

## Also in fixture

| Raw | Unit | Expected status |
|-----|------|-----------------|
| `energy_consumption` | `W` | incompatible (Energy vs Power) |
| `carbon_intensity` | `kgCO2e` | incompatible (intensity vs emission mass) |

## Non-goals

Values must **not** be silently treated as unit-valid. Ingestion is not hard-blocked in this milestone.
