# PUE / WUE / CUE Calculation Model

> **Milestone 13**

Aligned with ISO/IEC 30134 family practice and this project's seeded namespaces.

## Namespaces

| KPI | Namespace | Seeded metric type |
|-----|-----------|-------------------|
| PUE | `cim:energy.efficiency.pue` | `calculated_kpi` / Ratio / `ratio` |
| WUE | `cim:energy.efficiency.wue` | `calculated_kpi` / Ratio / `ratio` |
| CUE | `cim:energy.efficiency.cue` | `calculated_kpi` / Ratio / `ratio` |

Seeded catalogue uses `Ratio` as the KPI type. Calculated **result units** for WUE/CUE are the ISO-style derived units below (not silently stored as a dimensionless 0–1 ratio).

## Formulas

### PUE

```text
PUE = E_facility / E_IT
```

- Numerator: `cim:facility.energy.consumption.total` (Energy)
- Denominator: `cim:facility.it.energy.consumption` (Energy)
- Compatible energy units are converted to **kWh** before division
- Result unit: `ratio` (dimensionless). PUE < 1.0 emits a warning (boundary check)

### WUE

```text
WUE = V_water / E_IT
```

- Numerator: `cim:water.usage.total` (WaterVolume → **L**)
- Denominator: IT equipment energy → **kWh**
- Result unit: **L/kWh** (ISO/IEC 30134-3 convention)

### CUE

```text
CUE = M_CO2e / E_IT
```

- Preferred numerator: `cim:carbon.emission.operational` (CarbonEmission → **kgCO2e**)
- Alternate: `carbon_kind=intensity` with `cim:carbon.intensity.location_based` (`gCO2e/kWh` → kgCO2e/kWh)
- Denominator: IT equipment energy → **kWh**
- Result unit: **kgCO2e/kWh** (ISO/IEC 30134-8 convention)

## Denominator convention

All three KPIs use **IT equipment energy** as the denominator. This matches seeded PUE notes and ISO 30134 practice. There is no alternate denominator in this milestone.

## Normalization

Unit Registry `validate_observed_unit` + `convert_value` against quantity kind. Compatible units (`Wh`→`kWh`, `m3`→`L`, `gCO2e`→`kgCO2e`) are accepted. Power units on energy inputs are **incompatible**.
