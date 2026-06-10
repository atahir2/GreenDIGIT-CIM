from __future__ import annotations

from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.utils.unified_key import to_gd
from cloud_metrics.registry.namespace_registry import ensure_gd_namespace
from cloud_metrics.services.insert_mapped_metric import insert_mapped_metric
from cloud_metrics.services.keyword_learning import learn_keyword
from cloud_metrics.services.standards_registry import ensure_seed_standards, attach_standard

# 1) unified keys to seed (taxonomy + definition)
UNIFIED_KEYS = [
    # Cloud + Grid
    "gd.environment.emissions.cfp",
    "gd.environment.emissions.carbon_intensity",
    "gd.energy.consumption.total",
    "gd.energy.efficiency.pue",
    "gd.performance.work.total",
    "gd.performance.time.wallclock",
    "gd.performance.time.suspend",
    "gd.performance.cpu.time",
    "gd.performance.cpu.normalization_factor",
    "gd.performance.efficiency.compute",

    # Grid extras
    "gd.performance.cpu.count",
    "gd.performance.cpu.tdp",
    "gd.performance.cpu.time_normalized",
    "gd.performance.cpu.time_scaled",

    # Network
    "gd.network.traffic.total_bytes",
]

# 2) alias seeds (fast path keyword-to-taxonomy)
ALIAS_SEEDS = {
    # cloud/grid
    "pue":                        "gd.energy.efficiency.pue",
    "cfp_g":                      "gd.environment.emissions.cfp",
    "ci_g":                       "gd.environment.emissions.carbon_intensity",
    "energy_wh":                  "gd.energy.consumption.total",
    "energy_kwh":                 "gd.energy.consumption.total",
    "work":                       "gd.performance.work.total",
    "wallclocktime_s":            "gd.performance.time.wallclock",
    "suspendduration_s":          "gd.performance.time.suspend",
    "cpuduration_s":              "gd.performance.cpu.time",
    "cpunormalizationfactor":     "gd.performance.cpu.normalization_factor",
    "efficiency":                 "gd.performance.efficiency.compute",

    # grid-only extras
    "ncores":                     "gd.performance.cpu.count",
    "tdp_w":                      "gd.performance.cpu.tdp",
    "normcputime_s":              "gd.performance.cpu.time_normalized",
    "totalcputime_s":             "gd.performance.cpu.time",
    "scaledcputime_s":            "gd.performance.cpu.time_scaled",

    # network
    "amountofdatatransferred":    "gd.network.traffic.total_bytes",
    "bytes_transferred":          "gd.network.traffic.total_bytes",
    "data_bytes":                 "gd.network.traffic.total_bytes",
}

def seed():
    # ensuring standard catalog exists
    ensure_seed_standards()

    # ensuring taxonomy + metric_definitions
    for uk in UNIFIED_KEYS:
        parts = uk.split(".")
        assert parts[0] == "gd" and len(parts) >= 4, f"Bad unified key: {uk}"
        _, cat, sub, short = parts[:4]

        # creating taxonomy rows (auto_create)
        unresolved = ensure_gd_namespace(cat, sub, short, auto_create=True)

        # create metric_definition (and attach standards)
        insert_mapped_metric(unified_key=unresolved, source_keys=[], tags=[cat, sub, short])

    # learn the common raw aliases (so first sight is O(1))
    for raw, uk in ALIAS_SEEDS.items():
        parts = uk.split(".")
        _, cat, sub, short = parts[:4]
        learn_keyword(raw, cat, sub, short, confidence=0.99)

    print("Seed complete.")

if __name__ == "__main__":
    seed()
