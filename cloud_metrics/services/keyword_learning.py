# cloud_metrics/services/keyword_learning.py
from datetime import datetime
from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.models.metric_keyword import MetricKeyword

def learn_keyword(raw_key: str, category: str, subcategory: str, short_key: str, confidence: float):
    raw = raw_key.strip().lower()
    with SessionLocal() as s:
        mk = (
            s.query(MetricKeyword)
            .filter((MetricKeyword.keyword == raw) | (MetricKeyword.source_key == raw))
            .first()
        )
        if mk:
            # Only improve; don't downgrade existing good entries
            if mk.category != category or mk.subcategory != subcategory or mk.short_key != short_key:
                mk.category = category
                mk.subcategory = subcategory
                mk.short_key = short_key
            mk.updated_at = datetime.utcnow()
        else:
            mk = MetricKeyword(
                keyword=raw,
                source_key=raw,
                category=category,
                subcategory=subcategory,
                short_key=short_key,
            )
            s.add(mk)
        s.commit()
