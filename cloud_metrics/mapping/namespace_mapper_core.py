# cloud_metrics/mapping/namespace_mapper_core.py

import os
from typing import Dict, Tuple
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cloud_metrics.parsers.structured_parser import parse_structured_file
from cloud_metrics.parsers.unstructured_parser import parse_unstructured_text
from cloud_metrics.mapping.namespace_mapper import map_raw_to_unified

SUPPORTED_FILE_TYPES = {
    ".json", ".jsonl", ".ndjson",
    ".yaml", ".yml",
    ".csv", ".xml", ".txt"
}

def parse_and_extract_file_metrics(file_path: str, datacenter: str) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Parse a file into raw metrics, then map raw->unified using the registry.
    Returns (raw_metrics, mapped_metrics).
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_FILE_TYPES:
        raise ValueError(f"Unsupported file type: {ext}")

    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
            text = f.read()
        raw = parse_unstructured_text(text, datacenter=datacenter)
    else:
        raw = parse_structured_file(file_path)

    mapped: Dict[str, float] = {}
    for raw_key, val in raw.items():
        um = map_raw_to_unified(raw_key, val)
        if um:
            mapped[um.name] = float(val)
    return raw, mapped


def extract_metrics(metric_data: Dict[str, float], datacenter_name: str) -> Dict[str, float]:
    """
    Map a dict of raw metrics (from an API) to unified names using the registry.
    """
    mapped: Dict[str, float] = {}
    for raw_key, val in (metric_data or {}).items():
        um = map_raw_to_unified(raw_key, val)
        if um:
            mapped[um.name] = float(val)
    return mapped
