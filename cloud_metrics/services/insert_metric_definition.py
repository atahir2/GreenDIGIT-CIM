# cloud_metrics/services/insert_metric_definition.py

from sqlalchemy.exc import IntegrityError
from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.models.metric_definition import MetricDefinition

def insert_metric_definition(unified_key: str, tags: list[str] = None, sources: list[str] = None):
    session = SessionLocal()
    try:
        metric = MetricDefinition(
            unified_key=unified_key,
            tags=tags or [],
            sources=sources or []
        )
        session.add(metric)
        session.commit()
        print(f"✅ Metric definition '{unified_key}' inserted successfully.")
    except IntegrityError:
        session.rollback()
        print(f"⚠️ Metric definition '{unified_key}' already exists.")
    except Exception as e:
        session.rollback()
        print(f"❌ Error inserting metric definition: {e}")
    finally:
        session.close()
