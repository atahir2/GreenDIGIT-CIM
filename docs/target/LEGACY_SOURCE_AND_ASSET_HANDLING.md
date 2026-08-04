# Legacy Source and Asset Handling

> **Milestone 6** · Inventory of existing source / resource / asset behaviour  
> **Status**: Documented (legacy paths remain in place)

---

## 1. Parser tags and labels

| Location | Behaviour |
|----------|-----------|
| `parsers/structured_parser.py` | Flattens structured files to numeric keys; no Prom/OTel label model |
| `parsers/unstructured_parser.py` | Regex extraction; keys like `{datacenter}.cpu` |
| `utils/metadata.py` → `IngestMeta` / `parse_partner_metadata()` | Primary partner metadata: datacenter, ri_id, node_id, vm_id, host, site_id |
| `utils/ingest_any.py` | `PartnerMeta`, site-id key aliases |
| `MetricSample.tags` | JSON bag; often empty or classification tags |

There is **no** production Prometheus/OpenTelemetry label pipeline today.

---

## 2. Source system identifiers

| Location | Behaviour |
|----------|-----------|
| `ingestion/automated_mapper.py` | Heuristic `file_upload` / `aws_cloudwatch` / `gcp_monitoring` via `origin_label`; looks up legacy `Source` by name (ID not persisted on sample) |
| `api/registry_api.py` | CRUD on legacy `sources` table |
| `scripts/streamlit_uploader.py` | Datacenter-centric upload path |
| `models/cim_mapping.py` / `CimMetricMapping` | Optional `source_id` FK (legacy → `sources`, CIM → `cim_sources`) |

---

## 3. Node / cluster / GPU / workflow identifiers

Persisted as **flat strings** on `MetricSample` (`ri_id`, `node_id`, `vm_id`, `host`, `site_id`) — not as hierarchical Asset rows.

Asset type vocabulary exists on models/comments (`datacenter`, `cluster`, `node`, `gpu`, `workflow`, …) but runtime almost only creates `type="datacenter"` assets in migration scripts.

---

## 4. Database models

| Model | Table | Notes |
|-------|-------|-------|
| `Source` | `sources` | Legacy Antigravity |
| `Asset` | `assets` | Legacy; hierarchy via `parent_id`; **no** `identifier` |
| `Datacenter` | `datacenters` | Still FK target for samples / uploads |
| `CimSource` | `cim_sources` | Milestone 2+; unique `(name, type)` |
| `CimAsset` | `cim_assets` | Milestone 2+; unique `(identifier, type)`; parent + lifecycle FKs |

---

## 5. Seeds and tests

* Legacy sources seeded in `scripts/seed_registries.py`
* CIM bootstrap source: `cim_registry_bootstrap` (Milestone 3)
* No bulk `CimAsset` seed catalogue
* Skeleton tests expect empty `list_sources()` / `list_assets()` without a session

---

## 6. Milestone 6 stance

Additive soft resolution against `cim_sources` / `cim_assets`. Legacy `Source` / `Asset` / `Datacenter` paths are **not** removed or forced onto ingestion in this milestone.
