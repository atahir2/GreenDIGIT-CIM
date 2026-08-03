"""add_cim_registry_tables

Revision ID: c2f8a1b9e047
Revises: a7708d6bee50
Create Date: 2026-08-03 18:30:00.000000

Milestone 2: additive registry-driven CIM schema (``cim_*`` tables).

Does not alter or drop legacy / Antigravity tables. Does not migrate mapping
data or wire ingestion. Fully reversible via downgrade().
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2f8a1b9e047"
down_revision: Union[str, Sequence[str], None] = "a7708d6bee50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _governance_columns():
    """Shared governance fields for registry tables."""
    return [
        sa.Column("status", sa.String(length=64), server_default="draft", nullable=False),
        sa.Column(
            "review_status",
            sa.String(length=64),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    ]


def upgrade() -> None:
    # --- quantity kinds ---
    op.create_table(
        "cim_quantity_kinds",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("qudt_uri", sa.String(length=256), nullable=True),
        *_governance_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_cim_quantity_kinds_name"),
    )
    op.create_index(
        "ix_cim_quantity_kinds_status", "cim_quantity_kinds", ["status"], unique=False
    )

    # --- units ---
    op.create_table(
        "cim_units",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("quantity_kind_id", sa.Integer(), nullable=False),
        sa.Column("si_base", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("canonical_unit_id", sa.Integer(), nullable=True),
        sa.Column(
            "conversion_factor", sa.Float(), server_default="1.0", nullable=False
        ),
        sa.Column(
            "conversion_offset", sa.Float(), server_default="0.0", nullable=False
        ),
        sa.Column("qudt_uri", sa.String(length=256), nullable=True),
        sa.Column("saref_uri", sa.String(length=256), nullable=True),
        *_governance_columns(),
        sa.ForeignKeyConstraint(
            ["quantity_kind_id"],
            ["cim_quantity_kinds.id"],
            name="fk_cim_units_quantity_kind_id_cim_quantity_kinds",
        ),
        sa.ForeignKeyConstraint(
            ["canonical_unit_id"],
            ["cim_units.id"],
            name="fk_cim_units_canonical_unit_id_cim_units",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", name="uq_cim_units_symbol"),
    )
    op.create_index(
        "ix_cim_units_quantity_kind_id", "cim_units", ["quantity_kind_id"], unique=False
    )
    op.create_index("ix_cim_units_status", "cim_units", ["status"], unique=False)

    # --- sources ---
    op.create_table(
        "cim_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("protocol", sa.String(length=64), nullable=True),
        sa.Column("format", sa.String(length=64), nullable=True),
        sa.Column("schema_version", sa.String(length=64), nullable=True),
        sa.Column("capabilities", sa.JSON(), server_default="{}", nullable=True),
        sa.Column(
            "auth_method", sa.String(length=64), server_default="none", nullable=False
        ),
        sa.Column("metadata_info", sa.JSON(), server_default="{}", nullable=True),
        *_governance_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "type", name="uq_cim_sources_name_type"),
    )
    op.create_index("ix_cim_sources_type", "cim_sources", ["type"], unique=False)
    op.create_index("ix_cim_sources_status", "cim_sources", ["status"], unique=False)

    # --- lifecycle stages (before assets) ---
    op.create_table(
        "cim_lifecycle_stages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("stage_key", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=True),
        *_governance_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_cim_lifecycle_stages_name"),
        sa.UniqueConstraint("stage_key", name="uq_cim_lifecycle_stages_stage_key"),
    )
    op.create_index(
        "ix_cim_lifecycle_stages_sequence",
        "cim_lifecycle_stages",
        ["sequence"],
        unique=False,
    )

    # --- assets ---
    op.create_table(
        "cim_assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("identifier", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("location", sa.String(length=256), nullable=True),
        sa.Column("provider", sa.String(length=128), nullable=True),
        sa.Column("specifications", sa.JSON(), server_default="{}", nullable=True),
        sa.Column("lifecycle_stage_id", sa.Integer(), nullable=True),
        *_governance_columns(),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["cim_assets.id"],
            name="fk_cim_assets_parent_id_cim_assets",
        ),
        sa.ForeignKeyConstraint(
            ["lifecycle_stage_id"],
            ["cim_lifecycle_stages.id"],
            name="fk_cim_assets_lifecycle_stage_id_cim_lifecycle_stages",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "identifier", "type", name="uq_cim_assets_identifier_type"
        ),
    )
    op.create_index("ix_cim_assets_name", "cim_assets", ["name"], unique=False)
    op.create_index("ix_cim_assets_type", "cim_assets", ["type"], unique=False)
    op.create_index("ix_cim_assets_parent_id", "cim_assets", ["parent_id"], unique=False)
    op.create_index("ix_cim_assets_status", "cim_assets", ["status"], unique=False)

    # --- standards ---
    op.create_table(
        "cim_standards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("standard_version", sa.String(length=64), nullable=True),
        sa.Column("url", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("vocabulary_type", sa.String(length=64), nullable=True),
        sa.Column("namespace_prefix", sa.String(length=64), nullable=True),
        sa.Column("namespace_uri", sa.String(length=512), nullable=True),
        sa.Column("domain", sa.String(length=64), nullable=True),
        *_governance_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "code",
            "standard_version",
            name="uq_cim_standards_code_standard_version",
        ),
        sa.UniqueConstraint(
            "name",
            "standard_version",
            name="uq_cim_standards_name_standard_version",
        ),
    )
    op.create_index("ix_cim_standards_status", "cim_standards", ["status"], unique=False)

    # --- standard terms ---
    op.create_table(
        "cim_standard_terms",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("standard_id", sa.Integer(), nullable=False),
        sa.Column("term_code", sa.String(length=128), nullable=False),
        sa.Column("term_label", sa.String(length=255), nullable=True),
        sa.Column("term_uri", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        *_governance_columns(),
        sa.ForeignKeyConstraint(
            ["standard_id"],
            ["cim_standards.id"],
            name="fk_cim_standard_terms_standard_id_cim_standards",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "standard_id",
            "term_code",
            name="uq_cim_standard_terms_standard_term",
        ),
    )
    op.create_index(
        "ix_cim_standard_terms_standard_id",
        "cim_standard_terms",
        ["standard_id"],
        unique=False,
    )

    # --- metric definitions ---
    op.create_table(
        "cim_metric_definitions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("namespace", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("domain", sa.String(length=64), nullable=True),
        sa.Column("category", sa.String(length=128), nullable=True),
        sa.Column("subcategory", sa.String(length=128), nullable=True),
        sa.Column("quantity_kind_id", sa.Integer(), nullable=True),
        sa.Column("canonical_unit_id", sa.Integer(), nullable=True),
        sa.Column("metric_type", sa.String(length=64), nullable=True),
        sa.Column("tags", sa.JSON(), server_default="[]", nullable=True),
        sa.Column("sources", sa.JSON(), server_default="[]", nullable=True),
        *_governance_columns(),
        sa.ForeignKeyConstraint(
            ["quantity_kind_id"],
            ["cim_quantity_kinds.id"],
            name="fk_cim_metric_definitions_quantity_kind_id_cim_quantity_kinds",
        ),
        sa.ForeignKeyConstraint(
            ["canonical_unit_id"],
            ["cim_units.id"],
            name="fk_cim_metric_definitions_canonical_unit_id_cim_units",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "namespace", name="uq_cim_metric_definitions_namespace"
        ),
    )
    op.create_index(
        "ix_cim_metric_definitions_domain",
        "cim_metric_definitions",
        ["domain"],
        unique=False,
    )
    op.create_index(
        "ix_cim_metric_definitions_status",
        "cim_metric_definitions",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_cim_metric_definitions_review_status",
        "cim_metric_definitions",
        ["review_status"],
        unique=False,
    )

    # --- metric mappings ---
    op.create_table(
        "cim_metric_mappings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_key", sa.String(length=255), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("metric_id", sa.Integer(), nullable=False),
        sa.Column("standard_id", sa.Integer(), nullable=True),
        sa.Column("standard_term_id", sa.Integer(), nullable=True),
        sa.Column(
            "relation_type",
            sa.String(length=64),
            server_default="underReview",
            nullable=False,
        ),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column(
            "origin", sa.String(length=64), server_default="manual", nullable=False
        ),
        sa.Column("approved_by", sa.String(length=128), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        *_governance_columns(),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["cim_sources.id"],
            name="fk_cim_metric_mappings_source_id_cim_sources",
        ),
        sa.ForeignKeyConstraint(
            ["metric_id"],
            ["cim_metric_definitions.id"],
            name="fk_cim_metric_mappings_metric_id_cim_metric_definitions",
        ),
        sa.ForeignKeyConstraint(
            ["standard_id"],
            ["cim_standards.id"],
            name="fk_cim_metric_mappings_standard_id_cim_standards",
        ),
        sa.ForeignKeyConstraint(
            ["standard_term_id"],
            ["cim_standard_terms.id"],
            name="fk_cim_metric_mappings_standard_term_id_cim_standard_terms",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_key",
            "source_id",
            name="uq_cim_metric_mappings_source_key_source_id",
        ),
    )
    op.create_index(
        "ix_cim_metric_mappings_source_key",
        "cim_metric_mappings",
        ["source_key"],
        unique=False,
    )
    op.create_index(
        "ix_cim_metric_mappings_metric_id",
        "cim_metric_mappings",
        ["metric_id"],
        unique=False,
    )
    op.create_index(
        "ix_cim_metric_mappings_standard_id",
        "cim_metric_mappings",
        ["standard_id"],
        unique=False,
    )
    op.create_index(
        "ix_cim_metric_mappings_status",
        "cim_metric_mappings",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_cim_metric_mappings_review_status",
        "cim_metric_mappings",
        ["review_status"],
        unique=False,
    )

    # --- metric lifecycle links ---
    op.create_table(
        "cim_metric_lifecycle_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("metric_id", sa.Integer(), nullable=False),
        sa.Column("lifecycle_stage_id", sa.Integer(), nullable=False),
        sa.Column(
            "relevance",
            sa.String(length=64),
            server_default="primary",
            nullable=False,
        ),
        *_governance_columns(),
        sa.ForeignKeyConstraint(
            ["metric_id"],
            ["cim_metric_definitions.id"],
            name="fk_cim_metric_lifecycle_links_metric_id_cim_metric_definitions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lifecycle_stage_id"],
            ["cim_lifecycle_stages.id"],
            name="fk_cim_metric_lifecycle_links_lifecycle_stage_id_cim_lifecycle_stages",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "metric_id",
            "lifecycle_stage_id",
            name="uq_cim_metric_lifecycle_links_metric_stage",
        ),
    )
    op.create_index(
        "ix_cim_metric_lifecycle_links_metric_id",
        "cim_metric_lifecycle_links",
        ["metric_id"],
        unique=False,
    )
    op.create_index(
        "ix_cim_metric_lifecycle_links_lifecycle_stage_id",
        "cim_metric_lifecycle_links",
        ["lifecycle_stage_id"],
        unique=False,
    )

    # --- validation rules ---
    op.create_table(
        "cim_validation_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rule_type", sa.String(length=64), nullable=False),
        sa.Column("target_registry", sa.String(length=64), nullable=False),
        sa.Column("condition", sa.JSON(), server_default="{}", nullable=False),
        sa.Column(
            "severity", sa.String(length=32), server_default="error", nullable=False
        ),
        *_governance_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_cim_validation_rules_name"),
    )
    op.create_index(
        "ix_cim_validation_rules_target_registry",
        "cim_validation_rules",
        ["target_registry"],
        unique=False,
    )
    op.create_index(
        "ix_cim_validation_rules_status",
        "cim_validation_rules",
        ["status"],
        unique=False,
    )

    # --- evidence requirements ---
    op.create_table(
        "cim_evidence_requirements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("standard_id", sa.Integer(), nullable=False),
        sa.Column("metric_id", sa.Integer(), nullable=False),
        sa.Column("evidence_type", sa.String(length=64), nullable=False),
        sa.Column(
            "requirement_level",
            sa.String(length=64),
            server_default="recommended",
            nullable=False,
        ),
        sa.Column("reporting_period", sa.String(length=64), nullable=True),
        sa.Column("aggregation_method", sa.String(length=64), nullable=True),
        sa.Column("boundary", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        *_governance_columns(),
        sa.ForeignKeyConstraint(
            ["standard_id"],
            ["cim_standards.id"],
            name="fk_cim_evidence_requirements_standard_id_cim_standards",
        ),
        sa.ForeignKeyConstraint(
            ["metric_id"],
            ["cim_metric_definitions.id"],
            name="fk_cim_evidence_requirements_metric_id_cim_metric_definitions",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "standard_id",
            "metric_id",
            "evidence_type",
            name="uq_cim_evidence_requirements_std_metric_type",
        ),
    )
    op.create_index(
        "ix_cim_evidence_requirements_standard_id",
        "cim_evidence_requirements",
        ["standard_id"],
        unique=False,
    )
    op.create_index(
        "ix_cim_evidence_requirements_metric_id",
        "cim_evidence_requirements",
        ["metric_id"],
        unique=False,
    )

    # --- provenance ---
    op.create_table(
        "cim_provenance_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("activity", sa.String(length=64), nullable=False),
        sa.Column("agent", sa.String(length=128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inputs", sa.JSON(), server_default="{}", nullable=True),
        sa.Column("outputs", sa.JSON(), server_default="{}", nullable=True),
        sa.Column("method", sa.String(length=128), nullable=True),
        sa.Column("prov_uri", sa.String(length=256), nullable=True),
        *_governance_columns(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cim_provenance_records_entity",
        "cim_provenance_records",
        ["entity_type", "entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_cim_provenance_records_activity",
        "cim_provenance_records",
        ["activity"],
        unique=False,
    )
    op.create_index(
        "ix_cim_provenance_records_created_at",
        "cim_provenance_records",
        ["created_at"],
        unique=False,
    )

    # --- extension metrics ---
    op.create_table(
        "cim_extension_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("metric_id", sa.Integer(), nullable=False),
        sa.Column("proposed_standard", sa.String(length=255), nullable=True),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("proposed_by", sa.String(length=128), nullable=True),
        sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        *_governance_columns(),
        sa.ForeignKeyConstraint(
            ["metric_id"],
            ["cim_metric_definitions.id"],
            name="fk_cim_extension_metrics_metric_id_cim_metric_definitions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "metric_id", name="uq_cim_extension_metrics_metric_id"
        ),
    )
    op.create_index(
        "ix_cim_extension_metrics_status",
        "cim_extension_metrics",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_cim_extension_metrics_review_status",
        "cim_extension_metrics",
        ["review_status"],
        unique=False,
    )


def downgrade() -> None:
    """Drop all Milestone 2 ``cim_*`` tables in reverse dependency order."""
    op.drop_index(
        "ix_cim_extension_metrics_review_status", table_name="cim_extension_metrics"
    )
    op.drop_index("ix_cim_extension_metrics_status", table_name="cim_extension_metrics")
    op.drop_table("cim_extension_metrics")

    op.drop_index(
        "ix_cim_provenance_records_created_at", table_name="cim_provenance_records"
    )
    op.drop_index(
        "ix_cim_provenance_records_activity", table_name="cim_provenance_records"
    )
    op.drop_index(
        "ix_cim_provenance_records_entity", table_name="cim_provenance_records"
    )
    op.drop_table("cim_provenance_records")

    op.drop_index(
        "ix_cim_evidence_requirements_metric_id",
        table_name="cim_evidence_requirements",
    )
    op.drop_index(
        "ix_cim_evidence_requirements_standard_id",
        table_name="cim_evidence_requirements",
    )
    op.drop_table("cim_evidence_requirements")

    op.drop_index(
        "ix_cim_validation_rules_status", table_name="cim_validation_rules"
    )
    op.drop_index(
        "ix_cim_validation_rules_target_registry",
        table_name="cim_validation_rules",
    )
    op.drop_table("cim_validation_rules")

    op.drop_index(
        "ix_cim_metric_lifecycle_links_lifecycle_stage_id",
        table_name="cim_metric_lifecycle_links",
    )
    op.drop_index(
        "ix_cim_metric_lifecycle_links_metric_id",
        table_name="cim_metric_lifecycle_links",
    )
    op.drop_table("cim_metric_lifecycle_links")

    op.drop_index(
        "ix_cim_metric_mappings_review_status", table_name="cim_metric_mappings"
    )
    op.drop_index("ix_cim_metric_mappings_status", table_name="cim_metric_mappings")
    op.drop_index(
        "ix_cim_metric_mappings_standard_id", table_name="cim_metric_mappings"
    )
    op.drop_index("ix_cim_metric_mappings_metric_id", table_name="cim_metric_mappings")
    op.drop_index(
        "ix_cim_metric_mappings_source_key", table_name="cim_metric_mappings"
    )
    op.drop_table("cim_metric_mappings")

    op.drop_index(
        "ix_cim_metric_definitions_review_status",
        table_name="cim_metric_definitions",
    )
    op.drop_index(
        "ix_cim_metric_definitions_status", table_name="cim_metric_definitions"
    )
    op.drop_index(
        "ix_cim_metric_definitions_domain", table_name="cim_metric_definitions"
    )
    op.drop_table("cim_metric_definitions")

    op.drop_index(
        "ix_cim_standard_terms_standard_id", table_name="cim_standard_terms"
    )
    op.drop_table("cim_standard_terms")

    op.drop_index("ix_cim_standards_status", table_name="cim_standards")
    op.drop_table("cim_standards")

    op.drop_index("ix_cim_assets_status", table_name="cim_assets")
    op.drop_index("ix_cim_assets_parent_id", table_name="cim_assets")
    op.drop_index("ix_cim_assets_type", table_name="cim_assets")
    op.drop_index("ix_cim_assets_name", table_name="cim_assets")
    op.drop_table("cim_assets")

    op.drop_index(
        "ix_cim_lifecycle_stages_sequence", table_name="cim_lifecycle_stages"
    )
    op.drop_table("cim_lifecycle_stages")

    op.drop_index("ix_cim_sources_status", table_name="cim_sources")
    op.drop_index("ix_cim_sources_type", table_name="cim_sources")
    op.drop_table("cim_sources")

    op.drop_index("ix_cim_units_status", table_name="cim_units")
    op.drop_index("ix_cim_units_quantity_kind_id", table_name="cim_units")
    op.drop_table("cim_units")

    op.drop_index("ix_cim_quantity_kinds_status", table_name="cim_quantity_kinds")
    op.drop_table("cim_quantity_kinds")
