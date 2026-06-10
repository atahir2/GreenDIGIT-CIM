# Current Metric Mapping Logic — GreenDIGIT CIM

> **Generated**: 2026-06-10 · **Scope**: Detailed audit of all metric classification and mapping mechanisms (read-only)

---

## 1. Overview

The CIM system maps **raw metric keys** (vendor-specific, partner-specific names) to **unified keys** in the GreenDIGIT namespace. The mapping logic is distributed across **multiple modules** with significant overlap and duplication.

### Unified Key Format

```
gd.<category>.<subcategory>.<short_key>
```

| Part | Purpose | Examples |
|------|---------|----------|
| `gd` | Fixed prefix (GreenDIGIT) | Always `gd` |
| `category` | Domain area | `energy`, `performance`, `network`, `storage`, `environment` |
| `subcategory` | Specific concern | `consumption`, `cpu`, `traffic`, `disk`, `temperature` |
| `short_key` | Metric identifier | `total`, `utilization`, `incoming`, `read_io`, `interior` |

---

## 2. Classification Mechanisms (5 Layers)

### Layer 1: Semantic Classifier

**File**: [semantic_classifier.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/ingestion/semantic_classifier.py)

Exact suffix matching against a hardcoded dictionary of 10 entries.

| Normalized Suffix | Standard | Category | Subcategory | Short Key |
|------------------|----------|----------|-------------|-----------|
| `elecpower` | iso | energy | power | total |
| `powersolar` | iso | energy | renewable | solar |
| `diskreadio` | iso | storage | disk | read_io |
| `diskwriteio` | iso | storage | disk | write_io |
| `envinternaltemp` | jrc | environment | temperature | internal |
| `envexternaltemp` | jrc | environment | temperature | external |
| `cpuusage` | iso | performance | cpu | utilization |
| `memoryused` | iso | performance | memory | usage |
| `networkin` | iso | network | traffic | incoming |
| `networkout` | iso | network | traffic | outgoing |

**Normalization**: `raw_key.lower().replace(" ","").replace("-","").replace("_","")` then checks `endswith()`.

**Issues**:
- Only 10 entries — very limited coverage
- Returns `(org, domain, category, metric)` but the `org` (e.g., "iso", "jrc") is discarded by callers
- Naming inconsistency: returns "internal"/"external" for temperature but alias classifier uses "interior"/"exterior"

---

### Layer 2: Database Keyword Lookup

**File**: [automated_mapper.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/ingestion/automated_mapper.py#L66-L76) (inside `_classify_to_parts()`)

Queries `metric_keywords` table for exact match on `keyword` or `source_key`.

```sql
SELECT * FROM metric_keywords
WHERE keyword = lower(raw_key) OR source_key = lower(raw_key)
LIMIT 1;
```

Returns `(category, subcategory, short_key)` if found.

**Note**: This only runs inside the unused `_classify_to_parts()` function. The main path via `classify_metric()` in ensemble_classifier does **not** query DB keywords.

---

### Layer 3: Alias Fuzzy Classifier

**File**: [alias_classifier.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/classifiers/alias_classifier.py)

Uses **RapidFuzz** `WRatio` scorer against ~80 hardcoded aliases.

**Alias Categories:**

| Category | Subcategory | Short Key | # Aliases | Example Aliases |
|----------|-------------|-----------|-----------|-----------------|
| energy | consumption | total | 8 | `energy_wh`, `kwh_total`, `energy_consumed` |
| energy | power | total | 4 | `active_power`, `electric_power`, `wattage` |
| energy | renewable | solar | 4 | `solar`, `pv`, `photovoltaic` |
| energy | efficiency | pue | 5 | `pue`, `power_usage_effectiveness`, `dc_pue` |
| network | traffic | incoming | 5 | `network_in`, `rx_bytes`, `ingress_bytes` |
| network | traffic | outgoing | 5 | `network_out`, `tx_bytes`, `egress_bytes` |
| network | traffic | total_bytes | 6 | `amountofdatatransferred`, `bytes_transferred` |
| storage | disk | read_io | 6 | `disk_read_ops`, `read_iops`, `read_bytes` |
| storage | disk | write_io | 6 | `disk_write_ops`, `write_iops`, `write_bytes` |
| storage | disk | latency | 6 | `disk_latency`, `avg_read_latency`, `avgqlen` |
| storage | disk | usage | 6 | `disk_usage`, `disk_used`, `capacity_used` |
| environment | temperature | interior | 5 | `interior_temperature`, `temp_indoor` |
| environment | temperature | exterior | 5 | `exterior_temperature`, `temp_outdoor` |
| environment | temperature | ambient | 3 | `ambient_temperature`, `temp_room` |
| environment | water | wue | 5 | `wue`, `water_usage_effectiveness` |
| environment | emissions | cfp | 7 | `cfp`, `carbon_footprint`, `co2e`, `ghg_emissions` |
| environment | emissions | ci | 3 | `ci`, `carbon_intensity` |
| performance | work | total | 2 | `work`, `work_total` |
| performance | time | wallclock | 4 | `wallclocktime_s`, `walltime_s` |
| performance | time | suspend | 3 | `suspendduration_s`, `suspend_duration` |
| performance | cpu | time | 4 | `cpuduration_s`, `totalcputime_s` |
| performance | cpu | normalization_factor | 2 | `cpunormalizationfactor` |
| performance | cpu | count | 2 | `ncores`, `cores` |
| performance | cpu | tdp | 1 | `tdp_w` |
| performance | cpu | time_normalized | 1 | `normcputime_s` |
| performance | cpu | time_scaled | 1 | `scaledcputime_s` |
| performance | efficiency | compute | 2 | `efficiency`, `compute` |

**Cutoff**: 88 in ensemble, 90 in `_classify_to_parts()` (inconsistent).

---

### Layer 4: Token Rule Engine

**File**: [ensemble_classifier.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/classifiers/ensemble_classifier.py#L30-L74) (`_rule_guess()`)

Token-based set intersection. Tokenizes raw_key via `[A-Z]?[a-z]+|[0-9]+` regex, then checks membership:

| Domain | Trigger Tokens | Sub-decision Tokens | Result |
|--------|---------------|---------------------|--------|
| Storage | disk, volume, filesystem, fs, storage | read, writes → read_io/write_io; latency → latency | `storage.disk.*` |
| Network | network, traffic, throughput, bandwidth | in, rx, ingress → incoming; out, tx → outgoing | `network.traffic.*` |
| Energy | kwh, kilowatthour, consumption | — | `energy.consumption.total` |
| Energy | solar, pv, renewable | — | `energy.renewable.solar` |
| Energy | power, watt, watts, kw | — | `energy.power.total` |
| Env | temperature, temp, celsius | interior/int → interior; exterior/ext → exterior | `environment.temperature.*` |
| Perf | cpu, processor | — | `performance.cpu.utilization` |
| Perf | memory, mem, ram | — | `performance.memory.usage` |

**Confidence**: 0.60–0.80

---

### Layer 5: Embedding Classifier

**File**: [ensemble_classifier.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/classifiers/ensemble_classifier.py#L76-L97) (`_embed_guess()`)

Uses **sentence-transformers/all-MiniLM-L6-v2** to encode the raw key and compare against 10 canonical phrases via cosine similarity.

```python
CANDIDATES = [
    ("storage read io",              ("storage","disk","read_io")),
    ("storage write io",             ("storage","disk","write_io")),
    ("storage latency",              ("storage","disk","latency")),
    ("storage usage",                ("storage","disk","usage")),
    ("network traffic incoming",     ("network","traffic","incoming")),
    ("network traffic outgoing",     ("network","traffic","outgoing")),
    ("energy consumption kwh total", ("energy","consumption","total")),
    ("energy power total",           ("energy","power","total")),
    ("solar renewable energy",       ("energy","renewable","solar")),
    ("environment ambient temperature", ("environment","temperature","ambient")),
]
```

**Threshold**: cosine similarity ≥ 0.60. Model is lazy-loaded (first call penalty).

---

### Layer 6: Fallback

**File**: [fallbacks.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/classifiers/fallbacks.py)

Returns `("custom", "unknown", slug_of_raw_key)`.

**Critical Bug**: Lines 21–50 contain more sophisticated logic (PUE/CFP detection, unit-driven hints, token slugging) but are **unreachable dead code** because line 19 has an unconditional `return`.

---

## 3. Namespace Generation

### 3.1 `ensure_gd_namespace()` (Primary)

**File**: [namespace_registry.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/registry/namespace_registry.py)

1. Checks if `Category` row exists in DB (case-insensitive)
2. If not and `auto_create=True`, creates it (links to `gd` standard)
3. Same for `Subcategory`
4. Returns `gd.{cat.name}.{sub.name}.{short_key.lower()}`
5. Guard: skips auto-creation for `uncategorized`/`unknown` values

### 3.2 `generate_namespace()` (Unused Legacy)

**File**: [namespace_generator.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/namespace_generator.py)

1. Looks up `Category` → `Standard` → `Subcategory` in DB
2. Returns `{standard.name}.{cat.name}.{sub.name}.{metric_short_key}`
3. Includes alias maps (`CATEGORY_ALIASES`, `SUBCATEGORY_ALIASES`)
4. **Not used** in the main ingestion flow — superseded by `ensure_gd_namespace()`

### 3.3 `to_gd()` (Post-Normalization)

**File**: [unified_key.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/utils/unified_key.py)

Normalizes any dotted key to exactly `gd.cat.sub.short`:
- Already `gd.*` → keep next 3 parts
- 4+ parts → drop first (assumed standard prefix), take next 3
- 3 parts → assume cat.sub.short, prefix `gd.`
- Otherwise → `gd.unknown.unknown.unknown`

---

## 4. Mapping Storage

### 4.1 JSON File (`metric_mapping.json`)

**Two files with different schemas:**

#### `cloud_metrics/mapping/metric_mapping.json` (Runtime)

```json
{
  "gd.energy.consumption.total": [
    "1-grid-site", "alpha.energy.kwh", "datacenter_A", "energy_wh", ...
  ]
}
```
- Structure: `{ unified_key: [source_key_1, source_key_2, ...] }`
- **Problem**: mixes datacenter names ("datacenter_A", "1-grid-site") with actual raw metric keys ("energy_wh")
- Updated atomically via `mapping_sync.py`

#### `cloud_metrics/data/metric_mapping.json` (Export)

```json
{
  "generated_at": "2025-09-08T12:56:12.461918+00:00",
  "count": 30,
  "mappings": {
    "elec.power": {
      "unified_key": "gd.energy.power.total",
      "last_seen": "2025-09-08T12:14:05.017949+00:00"
    }
  }
}
```
- Structure: `{ raw_key: { unified_key, last_seen } }`
- Generated by `rebuild_mapping_json.py`

### 4.2 Database Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `metric_mappings` | **Canonical approved** raw→unified | `raw_key` (unique), `unified_key`, `version`, `unit` |
| `mapping_proposals` | **Proposed** mappings awaiting review | `raw_key`, `suggested_unified_key`, `confidence`, `status` |
| `mapping_events` | **Audit trail** | `raw_key`, `event`, `payload` |
| `metric_source_map` | **Per-datacenter** raw→unified tracking | `datacenter_id`, `raw_key`, `unified_key`, `first_seen`, `last_seen` |
| `metric_keywords` | **Learned** raw→taxonomy cache | `keyword`, `category`, `subcategory`, `short_key` |
| `metric_definitions` | **Unified key registry** | `unified_key` (unique), `tags`, `sources` |

### 4.3 `mapping_sync.py` — JSON ↔ DB Sync

**File**: [mapping_sync.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/utils/mapping_sync.py)

- `sync_metric_mapping(unified_key, source_key)` — adds source_key to unified_key's list in JSON
- `remove_source_key(unified_key, source_key)` — removes a mapping
- `export_registry_to_json(dest)` — merges `metric_mappings` + `metric_definitions.sources` → JSON
- Uses atomic write (temp file + `os.replace`)
- Clears `namespace_mapper._load_mapping` cache after updates

---

## 5. Standards Linkage

**File**: [standards_registry.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/standards_registry.py)

### Seeded Standards (12)

| Code | Standard | Description |
|------|----------|-------------|
| TGG-PUE | The Green Grid PUE | Power Usage Effectiveness |
| TGG-WUE | The Green Grid WUE | Water Usage Effectiveness |
| GHG | Greenhouse Gas Protocol | Emissions / CO2e / CFP |
| ISO-50001 | ISO 50001 | Energy management systems |
| ASHRAE-90.4-2022 | Energy Standard for Data Centers | Energy efficiency requirements |
| ASHRAE-TC9.9-2021 | Thermal Guidelines 5th ed. | Thermal/humidity envelopes |
| JRC-CoC-2025 | EU Code of Conduct | Best practice for DC energy |
| IEEE-802.3az-2010 | Energy Efficient Ethernet | EEE / LPI |
| IEEE-1459-2025 | Electric Power Quantities | Power definitions |
| IEEE-1547-2018 | DER Interconnection | Distributed energy resources |
| IETF | Internet Engineering Task Force | Networking metrics |
| SNIA | Storage Networking Industry Association | Storage performance |

### Linkage Rules

```python
gd.energy.efficiency.pue     → TGG-PUE (0.99)
gd.environment.water.wue     → TGG-WUE (0.99)
gd.environment.emissions.*   → GHG (0.85)
gd.environment.temperature.* → ASHRAE-TC9.9-2021 (0.80)
gd.energy.power.total        → IEEE-1459-2025 (0.70)
gd.energy.renewable.solar    → IEEE-1547-2018 (0.50)
gd.network.traffic.*         → IETF (0.60)
gd.storage.disk.*            → SNIA (0.60)
gd.performance.cpu/memory    → JRC-CoC-2025 (0.40) [optional flag]
gd.energy.*                  → ISO-50001 (0.60) [umbrella]
```

---

## 6. Known Issues in Mapping Logic

| Issue | Location | Severity |
|-------|----------|----------|
| **Duplicated classification rules** | `automated_mapper._classify_to_parts()` vs `ensemble_classifier.classify_metric()` | High — two independent codepaths |
| **Dead code in fallbacks.py** | L21–50 unreachable after L19 early return | Medium — lost functionality |
| **Temperature naming inconsistency** | semantic: "internal/external" vs alias: "interior/exterior" | Medium — different unified keys for same concept |
| **Datacenter names in mapping JSON** | `metric_mapping.json` stores origin labels as "source keys" | High — pollutes reverse lookup |
| **`metric_mappings` table unused** | Model exists but `register_mapping()` doesn't write to it | Medium — dead schema |
| **`mapping_proposals`/`mapping_events` unused** | Models exist but no code writes to them | Medium — audit trail not active |
| **Two different mapping JSON formats** | `mapping/` vs `data/` with incompatible schemas | High — confusing |
| **No DB keyword lookup in main flow** | `classify_metric()` chain skips DB keyword check | Medium — learned keywords only help via `_classify_to_parts()` which is a parallel path |
| **Inconsistent fuzzy cutoffs** | 88 in ensemble_classifier, 90 in automated_mapper | Low — minor |
| **`efficiency` alias too generic** | "efficiency" maps to `performance.efficiency.compute` — could match energy efficiency | Low |
