# Quantity Kind Model

> **Milestone 5** · CIM quantity kinds and their unit families

Canonical catalogue lives in `cloud_metrics/registry/seed/data.py`
(`QUANTITY_KINDS`, `UNITS`) and is loaded into `cim_quantity_kinds` /
`cim_units`.

---

## Quantity kinds

| Name | Description | Canonical unit | Member units |
|------|-------------|----------------|--------------|
| `Power` | Instantaneous / average power | `W` | `W`, `kW` |
| `Energy` | Energy over a period | `kWh` | `Wh`, `kWh`, `J` |
| `CarbonEmission` | GHG as CO₂e mass | `kgCO2e` | `kgCO2e`, `gCO2e` |
| `CarbonIntensity` | Emission factor per energy | `gCO2e/kWh` | `gCO2e/kWh` |
| `Time` | Duration | `s` | `s`, `ms`, `h` |
| `DataSize` | Information size | `B` | `B`, `KB`, `MB`, `GB`, `TB` |
| `Ratio` | Ratio / percentage | `%` | `%`, `ratio` |
| `Dimensionless` | Unitless score / factor | `dimensionless` | `score`, `dimensionless` |
| `WaterVolume` | Water volume | `L` | `L`, `m3` |
| `Count` | Discrete count | `count` | `count` |

---

## Compatibility rules

* Units are compatible **iff** they share the same quantity kind.
* Cross-kind combinations are **incompatible** (e.g. Power metric + `kWh`).
* `Dimensionless` and `Count` allow missing observed units.
* Other kinds expect a unit when validation is requested.

---

## Relationship to metrics

`CimMetricDefinition.quantity_kind_id` and `canonical_unit_id` declare the
expected kind and preferred reporting unit. Examples:

| Metric namespace | Quantity kind | Canonical |
|-----------------|---------------|-----------|
| `cim:compute.node.power.draw` | Power | `W` |
| `cim:energy.consumption.total` | Energy | `kWh` |
| `cim:carbon.emission.operational` | CarbonEmission | `kgCO2e` |
| `cim:carbon.intensity.location_based` | CarbonIntensity | `gCO2e/kWh` |
| `cim:workflow.execution.duration` | Time | `s` |
| `cim:compute.memory.usage` | DataSize | `B` |
| `cim:water.usage.total` | WaterVolume | `L` |
| `cim:energy.efficiency.pue` | Ratio | `ratio` |

---

## Legacy note

The older `Percentage` / `Temperature` / `DataRate` kinds in
`seed_registries.py` are **not** part of this model. Mapping-flow validation
uses the CIM names above only.
