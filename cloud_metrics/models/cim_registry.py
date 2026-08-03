"""SQLAlchemy models for the Milestone 2 registry-driven CIM tables.

These ``cim_*`` tables are additive. They coexist with legacy / Antigravity
tables (``metric_definitions``, ``units``, ``sources``, ``cim_mappings``, etc.)
and are not wired into ingestion in this milestone.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declared_attr, relationship

from cloud_metrics.models.db_models import Base


class CimGovernanceMixin:
    """Common governance columns for registry entries."""

    @declared_attr
    def status(cls):
        # draft | candidate | approved | rejected | deprecated | retired | active
        return Column(String(64), nullable=False, server_default="draft")

    @declared_attr
    def review_status(cls):
        # pending | under_review | approved | rejected
        return Column(String(64), nullable=False, server_default="pending")

    @declared_attr
    def confidence_score(cls):
        return Column(Float, nullable=True)

    @declared_attr
    def version(cls):
        return Column(Integer, nullable=False, server_default="1")

    @declared_attr
    def created_at(cls):
        return Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )

    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        )

    @declared_attr
    def created_by(cls):
        return Column(String(128), nullable=True)

    @declared_attr
    def notes(cls):
        return Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Unit / Quantity Kind
# ---------------------------------------------------------------------------


class CimQuantityKind(CimGovernanceMixin, Base):
    __tablename__ = "cim_quantity_kinds"
    __table_args__ = (
        UniqueConstraint("name", name="uq_cim_quantity_kinds_name"),
        Index("ix_cim_quantity_kinds_status", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    description = Column(String(512), nullable=True)
    qudt_uri = Column(String(256), nullable=True)

    units = relationship(
        "CimUnit",
        back_populates="quantity_kind",
        foreign_keys="CimUnit.quantity_kind_id",
    )


class CimUnit(CimGovernanceMixin, Base):
    __tablename__ = "cim_units"
    __table_args__ = (
        UniqueConstraint("symbol", name="uq_cim_units_symbol"),
        Index("ix_cim_units_quantity_kind_id", "quantity_kind_id"),
        Index("ix_cim_units_status", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False)
    quantity_kind_id = Column(
        Integer,
        ForeignKey(
            "cim_quantity_kinds.id",
            name="fk_cim_units_quantity_kind_id_cim_quantity_kinds",
        ),
        nullable=False,
    )
    si_base = Column(Boolean, nullable=False, server_default="0")
    canonical_unit_id = Column(
        Integer,
        ForeignKey("cim_units.id", name="fk_cim_units_canonical_unit_id_cim_units"),
        nullable=True,
    )
    conversion_factor = Column(Float, nullable=False, server_default="1.0")
    conversion_offset = Column(Float, nullable=False, server_default="0.0")
    qudt_uri = Column(String(256), nullable=True)
    saref_uri = Column(String(256), nullable=True)

    quantity_kind = relationship(
        "CimQuantityKind",
        back_populates="units",
        foreign_keys=[quantity_kind_id],
    )
    canonical_unit = relationship(
        "CimUnit",
        remote_side="CimUnit.id",
        foreign_keys=[canonical_unit_id],
    )


# ---------------------------------------------------------------------------
# Source / Asset / Lifecycle (lifecycle before asset FK)
# ---------------------------------------------------------------------------


class CimSource(CimGovernanceMixin, Base):
    __tablename__ = "cim_sources"
    __table_args__ = (
        UniqueConstraint("name", "type", name="uq_cim_sources_name_type"),
        Index("ix_cim_sources_type", "type"),
        Index("ix_cim_sources_status", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    type = Column(String(64), nullable=False)
    protocol = Column(String(64), nullable=True)
    format = Column(String(64), nullable=True)
    schema_version = Column(String(64), nullable=True)
    capabilities = Column(JSON, nullable=True, server_default="{}")
    auth_method = Column(String(64), nullable=False, server_default="none")
    metadata_info = Column(JSON, nullable=True, server_default="{}")


class CimLifecycleStage(CimGovernanceMixin, Base):
    __tablename__ = "cim_lifecycle_stages"
    __table_args__ = (
        UniqueConstraint("name", name="uq_cim_lifecycle_stages_name"),
        UniqueConstraint("stage_key", name="uq_cim_lifecycle_stages_stage_key"),
        Index("ix_cim_lifecycle_stages_sequence", "sequence"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    stage_key = Column(String(64), nullable=False)
    label = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    sequence = Column(Integer, nullable=True)


class CimAsset(CimGovernanceMixin, Base):
    __tablename__ = "cim_assets"
    __table_args__ = (
        UniqueConstraint(
            "identifier", "type", name="uq_cim_assets_identifier_type"
        ),
        Index("ix_cim_assets_name", "name"),
        Index("ix_cim_assets_type", "type"),
        Index("ix_cim_assets_parent_id", "parent_id"),
        Index("ix_cim_assets_status", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(255), nullable=False)
    name = Column(String(128), nullable=False)
    type = Column(String(64), nullable=False)
    parent_id = Column(
        Integer,
        ForeignKey("cim_assets.id", name="fk_cim_assets_parent_id_cim_assets"),
        nullable=True,
    )
    location = Column(String(256), nullable=True)
    provider = Column(String(128), nullable=True)
    specifications = Column(JSON, nullable=True, server_default="{}")
    lifecycle_stage_id = Column(
        Integer,
        ForeignKey(
            "cim_lifecycle_stages.id",
            name="fk_cim_assets_lifecycle_stage_id_cim_lifecycle_stages",
        ),
        nullable=True,
    )

    parent = relationship("CimAsset", remote_side="CimAsset.id", backref="children")


# ---------------------------------------------------------------------------
# Standards
# ---------------------------------------------------------------------------


class CimStandard(CimGovernanceMixin, Base):
    __tablename__ = "cim_standards"
    __table_args__ = (
        # External catalogue identity (code + published version string)
        UniqueConstraint(
            "code",
            "standard_version",
            name="uq_cim_standards_code_standard_version",
        ),
        UniqueConstraint(
            "name",
            "standard_version",
            name="uq_cim_standards_name_standard_version",
        ),
        Index("ix_cim_standards_status", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(128), nullable=False)
    name = Column(String(255), nullable=False)
    # External published version (e.g. "2022", "1.1"); mixin ``version`` is
    # the integer registry-row version for governance.
    standard_version = Column(String(64), nullable=True)
    url = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    vocabulary_type = Column(String(64), nullable=True)
    namespace_prefix = Column(String(64), nullable=True)
    namespace_uri = Column(String(512), nullable=True)
    domain = Column(String(64), nullable=True)

    terms = relationship(
        "CimStandardTerm", back_populates="standard", cascade="all, delete-orphan"
    )


class CimStandardTerm(CimGovernanceMixin, Base):
    __tablename__ = "cim_standard_terms"
    __table_args__ = (
        UniqueConstraint(
            "standard_id", "term_code", name="uq_cim_standard_terms_standard_term"
        ),
        Index("ix_cim_standard_terms_standard_id", "standard_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    standard_id = Column(
        Integer,
        ForeignKey(
            "cim_standards.id",
            name="fk_cim_standard_terms_standard_id_cim_standards",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    term_code = Column(String(128), nullable=False)
    term_label = Column(String(255), nullable=True)
    term_uri = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)

    standard = relationship("CimStandard", back_populates="terms")


# ---------------------------------------------------------------------------
# Metrics / Mappings
# ---------------------------------------------------------------------------


class CimMetricDefinition(CimGovernanceMixin, Base):
    __tablename__ = "cim_metric_definitions"
    __table_args__ = (
        UniqueConstraint("namespace", name="uq_cim_metric_definitions_namespace"),
        Index("ix_cim_metric_definitions_domain", "domain"),
        Index("ix_cim_metric_definitions_status", "status"),
        Index("ix_cim_metric_definitions_review_status", "review_status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    namespace = Column(String(255), nullable=False)
    label = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    domain = Column(String(64), nullable=True)
    category = Column(String(128), nullable=True)
    subcategory = Column(String(128), nullable=True)
    quantity_kind_id = Column(
        Integer,
        ForeignKey(
            "cim_quantity_kinds.id",
            name="fk_cim_metric_definitions_quantity_kind_id_cim_quantity_kinds",
        ),
        nullable=True,
    )
    canonical_unit_id = Column(
        Integer,
        ForeignKey(
            "cim_units.id",
            name="fk_cim_metric_definitions_canonical_unit_id_cim_units",
        ),
        nullable=True,
    )
    metric_type = Column(String(64), nullable=True)
    tags = Column(JSON, nullable=True, server_default="[]")
    sources = Column(JSON, nullable=True, server_default="[]")

    quantity_kind = relationship("CimQuantityKind", foreign_keys=[quantity_kind_id])
    canonical_unit = relationship("CimUnit", foreign_keys=[canonical_unit_id])


class CimMetricMapping(CimGovernanceMixin, Base):
    __tablename__ = "cim_metric_mappings"
    __table_args__ = (
        UniqueConstraint(
            "source_key",
            "source_id",
            name="uq_cim_metric_mappings_source_key_source_id",
        ),
        Index("ix_cim_metric_mappings_source_key", "source_key"),
        Index("ix_cim_metric_mappings_metric_id", "metric_id"),
        Index("ix_cim_metric_mappings_standard_id", "standard_id"),
        Index("ix_cim_metric_mappings_status", "status"),
        Index("ix_cim_metric_mappings_review_status", "review_status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_key = Column(String(255), nullable=False)
    source_id = Column(
        Integer,
        ForeignKey(
            "cim_sources.id",
            name="fk_cim_metric_mappings_source_id_cim_sources",
        ),
        nullable=True,
    )
    metric_id = Column(
        Integer,
        ForeignKey(
            "cim_metric_definitions.id",
            name="fk_cim_metric_mappings_metric_id_cim_metric_definitions",
        ),
        nullable=False,
    )
    standard_id = Column(
        Integer,
        ForeignKey(
            "cim_standards.id",
            name="fk_cim_metric_mappings_standard_id_cim_standards",
        ),
        nullable=True,
    )
    standard_term_id = Column(
        Integer,
        ForeignKey(
            "cim_standard_terms.id",
            name="fk_cim_metric_mappings_standard_term_id_cim_standard_terms",
        ),
        nullable=True,
    )
    relation_type = Column(String(64), nullable=False, server_default="underReview")
    rationale = Column(Text, nullable=True)
    origin = Column(String(64), nullable=False, server_default="manual")
    approved_by = Column(String(128), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    source = relationship("CimSource", foreign_keys=[source_id])
    metric = relationship("CimMetricDefinition", foreign_keys=[metric_id])
    standard = relationship("CimStandard", foreign_keys=[standard_id])
    standard_term = relationship("CimStandardTerm", foreign_keys=[standard_term_id])


class CimMetricLifecycleLink(CimGovernanceMixin, Base):
    __tablename__ = "cim_metric_lifecycle_links"
    __table_args__ = (
        UniqueConstraint(
            "metric_id",
            "lifecycle_stage_id",
            name="uq_cim_metric_lifecycle_links_metric_stage",
        ),
        Index("ix_cim_metric_lifecycle_links_metric_id", "metric_id"),
        Index(
            "ix_cim_metric_lifecycle_links_lifecycle_stage_id", "lifecycle_stage_id"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_id = Column(
        Integer,
        ForeignKey(
            "cim_metric_definitions.id",
            name="fk_cim_metric_lifecycle_links_metric_id_cim_metric_definitions",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    lifecycle_stage_id = Column(
        Integer,
        ForeignKey(
            "cim_lifecycle_stages.id",
            name="fk_cim_metric_lifecycle_links_lifecycle_stage_id_cim_lifecycle_stages",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    relevance = Column(String(64), nullable=False, server_default="primary")

    metric = relationship("CimMetricDefinition", foreign_keys=[metric_id])
    lifecycle_stage = relationship(
        "CimLifecycleStage", foreign_keys=[lifecycle_stage_id]
    )


# ---------------------------------------------------------------------------
# Rules / Evidence / Provenance / Extension
# ---------------------------------------------------------------------------


class CimValidationRule(CimGovernanceMixin, Base):
    __tablename__ = "cim_validation_rules"
    __table_args__ = (
        UniqueConstraint("name", name="uq_cim_validation_rules_name"),
        Index("ix_cim_validation_rules_target_registry", "target_registry"),
        Index("ix_cim_validation_rules_status", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    rule_type = Column(String(64), nullable=False)
    target_registry = Column(String(64), nullable=False)
    condition = Column(JSON, nullable=False, server_default="{}")
    severity = Column(String(32), nullable=False, server_default="error")


class CimEvidenceRequirement(CimGovernanceMixin, Base):
    __tablename__ = "cim_evidence_requirements"
    __table_args__ = (
        Index("ix_cim_evidence_requirements_standard_id", "standard_id"),
        Index("ix_cim_evidence_requirements_metric_id", "metric_id"),
        UniqueConstraint(
            "standard_id",
            "metric_id",
            "evidence_type",
            name="uq_cim_evidence_requirements_std_metric_type",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    standard_id = Column(
        Integer,
        ForeignKey(
            "cim_standards.id",
            name="fk_cim_evidence_requirements_standard_id_cim_standards",
        ),
        nullable=False,
    )
    metric_id = Column(
        Integer,
        ForeignKey(
            "cim_metric_definitions.id",
            name="fk_cim_evidence_requirements_metric_id_cim_metric_definitions",
        ),
        nullable=False,
    )
    evidence_type = Column(String(64), nullable=False)
    requirement_level = Column(
        String(64), nullable=False, server_default="recommended"
    )
    reporting_period = Column(String(64), nullable=True)
    aggregation_method = Column(String(64), nullable=True)
    boundary = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)

    standard = relationship("CimStandard", foreign_keys=[standard_id])
    metric = relationship("CimMetricDefinition", foreign_keys=[metric_id])


class CimProvenanceRecord(CimGovernanceMixin, Base):
    __tablename__ = "cim_provenance_records"
    __table_args__ = (
        Index("ix_cim_provenance_records_entity", "entity_type", "entity_id"),
        Index("ix_cim_provenance_records_activity", "activity"),
        Index("ix_cim_provenance_records_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(Integer, nullable=True)
    activity = Column(String(64), nullable=False)
    agent = Column(String(128), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    inputs = Column(JSON, nullable=True, server_default="{}")
    outputs = Column(JSON, nullable=True, server_default="{}")
    method = Column(String(128), nullable=True)
    prov_uri = Column(String(256), nullable=True)


class CimExtensionMetric(CimGovernanceMixin, Base):
    __tablename__ = "cim_extension_metrics"
    __table_args__ = (
        UniqueConstraint("metric_id", name="uq_cim_extension_metrics_metric_id"),
        Index("ix_cim_extension_metrics_status", "status"),
        Index("ix_cim_extension_metrics_review_status", "review_status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_id = Column(
        Integer,
        ForeignKey(
            "cim_metric_definitions.id",
            name="fk_cim_extension_metrics_metric_id_cim_metric_definitions",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    proposed_standard = Column(String(255), nullable=True)
    justification = Column(Text, nullable=True)
    proposed_by = Column(String(128), nullable=True)
    proposed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    metric = relationship("CimMetricDefinition", foreign_keys=[metric_id])


CIM_REGISTRY_MODELS = (
    CimQuantityKind,
    CimUnit,
    CimSource,
    CimLifecycleStage,
    CimAsset,
    CimStandard,
    CimStandardTerm,
    CimMetricDefinition,
    CimMetricMapping,
    CimMetricLifecycleLink,
    CimValidationRule,
    CimEvidenceRequirement,
    CimProvenanceRecord,
    CimExtensionMetric,
)

CIM_REGISTRY_TABLES = tuple(m.__tablename__ for m in CIM_REGISTRY_MODELS)

GOVERNANCE_COLUMNS = (
    "id",
    "status",
    "review_status",
    "confidence_score",
    "version",
    "created_at",
    "updated_at",
    "created_by",
    "notes",
)
