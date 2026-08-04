# Standards Alignment Policy

> **Milestone 8** · Conservative claims only

---

## Principles

1. **Explicit seed only** — exactMatch requires a curated seed row.
2. **No silent upgrades** — heuristics must not invent exactMatch.
3. **Candidate isolation** — candidate/unknown metrics do not inherit approved standards mappings.
4. **Soft enrichment** — missing standards never fail ingestion.
5. **Transparent relations** — prefer `inputToKPI` / `contextualMatch` over false identity.

## Safe exactMatch examples

* PUE ↔ ISO/IEC 30134
* PUE ↔ EN 50600

## Intentionally not exactMatch

| Metric | Why |
|--------|-----|
| Node / GPU power | Input / observation models only |
| Workflow energy per run | Reproducibility / provenance relevance; no ISO/EN KPI identity |
| Operational carbon | Contextual carbon accounting only unless a specific seeded term exists |
| Water usage total | Input to WUE / contextual EN practice |

## Flag

`no_direct_standard_match` communicates “no exact identity claim” to callers and UIs.
