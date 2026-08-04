"""Translate legacy ``gd.*`` unified keys to canonical ``cim:*`` namespaces.

When a trusted exact or close mapping exists against an approved Milestone 3
metric, the CIM namespace is returned. Otherwise ``None`` signals that a
candidate metric definition should be created from the ``gd.*`` key.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

# Explicit legacy gd.* → approved cim:* alignments.
# Keys not listed (or mapped to None via resolve) become candidates.
GD_TO_CIM: Dict[str, str] = {
    "gd.energy.power.total": "cim:energy.power.total",
    "gd.energy.consumption.total": "cim:energy.consumption.total",
    "gd.energy.efficiency.pue": "cim:energy.efficiency.pue",
    "gd.environment.emissions.cfp": "cim:carbon.emission.operational",
    "gd.environment.emissions.ci": "cim:carbon.intensity.location_based",
    "gd.environment.emissions.carbon_intensity": "cim:carbon.intensity.location_based",
    "gd.environment.water.wue": "cim:energy.efficiency.wue",
    "gd.network.traffic.incoming": "cim:network.traffic.ingress",
    "gd.network.traffic.outgoing": "cim:network.traffic.egress",
    "gd.performance.cpu.utilization": "cim:compute.cpu.utilisation",
    "gd.performance.memory.usage": "cim:compute.memory.usage",
    "gd.performance.time.wallclock": "cim:workflow.execution.duration",
    "gd.storage.disk.usage": "cim:storage.capacity.used",
}

# Known gd.* keys that intentionally become candidates (no silent approve).
CANDIDATE_GD_KEYS = frozenset(
    {
        "gd.energy.renewable.solar",
        "gd.environment.temperature.exterior",
        "gd.environment.temperature.interior",
        "gd.environment.temperature.ambient",
        "gd.network.traffic.total_bytes",
        "gd.performance.cpu.count",
        "gd.performance.cpu.normalization_factor",
        "gd.performance.cpu.tdp",
        "gd.performance.cpu.time",
        "gd.performance.cpu.time_normalized",
        "gd.performance.cpu.time_scaled",
        "gd.performance.efficiency.compute",
        "gd.performance.time.suspend",
        "gd.performance.work.total",
        "gd.storage.disk.read_io",
        "gd.storage.disk.write_io",
        "gd.storage.disk.latency",
        "gd.uncategorized.unknown.unknown",
    }
)


def gd_to_candidate_cim(gd_key: str) -> str:
    """Derive a candidate ``cim:*`` namespace from a ``gd.*`` key."""
    key = (gd_key or "").strip()
    if key.startswith("gd."):
        return "cim:" + key[3:]
    if key.startswith("cim:"):
        return key
    return f"cim:extension.{key.replace('.', '_')}"


def resolve_cim_namespace(gd_or_cim: str) -> Tuple[str, bool]:
    """Return ``(cim_namespace, is_trusted_alignment)``.

    ``is_trusted_alignment`` is True only when the target is an explicit
    ``GD_TO_CIM`` entry (expected to already exist as an approved seed metric).
    """
    key = (gd_or_cim or "").strip()
    if not key:
        return "cim:extension.unknown", False
    if key.startswith("cim:"):
        return key, key in set(GD_TO_CIM.values())
    if key in GD_TO_CIM:
        return GD_TO_CIM[key], True
    return gd_to_candidate_cim(key), False


def triple_to_gd(category: str, subcategory: str, short_key: str) -> str:
    return f"gd.{category}.{subcategory}.{short_key}"
