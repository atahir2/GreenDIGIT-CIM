# cloud_metrics/ingestion/semantic_classifier.py

# A precise standards-based mapping for specific known raw metric keys
# This mapping ensures no overlap or ambiguity

STANDARDS_MAP = {
    "elec.power":      ("iso", "energy",      "power",      "total"),
    "power.solar":     ("iso", "energy",      "renewable",  "solar"),
    "disk.readio":     ("iso", "storage",     "disk",       "read_io"),
    "disk.writeio":    ("iso", "storage",     "disk",       "write_io"),
    "env.internaltemp":("jrc", "environment", "temperature","internal"),
    "env.externaltemp":("jrc", "environment", "temperature","external"),
    "cpu.usage":       ("iso", "performance", "cpu",        "utilization"),
    "memory.used":     ("iso", "performance", "memory",     "usage"),
    "network.in":      ("iso", "network",     "traffic",    "incoming"),
    "network.out":     ("iso", "network",     "traffic",    "outgoing"),
}

def classify_by_semantics(raw_key: str):
    """
    Normalize the raw key (strip spaces, dashes, underscores, case),
    then check if it ends with any of the standardized suffixes.
    Returns a 4-tuple (organization, domain, category, metric) or None.
    """
    key = raw_key.lower().replace(" ", "").replace("-", "").replace("_", "")
    for k, mapping in STANDARDS_MAP.items():
        if key.endswith(k.replace(".", "")):  # loose match on normalized key
            return mapping
    return None
