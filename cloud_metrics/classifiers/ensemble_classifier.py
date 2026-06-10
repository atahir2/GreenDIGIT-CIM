# cloud_metrics/classifiers/ensemble_classifier.py

from dataclasses import dataclass
from typing import Optional, Tuple
import re

from cloud_metrics.ingestion.semantic_classifier import classify_by_semantics
from cloud_metrics.classifiers.alias_classifier import guess_from_alias

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

_EMBED_MODEL = None

_WORD = re.compile(r"[A-Z]?[a-z]+|[0-9]+")

def _tokens(s: str) -> list[str]:
    return [t.lower() for t in _WORD.findall(s or "")]

@dataclass
class Decision:
    category: str
    subcategory: str
    short_key: str
    confidence: float
    rationale: str

def _rule_guess(toks: set[str]) -> Optional[Decision]:
    any_of = lambda *c: any(x in toks for x in c)

    # STORAGE
    if {"disk","volume","filesystem","fs","storage"} & toks:
        if {"read","reads","readops","readiops","readbytes","bytesread","ioread","iopsread"} & toks:
            return Decision("storage","disk","read_io",0.75,"rule:storage+read")
        if {"write","writes","writeops","writeiops","writebytes","byteswrite","iowrite","iopswrite"} & toks:
            return Decision("storage","disk","write_io",0.75,"rule:storage+write")
        if {"latency","msop","msecop","avgqlen"} & toks:
            return Decision("storage","disk","latency",0.70,"rule:storage+latency")
        return Decision("storage","disk","usage",0.65,"rule:storage+usage")

    # NETWORK
    if {"network","traffic","throughput","bandwidth","net","nic","eth"} & toks:
        if {"in","rx","ingress","receive","inbytes","inpackets"} & toks:
            return Decision("network","traffic","incoming",0.70,"rule:network+in")
        if {"out","tx","egress","transmit","outbytes","outpackets"} & toks:
            return Decision("network","traffic","outgoing",0.70,"rule:network+out")
        return Decision("network","traffic","incoming",0.60,"rule:network+default_in")

    # ENERGY
    if {"kwh","kilowatthour","energyconsumed","energyusage","consumption","consumed"} & toks:
        return Decision("energy","consumption","total",0.80,"rule:energy+kwh")
    if {"solar","pv","renewable"} & toks:
        return Decision("energy","renewable","solar",0.80,"rule:energy+solar")
    if {"power","watt","watts","kw"} & toks:
        return Decision("energy","power","total",0.70,"rule:energy+power")

    # ENVIRONMENT
    if {"temperature","temp","celsius"} & toks:
        # prefer ambient unless int/ext present
        if {"interior","indoor","int"} & toks:
            return Decision("environment","temperature","interior",0.70,"rule:env+temp+interior")
        if {"exterior","outdoor","ext"} & toks:
            return Decision("environment","temperature","exterior",0.70,"rule:env+temp+exterior")
        return Decision("environment","temperature","ambient",0.65,"rule:env+temp")

    # PERFORMANCE
    if {"cpu","processor"} & toks:
        return Decision("performance","cpu","utilization",0.70,"rule:perf+cpu")
    if {"memory","mem","ram"} & toks:
        return Decision("performance","memory","usage",0.70,"rule:perf+mem")

    return None

def _embed_guess(query: str, candidates: list[Tuple[str, Tuple[str,str,str]]]) -> Optional[Decision]:
    if SentenceTransformer is None:
        return None
    try:
        global _EMBED_MODEL
        if _EMBED_MODEL is None:
            _EMBED_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        q = _EMBED_MODEL.encode([query], normalize_embeddings=True)
        texts = [c[0] for c in candidates]
        embs = _EMBED_MODEL.encode(texts, normalize_embeddings=True)
        sims = (q @ embs.T)[0]
        best_i = int(sims.argmax())
        score = float(sims[best_i])
        cat, sub, short = candidates[best_i][1]

        # 0.60 is a decent default;
        if score >= 0.60:
            cat, sub, short = candidates[best_i][1]
            return Decision(cat, sub, short, score, f"embed:{score:.2f}→{texts[best_i]}")
    except Exception:
        return None
    return None

def classify_metric(raw_key: str) -> Decision:
    key = (raw_key or "").strip()
    toks = set(_tokens(key))

    # 0) check Mapping Registry first
    from cloud_metrics.services.mapping_registry_service import resolve_mapping
    try:
        mapping = resolve_mapping(key)
        if mapping:
            parts = mapping.cim_metric.unified_key.split(".")
            if len(parts) >= 4:
                return Decision(parts[1], parts[2], parts[3], mapping.confidence, mapping.rationale or "Mapping Registry resolution")
    except Exception as e:
        # Avoid crashing if database is not available (e.g. during standalone tests)
        pass

    # 0) exact semantic map (your existing function)
    sem = classify_by_semantics(raw_key)
    if sem:
        _, domain, category, metric = sem
        return Decision(domain, category, metric, 0.90, "semantic-map")

    # 1) fuzzy alias
    hit = guess_from_alias(key, cutoff=88)
    if hit:
        return Decision(hit.category, hit.subcategory, hit.short_key, max(0.85, hit.score/100.0), f"alias:{hit.matched_alias}")

    # 2) rules
    ruled = _rule_guess(toks)
    if ruled:
        return ruled

    # 3) optional embeddings — compare against a small set of canonical prompts
    # Keep this list short at first; you can expand or load from DB later.
    CANDIDATES = [
        ("storage read io", ("storage","disk","read_io")),
        ("storage write io", ("storage","disk","write_io")),
        ("storage latency", ("storage","disk","latency")),
        ("storage usage", ("storage","disk","usage")),
        ("network traffic incoming", ("network","traffic","incoming")),
        ("network traffic outgoing", ("network","traffic","outgoing")),
        ("energy consumption kwh total", ("energy","consumption","total")),
        ("energy power total", ("energy","power","total")),
        ("solar renewable energy", ("energy","renewable","solar")),
        ("environment ambient temperature", ("environment","temperature","ambient")),
    ]
    emb = _embed_guess(key, CANDIDATES)
    if emb:
        return emb

    return Decision("uncategorized","unknown","unknown",0.0,"none")
