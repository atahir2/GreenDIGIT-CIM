# CIM Standards Alignment Summary

> Research packaging · Milestone 15

## Position

The CIM **aligns to** selected standards vocabularies; it does **not** claim to implement those standards. Alignment is stored as mapping rows with an explicit `relation_type` and `review_status`.

## Relation vocabulary

`exactMatch`, `closeMatch`, `broadMatch`, `narrowMatch`, `inputToKPI`, `derivedFrom`, `contextualMatch`, `extensionMetric`, `noMatch`, `underReview`.

SKOS identity predicates are used in JSON-LD **only** for the first four. CIM-specific relations stay in a placeholder `cim:` namespace.

## Safe identity claims (seeded)

| CIM metric | Standard | Relation |
|------------|----------|----------|
| `cim:energy.efficiency.pue` | ISO/IEC 30134 | exactMatch |
| `cim:energy.efficiency.pue` | EN 50600 | exactMatch |

## Intentionally weaker claims

| CIM metric | Standards | Typical relation |
|------------|-----------|------------------|
| Node / GPU power | QUDT, SOSA/SSN, SAREF, ISO 30134, EN 50600 | contextualMatch / closeMatch / inputToKPI |
| Workflow energy per run | QUDT, PROV-O, RO-Crate, schema.org | contextualMatch |
| Operational carbon | ISO 14040/14044, EU CoC DC | contextualMatch |
| Water usage | ISO 30134, EN 50600 | inputToKPI / contextualMatch |

WUE and CUE KPI namespaces have **no** seeded `exactMatch`.

## Export

The standards crosswalk export lists CIM namespace, standard, term, relation type, confidence, review status, and notes. JSON-LD attaches mappings only to **approved** metrics.

Policy source: `docs/target/STANDARDS_ALIGNMENT_POLICY.md`, `docs/target/SEEDED_STANDARDS_AND_RELATIONS.md`.
