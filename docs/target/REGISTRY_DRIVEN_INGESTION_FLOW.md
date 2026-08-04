# Registry-Driven Ingestion Flow

> **Milestone 7** · Target path with orchestrator on unified file ingestion

---

## Target pipeline

```
input file / API / stream
  → parser
  → normalizer (existing flatten / numeric extract)
  → classifier  ─┐
                 │  (legacy ensemble still available)
  → registry orchestrator
       → Mapping Registry lookup
       → Unit Registry validation (soft)
       → Source Registry resolution (soft)
       → Asset Registry resolution (soft)
       → candidate handling
  → normalized CIM mapping result (OrchestratorResult)
  → adapter → storage_unified_key (gd.*)
  → existing storage layer
       (samples, Influx, JSON sync, definitions, upload log)
```

---

## Wired path (Milestone 7)

**Only** `cloud_metrics/ingestion/unified_ingestion.py` → `ingest_from_file()` enables the orchestrator by default:

```
ingest_from_file(..., use_registry_orchestrator=True)
  → parse_and_extract_file_metrics()
  → process_metric_sample(..., use_registry_orchestrator=True)
       → RegistryOrchestratorService.process()
       → if resolved: use storage_unified_key
       → else: legacy ensemble classifier (unchanged)
       → existing unit convert / rules / persist
```

Opt out: `ingest_from_file(..., use_registry_orchestrator=False)`.

---

## Not wired yet (remain legacy)

* `realtime_ingestor.ingest_from_api`
* AWS / GCP helpers
* Streamlit uploader
* Direct `process_metric_sample(...)` without the flag

---

## Resolution outcomes

| Outcome | `resolution_path` | Storage key source |
|---------|-------------------|--------------------|
| Registry hit | `registry` | `legacy_unified_key` or CIM→gd |
| Legacy fallback | `legacy_fallback` | same; `fallback_used=true` |
| Unresolved | `unresolved` | ensemble / fallback namespace |

Unit / source / asset enrichment never flips `resolved` to false (soft policy from Milestones 5–6).
