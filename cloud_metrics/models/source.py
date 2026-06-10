# cloud_metrics/models/source.py

from sqlalchemy import Column, Integer, String, JSON, DateTime, func
from cloud_metrics.models.db_models import Base

class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True) # e.g. "aws_cloudwatch", "scaphandre"
    type = Column(String(64), nullable=False) # file, api, prometheus, opentelemetry, scaphandre, manual
    protocol = Column(String(64), nullable=True) # HTTP, gRPC, file, MQTT, etc.
    format = Column(String(64), nullable=True) # JSON, YAML, CSV, XML, Prometheus, OTLP
    schema_version = Column(String(64), nullable=True) # source schema version
    capabilities = Column(JSON, nullable=True, server_default='{}') # capability info (JSON list or object)
    auth_method = Column(String(64), nullable=False, default="none") # none, token, api_key, oauth2
    status = Column(String(64), nullable=False, default="active") # active, inactive, deprecated
    metadata_info = Column(JSON, nullable=True, server_default='{}') # rename metadata -> metadata_info because SQLAlchemy Base metadata is reserved!

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
