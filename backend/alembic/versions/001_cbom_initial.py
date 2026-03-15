"""cbom_initial

Revision ID: 001_cbom_initial
Revises:
Create Date: CBOM initial schema

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_cbom_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_enum_if_not_exists(conn, name: str, values: list[str]) -> None:
    """Create PostgreSQL enum type only if it does not exist (avoids clash with existing schema)."""
    # Use literal name (we control it); values are quoted for safety.
    values_sql = ", ".join(f"'{v}'" for v in values)
    conn.execute(sa.text(
        f"DO $$ BEGIN "
        f"IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{name}') THEN "
        f"  CREATE TYPE {name} AS ENUM ({values_sql}); "
        f"END IF; END $$"
    ))


def upgrade() -> None:
    conn = op.get_bind()
    _create_enum_if_not_exists(conn, "scope_type_enum", ["environment", "application", "region", "custom"])
    _create_enum_if_not_exists(conn, "discovery_run_status_enum", ["running", "completed", "failed", "partial"])
    _create_enum_if_not_exists(conn, "asset_type_enum", ["certificate", "api_endpoint", "source_code", "database", "network_protocol"])
    _create_enum_if_not_exists(conn, "lifecycle_enum", ["active", "stale", "removed"])
    _create_enum_if_not_exists(conn, "migration_priority_enum", ["critical", "high", "medium", "low", "none"])
    _create_enum_if_not_exists(conn, "finding_usage_enum", ["key_exchange", "signing", "encryption", "hashing", "unknown"])
    _create_enum_if_not_exists(conn, "quantum_status_enum", ["vulnerable", "hybrid", "quantum_safe"])
    _create_enum_if_not_exists(conn, "remediation_action_enum", ["cert_replaced", "tls_upgraded", "algorithm_rotated", "code_updated", "deferred", "false_positive"])
    _create_enum_if_not_exists(conn, "remediation_status_enum", ["planned", "in_progress", "completed", "deferred", "cancelled"])

    # Enum types for columns: create_type=False so we don't duplicate (we created above if needed)
    scope_type_enum = postgresql.ENUM(
        "environment", "application", "region", "custom",
        name="scope_type_enum",
        create_type=False,
    )
    discovery_run_status_enum = postgresql.ENUM(
        "running", "completed", "failed", "partial",
        name="discovery_run_status_enum",
        create_type=False,
    )
    asset_type_enum = postgresql.ENUM(
        "certificate", "api_endpoint", "source_code", "database", "network_protocol",
        name="asset_type_enum",
        create_type=False,
    )
    lifecycle_enum = postgresql.ENUM("active", "stale", "removed", name="lifecycle_enum", create_type=False)
    migration_priority_enum = postgresql.ENUM(
        "critical", "high", "medium", "low", "none",
        name="migration_priority_enum",
        create_type=False,
    )
    finding_usage_enum = postgresql.ENUM(
        "key_exchange", "signing", "encryption", "hashing", "unknown",
        name="finding_usage_enum",
        create_type=False,
    )
    quantum_status_enum = postgresql.ENUM(
        "vulnerable", "hybrid", "quantum_safe",
        name="quantum_status_enum",
        create_type=False,
    )
    remediation_action_enum = postgresql.ENUM(
        "cert_replaced", "tls_upgraded", "algorithm_rotated", "code_updated", "deferred", "false_positive",
        name="remediation_action_enum",
        create_type=False,
    )
    remediation_status_enum = postgresql.ENUM(
        "planned", "in_progress", "completed", "deferred", "cancelled",
        name="remediation_status_enum",
        create_type=False,
    )

    # Organizations
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Scopes
    op.create_table(
        "scopes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("scope_type", scope_type_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scopes_organization_id"), "scopes", ["organization_id"], unique=False)

    # Discovery runs
    op.create_table(
        "discovery_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", discovery_run_status_enum, nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scope_id"], ["scopes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_discovery_runs_organization_id"), "discovery_runs", ["organization_id"], unique=False)
    op.create_index(op.f("ix_discovery_runs_scope_id"), "discovery_runs", ["scope_id"], unique=False)

    # Assets
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("asset_type", asset_type_enum, nullable=False),
        sa.Column("source_identifier", sa.String(length=1024), nullable=False),
        sa.Column("display_name", sa.String(length=512), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("first_seen_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_seen_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lifecycle", lifecycle_enum, nullable=False),
        sa.Column("migration_priority", migration_priority_enum, nullable=True),
        sa.Column("priority_score", sa.Integer(), nullable=True),
        sa.Column("priority_rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["first_seen_run_id"], ["discovery_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["last_seen_run_id"], ["discovery_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scope_id"], ["scopes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "scope_id", "asset_type", "source_identifier",
            name="uq_asset_org_scope_type_source",
        ),
    )
    op.create_index(op.f("ix_assets_organization_id"), "assets", ["organization_id"], unique=False)
    op.create_index(op.f("ix_assets_scope_id"), "assets", ["scope_id"], unique=False)
    op.create_index("ix_assets_organization_id_lifecycle", "assets", ["organization_id", "lifecycle"], unique=False)
    op.create_index("ix_assets_organization_id_asset_type", "assets", ["organization_id", "asset_type"], unique=False)

    # Crypto findings
    op.create_table(
        "crypto_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("algorithm", sa.String(length=128), nullable=False),
        sa.Column("usage", finding_usage_enum, nullable=False),
        sa.Column("quantum_status", quantum_status_enum, nullable=False),
        sa.Column("key_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("key_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finding_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("risk_score", sa.Integer(), nullable=True),
        sa.Column("cve_refs", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crypto_findings_asset_id"), "crypto_findings", ["asset_id"], unique=False)

    # Remediation events
    op.create_table(
        "remediation_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", remediation_action_enum, nullable=False),
        sa.Column("status", remediation_status_enum, nullable=False),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("performed_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("before_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_remediation_events_asset_id_created_at",
        "remediation_events",
        ["asset_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_remediation_events_asset_id_created_at", table_name="remediation_events")
    op.drop_table("remediation_events")
    op.drop_index(op.f("ix_crypto_findings_asset_id"), table_name="crypto_findings")
    op.drop_table("crypto_findings")
    op.drop_index("ix_assets_organization_id_asset_type", table_name="assets")
    op.drop_index("ix_assets_organization_id_lifecycle", table_name="assets")
    op.drop_index(op.f("ix_assets_scope_id"), table_name="assets")
    op.drop_index(op.f("ix_assets_organization_id"), table_name="assets")
    op.drop_table("assets")
    op.drop_index(op.f("ix_discovery_runs_scope_id"), table_name="discovery_runs")
    op.drop_index(op.f("ix_discovery_runs_organization_id"), table_name="discovery_runs")
    op.drop_table("discovery_runs")
    op.drop_index(op.f("ix_scopes_organization_id"), table_name="scopes")
    op.drop_table("scopes")
    op.drop_table("organizations")

    postgresql.ENUM(name="remediation_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="remediation_action_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="quantum_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="finding_usage_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="migration_priority_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="lifecycle_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="asset_type_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="discovery_run_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="scope_type_enum").drop(op.get_bind(), checkfirst=True)
