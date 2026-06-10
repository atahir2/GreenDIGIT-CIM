# cloud_metrics/classifiers/fallbacks.py


import re
_WORD = re.compile(r"[A-Z]?[a-z]+|[0-9]+")

def _tokens(s: str) -> list[str]:
    return [t.lower() for t in _WORD.findall(s or "")]

def fallback_namespace_from_raw(raw_key: str, unit_hint: str | None = None) -> tuple[str,str,str]:
    """
    Last-resort taxonomy when classifier fails.
    Heuristics:
      - single acronym like 'pue'/'cfp' -> known buckets
      - unit hints steer category
      - otherwise slug tokens: cat=sub=first token, short=last
    """
    short = "".join(_tokens(raw_key)) or "unknown"
    return "custom", "unknown", short

    t = _tokens(raw_key)
    slug = lambda s: "".join(_tokens(s)) or "unknown"

    if len(t) == 1:
        a = t[0]
        # well-known DC acronyms
        if a == "pue":
            return "energy","efficiency","pue"
        if a in {"cfp","co2e","co2eq"}:
            return "environment","emissions",a
        # unknown acronym → put under 'custom'
        return "custom","unknown",a

    # unit-driven nudges
    unit = (unit_hint or "").lower()
    if unit in {"kwh","kw","w"}:
        return "energy","power","total"
    if unit in {"bps","mbps","gbps"}:
        return "network","traffic","throughput"
    if unit in {"ops","iops","bytes"} and any(x in t for x in ("disk","volume","fs","storage")):
        return "storage","disk","usage"

    # general slugging: first token as category, second as subcat, last as short
    cat  = t[0]
    sub  = t[1] if len(t) > 1 else "unknown"
    short= t[-1]
    # keep categories sane; collapse weird ones to 'custom'
    if cat not in {"energy","environment","network","storage","performance"}:
        cat = "custom"
    return cat, sub, short
