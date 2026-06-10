import json, os
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional

from cloud_metrics.services.registry_service import resolve_unified_key

try:
    from cloud_metrics.utils.mapping_sync import _load as _load_sync
except Exception:
    _load_sync = None  # fallback below

_MAPPING_PATH = os.path.join(os.path.dirname(__file__), "metric_mapping.json")

@dataclass(frozen=True)
class UnifiedMetric:
    name: str
    tags: Dict[str, str]

@lru_cache(maxsize=1)
def _load_mapping() -> Dict[str, List[str]]:
    # Prefer mapping_sync loader (respects MAPPING_JSON_PATH); otherwise read local file.
    if _load_sync:
        return _load_sync()
    try:
        with open(_MAPPING_PATH, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        out: Dict[str, List[str]] = {}
        for k, v in data.items():
            out[k] = v if isinstance(v, list) else [v]
        return out
    except Exception:
        return {}

def map_raw_to_unified(raw_key: str, value: float) -> Optional[UnifiedMetric]:
    mapping = _load_mapping()
    for unified, raw_list in mapping.items():
        if raw_key in raw_list:
            return UnifiedMetric(name=unified, tags={})
    return None
