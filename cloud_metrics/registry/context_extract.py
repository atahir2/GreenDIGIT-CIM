"""Extract source / asset hints from free-form ingestion metadata.

Does not invent hierarchy. Only returns fields present (or safely aliased)
in the incoming metadata dict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional


def _first(meta: Mapping[str, Any], *keys: str) -> Optional[str]:
    if not meta:
        return None
    # exact
    for k in keys:
        if k in meta and meta[k] is not None and str(meta[k]).strip():
            return str(meta[k]).strip()
    # case-insensitive
    low = {str(k).lower(): v for k, v in meta.items()}
    for k in keys:
        v = low.get(k.lower())
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


def _nested(meta: Mapping[str, Any]) -> Dict[str, Any]:
    """Flatten one level of nested ``labels`` / ``metadata`` / ``resource`` dicts."""
    out: Dict[str, Any] = dict(meta)
    for nest_key in ("labels", "metadata", "resource", "attributes", "tags"):
        nested = meta.get(nest_key)
        if isinstance(nested, Mapping):
            for k, v in nested.items():
                out.setdefault(k, v)
    return out


# ---------------------------------------------------------------------------
# Source hints
# ---------------------------------------------------------------------------

_SOURCE_TYPE_ALIASES = {
    "file": "file",
    "file_upload": "file",
    "upload": "file",
    "api": "api",
    "rest": "api",
    "http": "api",
    "monitoring": "monitoring_system",
    "monitoring_system": "monitoring_system",
    "prometheus": "monitoring_system",
    "opentelemetry": "monitoring_system",
    "otel": "monitoring_system",
    "scaphandre": "monitoring_system",
    "cloudwatch": "cloud_api",
    "aws_cloudwatch": "cloud_api",
    "gcp_monitoring": "cloud_api",
    "cloud_api": "cloud_api",
    "workflow": "workflow_engine",
    "workflow_engine": "workflow_engine",
    "manual": "manual_input",
    "manual_input": "manual_input",
    "database": "database",
    "db": "database",
}


@dataclass
class SourceHints:
    name: Optional[str] = None
    type: Optional[str] = None
    ingestion_method: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0


def normalize_source_type(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    key = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    return _SOURCE_TYPE_ALIASES.get(key, key)


def extract_source_hints(metadata: Optional[Mapping[str, Any]]) -> SourceHints:
    """Infer source name/type from ingestion metadata (Prometheus-like, file, API)."""
    if not metadata:
        return SourceHints(confidence=0.0)
    m = _nested(dict(metadata))

    name = _first(
        m,
        "source",
        "source_name",
        "source_system",
        "exporter",
        "job",
        "api_name",
        "collector",
    )
    file_name = _first(m, "file_name", "filename", "file")
    api_name = _first(m, "api_name", "api")
    source_type_raw = _first(m, "source_type", "type")
    ingestion = _first(m, "ingestion_method", "ingest_method", "protocol")

    # Infer type when missing
    inferred_type = normalize_source_type(source_type_raw)
    confidence = 0.5
    if inferred_type:
        confidence = 0.85
    elif file_name:
        inferred_type = "file"
        name = name or file_name
        confidence = 0.8
    elif api_name:
        inferred_type = "api"
        name = name or api_name
        confidence = 0.8
    elif _first(m, "job", "instance", "__name__"):
        # Prometheus-like scrape labels
        inferred_type = "monitoring_system"
        name = name or _first(m, "job") or "prometheus"
        confidence = 0.75
    elif _first(m, "service.name", "telemetry.sdk.name"):
        inferred_type = "monitoring_system"
        name = name or _first(m, "service.name") or "opentelemetry"
        confidence = 0.7

    if not name and inferred_type:
        name = inferred_type

    extra = {
        k: v
        for k, v in m.items()
        if k
        not in {
            "source",
            "source_name",
            "source_system",
            "source_type",
            "type",
            "exporter",
            "file_name",
            "filename",
            "file",
            "api_name",
            "api",
            "ingestion_method",
            "ingest_method",
            "protocol",
        }
    }

    return SourceHints(
        name=name,
        type=inferred_type,
        ingestion_method=ingestion,
        metadata=extra,
        confidence=confidence if name else 0.0,
    )


# ---------------------------------------------------------------------------
# Asset hints
# ---------------------------------------------------------------------------


@dataclass
class AssetHints:
    """Ordered from root → leaf where known; only populated fields are used."""

    site: Optional[str] = None
    data_centre: Optional[str] = None
    cluster: Optional[str] = None
    rack: Optional[str] = None
    node: Optional[str] = None
    server: Optional[str] = None
    cpu: Optional[str] = None
    gpu: Optional[str] = None
    virtual_machine: Optional[str] = None
    container: Optional[str] = None
    service: Optional[str] = None
    workflow: Optional[str] = None
    workflow_run: Optional[str] = None
    dataset: Optional[str] = None
    experiment: Optional[str] = None
    primary_type: Optional[str] = None
    primary_identifier: Optional[str] = None
    confidence: float = 0.0
    raw: Dict[str, Any] = field(default_factory=dict)


def extract_asset_hints(metadata: Optional[Mapping[str, Any]]) -> AssetHints:
    """Infer asset identifiers from common label / partner metadata keys."""
    if not metadata:
        return AssetHints(confidence=0.0)
    m = _nested(dict(metadata))

    hints = AssetHints(
        site=_first(m, "site", "site_id", "site_name"),
        data_centre=_first(
            m, "data_centre", "datacenter", "data_center", "dc", "dc_name"
        ),
        cluster=_first(m, "cluster", "cluster_id", "cluster_name"),
        rack=_first(m, "rack", "rack_id"),
        node=_first(m, "node", "node_id", "host", "hostname", "server"),
        server=_first(m, "server", "server_id"),
        cpu=_first(m, "cpu", "cpu_id"),
        gpu=_first(m, "gpu", "gpu_id", "gpu_uuid"),
        virtual_machine=_first(m, "vm", "vm_id", "virtual_machine"),
        container=_first(m, "container", "container_id", "pod"),
        service=_first(m, "service", "service_name", "service.name"),
        workflow=_first(m, "workflow", "workflow_id", "workflow_name"),
        workflow_run=_first(m, "workflow_run", "workflow_run_id", "run_id"),
        dataset=_first(m, "dataset", "dataset_id"),
        experiment=_first(m, "experiment", "experiment_id"),
        raw=dict(m),
    )

    # Prefer most specific leaf as primary
    leaf_order = [
        ("gpu", hints.gpu),
        ("cpu", hints.cpu),
        ("workflow_run", hints.workflow_run),
        ("container", hints.container),
        ("virtual_machine", hints.virtual_machine),
        ("service", hints.service),
        ("node", hints.node),
        ("server", hints.server),
        ("rack", hints.rack),
        ("cluster", hints.cluster),
        ("workflow", hints.workflow),
        ("dataset", hints.dataset),
        ("experiment", hints.experiment),
        ("data_centre", hints.data_centre),
        ("site", hints.site),
    ]
    for typ, ident in leaf_order:
        if ident:
            hints.primary_type = typ
            hints.primary_identifier = ident
            break

    filled = sum(
        1
        for v in (
            hints.site,
            hints.data_centre,
            hints.cluster,
            hints.rack,
            hints.node,
            hints.server,
            hints.cpu,
            hints.gpu,
            hints.virtual_machine,
            hints.container,
            hints.service,
            hints.workflow,
            hints.workflow_run,
            hints.dataset,
            hints.experiment,
        )
        if v
    )
    hints.confidence = min(0.95, 0.4 + 0.1 * filled) if filled else 0.0
    return hints
