# Source and Asset Resolution Policy

> **Milestone 6** · Soft enrichment contract

---

## Extraction

`cloud_metrics/registry/context_extract.py`

* `extract_source_hints(metadata)` — source / job / file / API / Prom-like labels
* `extract_asset_hints(metadata)` — site/cluster/node/gpu/workflow/… aliases

Nested `labels` / `metadata` / `resource` / `attributes` / `tags` are flattened one level.

---

## Policy

| Situation | Behaviour |
|-----------|-----------|
| Known source `(name, type)` | `resolved` |
| New source, `create_candidate=True` | `candidate_created` (`status=candidate`) |
| New source, `create_candidate=False` | `missing` |
| Same name, multiple types, type omitted | `ambiguous` |
| Known asset `(identifier, type)` | `resolved` (may attach parent if previously null) |
| New asset | `candidate_created` or `missing` per flag |
| No extractable hints | `missing` |
| No DB session | `unknown` |
| Mapping without context | `not_requested` (fields left `None`) |

---

## Mapping lookup defaults

* `context=None` → no source/asset resolution (M4/M5 compatible)
* `context={...}` → resolve both source and asset (soft)
* `resolve_source` / `resolve_asset` override
* Unit validation (M5) remains independent
* **Never** flip `resolved` because source/asset is missing or candidate

---

## Duplicates

* Sources: unique `(name, type)` — second resolve returns existing
* Assets: unique `(identifier, type)` — second resolve returns existing

---

## Out of scope

* Replacing `Datacenter` / legacy `Source`/`Asset` in ingestion
* Persisting `source_id`/`asset_id` on `MetricSample`
* Full Prom scrape / OTLP receivers
* Lifecycle / standards / provenance wiring beyond existing seed FKs
