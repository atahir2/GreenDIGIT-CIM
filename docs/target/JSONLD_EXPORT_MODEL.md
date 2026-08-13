# JSON-LD Export Model

> **Milestone 15** · **Partial** implementation

## Status

**Partial.** Metrics are emitted as JSON-LD entities with a small, conservative `@context`. This is **not**:

- a complete CIM ontology
- a SHACL-validated graph
- a full QUDT / SAREF / PROV-O mapping
- an RDF/Turtle exporter (future work)

`compliance.full_standards_compliance` is always `false`. Profile: `cim-jsonld-partial`.

## Context (safe subset)

Used where the correspondence is obvious and already seeded:

| Prefix | IRI | Use |
|--------|-----|-----|
| `schema` | https://schema.org/ | `name`, `description`, `identifier`, `unitCode`, `PropertyValue` |
| `qudt` | http://qudt.org/schema/qudt/ | `hasQuantityKind` / `hasUnit` **only when** `qudt_uri` is stored on the quantity kind or unit |
| `prov` | http://www.w3.org/ns/prov# | provenance reference (`prov:Entity`, `wasGeneratedBy`, `wasAttributedTo`) |
| `skos` | http://www.w3.org/2004/02/skos/core# | `exactMatch`, `closeMatch`, `broadMatch`, `narrowMatch` |
| `cim` | https://example.org/greendigit/cim# | **Placeholder** CIM terms (`inputToKPI`, `contextualMatch`, …). Not a published ontology. |

## Metric entity (minimum fields)

| Field | JSON-LD key | Source |
|-------|-------------|--------|
| Metric as entity | `@type`: `schema:PropertyValue`, `cim:MetricDefinition` | — |
| Namespace | `identifier` | `cim_metric_definitions.namespace` |
| Label | `name` | `label` |
| Description | `description` | `description` |
| Unit | `unitCode` | canonical unit symbol |
| Quantity kind | `quantityKind` | quantity kind name |
| Source / asset context | `sourceContext` | `sources` JSON when present |
| Standards mappings | `standardsMappings[]` | relation type, SKOS/CIM predicate, review status, notes |
| Provenance reference | `provenance` | last `metric_definition` provenance record, or `null` |
| Governance | `status`, `reviewStatus` | stored values, never rewritten |

## Mapping predicates

| `relation_type` | Predicate |
|-----------------|-----------|
| exactMatch / closeMatch / broadMatch / narrowMatch | `skos:*` |
| inputToKPI, derivedFrom, contextualMatch, extensionMetric, noMatch, underReview | `cim:*` (CIM-specific; not SKOS) |

## Candidate policy

If the metric `status` is not `approved`/`active`, **approved standards mappings are omitted**. The entity still carries `status: candidate` (or whatever is stored).

## API

```text
GET /api/v1/cim-export/jsonld?namespace=cim:energy.efficiency.pue
GET /api/v1/cim-export/jsonld?all_metrics=true
```
