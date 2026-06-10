# cloud_metrics/parsers/structured_parser.py

import os
import json
import csv
import xml.etree.ElementTree as ET
from typing import Any, Dict, Iterable
from collections.abc import MutableMapping

try:
    import yaml  # PyYAML
except ImportError as e:
    raise ImportError(
        "PyYAML is required. Install with `pip install pyyaml` or `poetry add pyyaml`."
    ) from e


def _flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
    items: list[tuple[str, Any]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, MutableMapping):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def _to_float_or_none(x: Any):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _merge_docs(docs: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge multiple documents into a single flat dict:
    doc0.key, doc1.key, ...
    Only keep numeric values.
    """
    merged: Dict[str, Any] = {}
    for i, doc in enumerate(docs):
        flat = _flatten_dict(doc)
        for k, v in flat.items():
            fv = _to_float_or_none(v)
            if fv is not None:
                merged[f"doc{i}.{k}"] = fv
    return merged


def _parse_json_text(text: str) -> Dict[str, Any]:
    """
    Robust JSON parser:
    1) Try a single JSON document.
    2) If that fails with 'Extra data', try JSON Lines (NDJSON).
    3) As a final fallback, try parsing as YAML (YAML is a superset of JSON).
    Keeps only numeric values.
    """
    # 1) Single JSON doc
    try:
        data = json.loads(text)
        if isinstance(data, list):
            # list of docs -> merge with docN prefixes
            return _merge_docs([obj if isinstance(obj, dict) else {"value": obj} for obj in data])
        if isinstance(data, dict):
            flat = _flatten_dict(data)
            return {k: v for k, v in ((k, _to_float_or_none(v)) for k, v in flat.items()) if v is not None}
        # Primitive -> ignore
        return {}
    except json.JSONDecodeError as e:
        # 2) Try NDJSON (one JSON object per line)
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        ndjson_objs: list[Dict[str, Any]] = []
        ndjson_failed = False
        for ln in lines:
            try:
                obj = json.loads(ln)
                if isinstance(obj, dict):
                    ndjson_objs.append(obj)
                else:
                    ndjson_objs.append({"value": obj})
            except json.JSONDecodeError:
                ndjson_failed = True
                break
        if not ndjson_failed and ndjson_objs:
            return _merge_docs(ndjson_objs)

        # 3) Fallback to YAML (handles some “JSON-ish” with comments/trailing commas)
        try:
            docs = list(yaml.safe_load_all(text))
            # Normalize docs to dicts
            norm_docs = []
            for d in docs:
                if d is None:
                    continue
                if isinstance(d, dict):
                    norm_docs.append(d)
                else:
                    norm_docs.append({"value": d})
            if not norm_docs:
                return {}
            return _merge_docs(norm_docs)
        except Exception:
            # Re-raise the original JSON error for clarity
            raise e


def parse_structured_file(filepath: str) -> Dict[str, float]:
    """
    Parse JSON / JSONL / NDJSON / YAML / YML / CSV / XML.
    Return a flat dict of numeric values only.
    """
    ext = os.path.splitext(filepath)[-1].lower()

    # Read with BOM handling
    with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
        text = f.read()

    if ext in {".json", ".jsonl", ".ndjson"}:
        return _parse_json_text(text)

    if ext in {".yaml", ".yml"}:
        try:
            docs = list(yaml.safe_load_all(text))
        except yaml.YAMLError as e:
            raise ValueError(f"YAML parse error: {e}") from e
        return _merge_docs([d if isinstance(d, dict) else {"value": d} for d in docs if d is not None])

    if ext == ".csv":
        result: Dict[str, float] = {}
        with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                for key, value in (row or {}).items():
                    fv = _to_float_or_none(value)
                    if fv is not None:
                        result[f"row{i}.{key.strip()}"] = fv
        return result

    if ext == ".xml":
        result: Dict[str, float] = {}
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
        except ET.ParseError as e:
            raise ValueError(f"XML parse error: {e}") from e

        def recurse(elem, parent=""):
            for child in elem:
                key = f"{parent}.{child.tag}" if parent else child.tag
                if list(child):
                    recurse(child, key)
                else:
                    fv = _to_float_or_none(child.text)
                    if fv is not None:
                        result[key] = fv

        recurse(root)
        return result

    raise ValueError(f"Unsupported structured file type: {ext}")
