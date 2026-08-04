# Power / Energy Validation Policy

> **Milestone 5** · Explicit separation of Power vs Energy (and related kinds)

---

## Why this matters

Telemetry pipelines historically confuse instantaneous power and cumulative
energy (e.g. reporting `kWh` on a power metric, or `W` on energy totals).
Silent acceptance produces incorrect KPIs (PUE inputs, carbon intensity, etc.).

---

## Policy

| Expected kind | Compatible units | Incompatible examples |
|---------------|------------------|------------------------|
| **Power** | `W`, `kW` (aliases: `watt`, `watts`, `kw`, …) | `Wh`, `kWh`, `J` |
| **Energy** | `Wh`, `kWh`, `J` | `W`, `kW` |
| **CarbonEmission** | `kgCO2e`, `gCO2e` | Power/Energy units |
| **CarbonIntensity** | `gCO2e/kWh` | Bare `gCO2e` or `kWh` alone |
| **Time** | `s`, `ms`, `h` | — |
| **DataSize** | `B`…`TB` | Data-rate units (not in CIM seed) |
| **WaterVolume** | `L`, `m3` | — |

---

## Severity

* **Incompatible Power ↔ Energy:** `validation_status=incompatible`, `severity=error`
* Callers **may** reject or quarantine samples, but Milestone 5 does **not**
  hard-fail ingestion automatically.
* Mapping lookup remains successful (`resolved=True`) with error metadata so
  UIs / later pipeline stages can enforce policy safely.

---

## Examples

```text
cim:compute.node.power.draw + W     → valid
cim:compute.node.power.draw + kW    → normalized (canonical W)
cim:compute.node.power.draw + kWh   → incompatible (error)
cim:energy.consumption.total + kWh  → valid
cim:energy.consumption.total + W    → incompatible (error)
```

---

## Out of scope (this milestone)

* Automatic conversion of incompatible kinds (never)
* Blocking inserts in `process_metric_sample`
* Expanding CIM seed with DataRate / Temperature units
