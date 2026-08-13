# Legacy KPI Calculation Handling

> **Milestone 13** · What existed before the KPI Calculation Service

## Summary

Before Milestone 13 the registry-driven CIM **did not calculate** PUE, WUE, or CUE. Reportable KPI namespaces were seeded, evidence and standards were attached by lookup, and the Milestone 10 demonstrator **prepared** PUE inputs only.

Operational ingestion remained warning-based: incompatible units were flagged by the Unit Registry / orchestrator and did **not** hard-block sample storage.

## What existed

| Area | Behaviour |
|------|-----------|
| Seeded KPI metrics | `cim:energy.efficiency.pue`, `cim:energy.efficiency.wue`, `cim:energy.efficiency.cue` (`metric_type=calculated_kpi`, quantity kind `Ratio`, canonical unit `ratio`) |
| Formula on definitions | `CimMetricDefinition` has **no** formula column. Derivation is a governance field (`formula_or_derivation_method`) on orchestrator context / rules. |
| PUE in demo | `prepare_pue_context()` computes `1200/800=1.5` from fixture metadata and passes a pre-set ratio into the orchestrator for evidence/standards lookup. Not a calculation engine. |
| Evidence | Seeded mandatory ISO/IEC 30134 requirements for PUE, WUE, CUE (see [SEEDED_VALIDATION_AND_EVIDENCE_RULES.md](SEEDED_VALIDATION_AND_EVIDENCE_RULES.md)). |
| Rules | `kpi_requires_period_and_boundary` is a **warning** during orchestration, not a hard block. |
| Unit validation | Soft on ingestion: `incompatible` → warning/error metadata; mapping still resolves. |
| Standards | PUE has seeded `exactMatch` to ISO-IEC-30134 and EN-50600. WUE/CUE have **no** seeded exactMatch on the KPI namespace. Water/carbon inputs use `inputToKPI` / `contextualMatch`. |
| Provenance | Orchestrator records mapping/unit/governance events. No `kpi_calculation` activity. |
| Legacy aliases | `standards_registry.py` maps TGG-PUE / TGG-WUE aliases; no numeric calculation. |

## What was missing

- Explicit PUE = facility energy / IT energy with unit normalization
- Explicit WUE / CUE formulas
- Hard-block for reportable KPIs on incompatible units, missing period/boundary, or zero IT energy
- Provenance of the calculation itself
- Policy separating operational ingestion (soft) from reportable KPI calculation (hard)

## Non-goals retained

- No generic formula language / expression engine
- Orchestrator and ingestion paths unchanged
- Legacy fallback unchanged
