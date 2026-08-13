# KPI Evidence Requirements

> **Milestone 13** · How calculation attaches seeded evidence

`KpiCalculationService` calls `EvidenceRegistryService.get_requirements_for_metric` for the KPI namespace. Requirements are attached for **calculated and blocked** results so callers can see what reporting still needs.

## Seeded (unchanged)

| KPI | Standard | Types |
|-----|----------|--------|
| `cim:energy.efficiency.pue` | ISO-IEC-30134 | calculation (mandatory), measurement (mandatory) |
| `cim:energy.efficiency.wue` | ISO-IEC-30134 | measurement (mandatory) |
| `cim:energy.efficiency.cue` | ISO-IEC-30134 | calculation (mandatory) |

PUE evidence text covers facility energy, IT energy, aggregation period, boundary, and metering source.

## Standards mappings

Attached via `StandardsRegistryService.get_mappings_for_metric` **only if seeded and the KPI definition is approved**:

- PUE: `exactMatch` ISO-IEC-30134 and EN-50600
- WUE / CUE: no seeded `exactMatch` on the KPI namespace (do not invent)

## Fulfillment

This milestone **declares** requirements; it does not store evidence artifacts or mark fulfillment complete.
