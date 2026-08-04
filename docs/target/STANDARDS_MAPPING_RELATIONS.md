# Standards Mapping Relations

> **Milestone 8** · Controlled vocabulary for metric↔standard links

---

## Allowed `relation_type` values

| Relation | Meaning | When to use |
|----------|---------|-------------|
| `exactMatch` | Same concept / KPI identity | Only when explicitly seeded and safe (e.g. PUE ↔ ISO/IEC 30134-2) |
| `closeMatch` | Strong conceptual overlap | e.g. SAREF power measurement vs node power |
| `broadMatch` | Broader standard concept | Rare in seed |
| `narrowMatch` | Narrower specialisation | Rare in seed |
| `inputToKPI` | Measurement feeds a KPI | Node power → PUE inputs; water → WUE |
| `derivedFrom` | Derived from standard formula | Reserved |
| `contextualMatch` | Relevant framing / model / unit | QUDT, SOSA/SSN, PROV-O, RO-Crate, OCP |
| `extensionMetric` | Outside catalogue alignment | Extension metrics |
| `noMatch` | Explicitly no alignment | Declared non-match |
| `underReview` | Proposed, not approved | Review queue |

## Rules

1. Never upgrade `contextualMatch` / `inputToKPI` / `closeMatch` to `exactMatch` automatically.
2. `no_direct_standard_match=True` when no `exactMatch` exists (even if other relations are present).
3. Candidate metrics never receive approved standards mappings via the orchestrator.
