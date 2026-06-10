# cloud_metrics/parsers/unstructured_parser.py

import re

def parse_unstructured_text(text: str, datacenter: str = "naive") -> dict:
    """
    Parse paragraph-style unstructured text to extract known metrics and their values.
    Returns a dict of {datacenter.metric_name: value}.
    """
    patterns = {
        "cpu": r"cpu.*?(?:usage)?(?:reached|at|is)?[^\d]*(\d+(?:\.\d+)?)\s*%",
        "memory": r"memory.*?(?:used|usage)?(?:was|at|is)?[^\d]*(\d+(?:\.\d+)?)\s*(?:gb|g|gigabytes)?",
        "power": r"power.*?(?:usage|consumption)?(?:was|is|hit)?[^\d]*(\d+(?:\.\d+)?)\s*(?:w|watts)?",
        "network.in": r"network.*?(?:in|incoming).*?(?:was|at)?[^\d]*(\d+(?:\.\d+)?)\s*(?:mbps|m/bits)?",
        "network.out": r"network.*?(?:out|outgoing).*?(?:was|reached)?[^\d]*(\d+(?:\.\d+)?)\s*(?:mbps|m/bits)?",
        "temperature": r"temperature.*?(?:was|reached|peaked)?[^\d]*(\d+(?:\.\d+)?)\s*(?:°c|celsius|c)?"
    }

    extracted = {}
    lowered = text.lower()

    for key, pattern in patterns.items():
        match = re.search(pattern, lowered)
        if match:
            try:
                value = float(match.group(1))
                metric_key = f"{datacenter}.{key}"
                extracted[metric_key] = value
            except:
                pass

    return extracted
