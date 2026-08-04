# Seeded Standards and Relations

> **Milestone 3** · Standards catalogue + conservative metric↔standard mappings

---

## Seeded standards (`cim_standards`)

| Code (short_name) | Name | Domain / scope |
|-------------------|------|----------------|
| QUDT | Quantities, Units, Dimensions and Types | units |
| SOSA-SSN | SOSA/SSN | observations |
| SAREF | Smart Applications REFerence ontology | iot |
| SCHEMA-ORG | schema.org | web |
| PROV-O | PROV Ontology | provenance |
| DCAT | Data Catalog Vocabulary | data |
| RO-CRATE | Research Object Crate | research |
| OTEL | OpenTelemetry | observability |
| ISO-IEC-30134 | ISO/IEC 30134 Data centre KPIs | datacentre |
| EN-50600 | EN 50600 Data centre facilities and infrastructures | datacentre |
| OCP | Open Compute Project | hardware |
| ISO-14040-14044 | ISO 14040/14044 Life Cycle Assessment | environment |
| ISO-50001 | ISO 50001 Energy management systems | energy |
| ISO-14001 | ISO 14001 Environmental management systems | environment |
| EU-COC-DC | EU Code of Conduct for Data Centres | datacentre |

All seeded with `status=approved`, `review_status=approved`.

---

## Relation type vocabulary

Stored as strings on `cim_metric_mappings.relation_type` (no dedicated table).

Approved values (`cloud_metrics.registry.seed.RELATION_TYPES`):

* `exactMatch`
* `closeMatch`
* `broadMatch`
* `narrowMatch`
* `inputToKPI`
* `derivedFrom`
* `contextualMatch`
* `extensionMetric`
* `noMatch`
* `underReview`

---

## Safe initial standards mappings

Synthetic bootstrap source: `cim_registry_bootstrap` (`type=manual`).  
`source_key` pattern: `std:<CODE>:<suffix>:<metric_namespace>`.

| Metric | Standard | Relation | Notes |
|--------|----------|----------|-------|
| `cim:energy.efficiency.pue` | ISO-IEC-30134 | exactMatch | PUE in 30134-2 |
| `cim:energy.efficiency.pue` | EN-50600 | exactMatch | DC PUE practice alignment |
| `cim:compute.node.power.draw` | QUDT | contextualMatch | Quantity/unit alignment only |
| `cim:compute.node.power.draw` | SOSA-SSN | contextualMatch | Observation model |
| `cim:compute.node.power.draw` | SAREF | closeMatch | Device power concepts |
| `cim:compute.node.power.draw` | ISO-IEC-30134 | inputToKPI | Input, not the KPI itself |
| `cim:compute.node.power.draw` | EN-50600 | inputToKPI | Input measurement |
| `cim:compute.gpu.power.average` | QUDT | contextualMatch | Quantity/unit alignment |
| `cim:compute.gpu.power.average` | SOSA-SSN | contextualMatch | Observation model |
| `cim:compute.gpu.power.average` | SAREF | closeMatch | Device power concepts |
| `cim:compute.gpu.power.average` | OCP | contextualMatch | Hardware efficiency practices |
| `cim:workflow.energy.per_run` | QUDT | contextualMatch | Unit alignment |
| `cim:workflow.energy.per_run` | PROV-O | contextualMatch | Provenance relevance |
| `cim:workflow.energy.per_run` | RO-CRATE | contextualMatch | Reproducibility packaging |
| `cim:workflow.energy.per_run` | SCHEMA-ORG | contextualMatch | Metadata relevance |
| `cim:carbon.emission.operational` | ISO-14040-14044 | contextualMatch | GHG/LCA framing only |
| `cim:carbon.emission.operational` | EU-COC-DC | contextualMatch | Reporting practice relevance |
| `cim:carbon.intensity.location_based` | ISO-14040-14044 | contextualMatch | Not exact clause claim |
| `cim:carbon.intensity.location_based` | EU-COC-DC | contextualMatch | Reporting practice relevance |
| `cim:water.usage.total` | ISO-IEC-30134 | inputToKPI | Input toward WUE |
| `cim:water.usage.total` | EN-50600 | contextualMatch | Water/env reporting practice |

**Not seeded as exactMatch:** workflow energy ↔ ISO/EN KPIs; node/GPU power ↔ ISO KPIs; carbon emission ↔ specific ISO emission-factor clauses.
