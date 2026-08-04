# cloud_metrics/classifiers/alias_classifier.py

from dataclasses import dataclass
from typing import Optional
import re

_WORD = re.compile(r"[A-Z]?[a-z]+|[0-9]+")

def _norm(s: str) -> str:
    """Tokenize camelCase/underscores/dots and lower-case: 'NetworkIn.Bytes' -> 'network in bytes'."""
    return " ".join(t.lower() for t in _WORD.findall(s or ""))

@dataclass
class AliasHit:
    category: str
    subcategory: str
    short_key: str
    score: float
    matched_alias: str

# canonical -> list of aliases
ALIASES = {
    # Energy
    ("energy", "consumption", "total"): [
        "energy_wh", "energy_kwh", "kilowatt_hours", "kwh_total", "energy_consumed", "energy_usage", "total_energy_wh", "total_energy_kwh",
    ],
    ("energy", "power", "total"): [
        "active_power", "electric_power", "kw_total", "wattage",
    ],
    ("energy", "renewable", "solar"): [
        "solar", "solar_power", "pv", "photovoltaic",
    ],
    ("energy", "efficiency", "pue"): [
        "pue", "power_usage_effectiveness", "power-usage-effectiveness", "dc_pue", "data_center_pue"
    ],
    # Network
    ("network", "traffic", "incoming"): [
        "network_in", "ingress_bytes", "rx_bytes", "receive_bytes", "in_packets",
    ],
    ("network", "traffic", "outgoing"): [
        "network_out", "egress_bytes", "tx_bytes", "transmit_bytes", "out_packets",
    ],
    ("network", "traffic", "total_bytes"): [
        "amountofdatatransferred", "bytes_transferred", "data_bytes", "total_bytes","traffic_bytes", "traffic",
    ],
    # Storage
    ("storage", "disk", "read_io"): [
        "disk_read_ops", "read_iops", "reads_completed", "read_bytes", "volume_read_bytes", "fs_reads",
    ],
    ("storage", "disk", "write_io"): [
        "disk_write_ops", "write_iops", "writes_completed", "write_bytes", "volume_write_bytes", "fs_writes",
    ],
    ("storage", "disk", "latency"): [
        "disk_latency", "avg_read_latency", "avg_write_latency", "ms_per_op", "avg_queue_len", "avgqlen",
    ],
    ("storage", "disk", "usage"): [
        "disk_usage", "disk_used", "capacity_used", "filesystem_used", "volume_total_bytes", "volume_available_bytes",
    ],
    # Environment
    ("environment", "temperature", "interior"): [
        "interior_temperature", "indoor_temperature", "temp_interior", "temp_indoor", "temp_int",
    ],
    ("environment", "temperature", "exterior"): [
        "exterior_temperature", "outdoor_temperature", "temp_exterior", "temp_outdoor", "temp_ext",
    ],
    ("environment", "temperature", "ambient"): [
        "ambient_temperature", "temp_ambient", "temp_room",
    ],
    ("environment","water","wue"): [
        "wue", "water_usage_effectiveness", "water-usage-effectiveness", "dc_wue", "data_center_wue"
    ],
    ("environment","emissions","cfp"): [
        "cfp", "cfp_g", "carbon_footprint", "co2e", "co2eq", "ghg_emissions", "carbon_emissions"
    ],
    ("environment","emissions","ci"): [
        "ci", "ci_g", "carbon_intensity",
    ],
    #Performance
    ("performance","work","total"): [
        "work", "work_total",
    ],
    ("performance","time","wallclock"): [
        "wallclocktime_s","walltime_s", "wallclock", "wall_clock",
    ],
    ("performance","time","suspend"): [
        "suspendduration_s", "suspend_duration", "suspend",
    ],
    ("performance","cpu","time"): [
        "cpuduration_s","totalcputime_s", "cpu_time", "cputime",
    ],
    ("performance","cpu","normalization_factor"): [
        "cpunormalizationfactor", "normalization_factor",
    ],
    ("performance","efficiency","compute"): [
        "efficiency", "compute",
    ],
    # Grid
    ("performance","cpu","count"): [
        "ncores","cores"],
    ("performance","cpu","tdp"): [
        "tdp_w"],
    ("performance","cpu","time_normalized"): [
        "normcputime_s"],
    ("performance","cpu","time_scaled"): [
        "scaledcputime_s"],
}

# flatten lookup list
_CANDIDATES = []
_ALIAS_TO_TRIPLE = {}
for triple, names in ALIASES.items():
    for n in names:
        nn = _norm(n)
        _CANDIDATES.append(nn)
        _ALIAS_TO_TRIPLE[nn] = triple

def guess_from_alias(raw_key: str, cutoff: int = 88) -> Optional[AliasHit]:
    """
        Fuzzy map raw_key to a canonical (category, subcategory, short_key).
        Returns None if no alias clears the cutoff.
        Uses normalized strings for robust matching.
    """
    if not raw_key:
        return None

    q = _norm(raw_key)

    try:
        from rapidfuzz import process, fuzz
    except ImportError:
        # Exact normalized match without RapidFuzz (dev/test environments).
        triple = _ALIAS_TO_TRIPLE.get(q)
        if triple is None:
            return None
        c, s, k = triple
        return AliasHit(c, s, k, 100.0, matched_alias=q)

    # search across alias names
    match = process.extractOne(
        q,
        _CANDIDATES,
        scorer=fuzz.WRatio,
        score_cutoff=cutoff
    )
    if not match:
        return None

    alias_norm, score, _ = match  # name, score, index
    c, s, k = _ALIAS_TO_TRIPLE[alias_norm]
    return AliasHit(c, s, k, float(score), matched_alias=alias_norm)
