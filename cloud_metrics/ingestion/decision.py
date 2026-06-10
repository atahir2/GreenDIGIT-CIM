# cloud_metrics/ingestion/decision.py
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass(frozen=True)
class MappingDecision:
    unified_key: str
    confidence: float
    rationale: str
    unit: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
