# cloud_metrics/scripts/create_schema.py

from sqlalchemy import inspect

from cloud_metrics.utils.config import _engine
from cloud_metrics.models import standard_models   # registers Standard / MetricStandardMap
from cloud_metrics.models import namespace_models  # registers Category/Subcategory/etc.
from cloud_metrics.models import metric_definition # registers MetricDefinition
from cloud_metrics.models import Base
import cloud_metrics.models
from sqlalchemy.orm import configure_mappers
configure_mappers()


def main():
    print("Creating all tables…")
    Base.metadata.create_all(bind=_engine)

    insp = inspect(_engine)
    tables = ", ".join(sorted(insp.get_table_names()))
    print(f"✅ Done. Tables present: {tables}")

if __name__ == "__main__":
    main()
