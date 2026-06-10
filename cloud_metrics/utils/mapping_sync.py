import json
import os
from typing import Dict, List, Optional

# Resolve where to write the mapping JSON
_ENV_PATH = os.getenv("MAPPING_JSON_PATH", "").strip()
if _ENV_PATH:
    _MAPPING_PATH = os.path.normpath(_ENV_PATH)
else:
    # default inside repo (editable installs still point here)
    _MAPPING_PATH = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "mapping", "metric_mapping.json")
    )

def _ensure_parent_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)

def _ensure_mapping_file() -> None:
    _ensure_parent_dir(_MAPPING_PATH)
    if not os.path.exists(_MAPPING_PATH):
        with open(_MAPPING_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
        print(f"🆕 Created mapping file at: {_MAPPING_PATH}")

def _load() -> Dict[str, List[str]]:
    _ensure_mapping_file()
    try:
        with open(_MAPPING_PATH, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        out: Dict[str, List[str]] = {}
        for k, v in data.items():
            if isinstance(v, list):
                out[k] = [str(x) for x in v]
            elif isinstance(v, str):
                out[k] = [v]
        return out
    except Exception:
        return {}

def _atomic_write_to(path: str, data: Dict[str, List[str]]) -> None:
    _ensure_parent_dir(path)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp_path, path)
    print(f"💾 mapping JSON updated: {path} (keys={len(data)})")

def _atomic_write(data: Dict[str, List[str]]) -> None:
    _atomic_write_to(_MAPPING_PATH, data)

def _clear_mapper_cache() -> None:
    try:
        from cloud_metrics.mapping.namespace_mapper import _load_mapping as _nm_load
        _nm_load.cache_clear()  # type: ignore[attr-defined]
        print("🔄 namespace_mapper cache cleared")
    except Exception:
        pass

def sync_metric_mapping(unified_key: str, source_key: str, tags: Optional[List[str]] = None) -> None:
    unified_key = str(unified_key).strip()
    source_key = str(source_key).strip()
    if not unified_key or not source_key:
        return
    data = _load()
    cur = set(data.get(unified_key, []))
    if source_key not in cur:
        cur.add(source_key)
        data[unified_key] = sorted(cur)
        _atomic_write(data)
        _clear_mapper_cache()

def remove_source_key(unified_key: str, source_key: str) -> None:
    data = _load()
    lst = data.get(unified_key)
    if not lst:
        return
    new_list = [x for x in lst if x != source_key]
    if new_list:
        data[unified_key] = new_list
    else:
        data.pop(unified_key, None)
    _atomic_write(data)
    _clear_mapper_cache()

def export_registry_to_json(dest_path: Optional[str] = None) -> str:
    """
    Merge both sources:
      - metric_mappings (approved registry)
      - metric_definitions.sources (legacy)
    """
    from cloud_metrics.utils.config import SessionLocal
    from cloud_metrics.models.metric_mapping import MetricMapping
    from cloud_metrics.models.metric_definition import MetricDefinition

    dest = os.path.normpath(dest_path or _MAPPING_PATH)
    data: Dict[str, set] = {}

    with SessionLocal() as s:
        for row in s.query(MetricMapping).all():
            data.setdefault(row.unified_key, set()).add(row.raw_key)
        for md in s.query(MetricDefinition).all():
            for raw in (md.sources or []):
                data.setdefault(md.unified_key, set()).add(str(raw))

    final = {k: sorted(v) for k, v in data.items()}
    _atomic_write_to(dest, final)
    if not dest_path:
        _clear_mapper_cache()
    print(f"📦 export_registry_to_json wrote {sum(len(v) for v in final.values())} pairs across {len(final)} unified keys")
    return dest
