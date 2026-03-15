"""Asset — one logical cryptographic thing (certificate, API, code location, DB, network)."""
import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AssetType(str, enum.Enum):
    certificate = "certificate"
    api_endpoint = "api_endpoint"
    source_code = "source_code"
    database = "database"
    network_protocol = "network_protocol"


class Lifecycle(str, enum.Enum):
    active = "active"
    stale = "stale"
    removed = "removed"


class MigrationPriority(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    none = "none"


class Asset(Base):
    __tablename__ = "assets"

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "scope_id",
            "asset_type",
            "source_identifier",
            name="uq_asset_org_scope_type_source",
        ),
        Index("ix_assets_organization_id_lifecycle", "organization_id", "lifecycle"),
        Index("ix_assets_organization_id_asset_type", "organization_id", "asset_type"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("scopes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="asset_type_enum", create_constraint=True),
        nullable=False,
    )
    source_identifier: Mapped[str] = mapped_column(String(1024), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    first_seen_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("discovery_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_seen_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("discovery_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lifecycle: Mapped[Lifecycle] = mapped_column(
        Enum(Lifecycle, name="lifecycle_enum", create_constraint=True),
        nullable=False,
    )
    migration_priority: Mapped[MigrationPriority | None] = mapped_column(
        Enum(MigrationPriority, name="migration_priority_enum", create_constraint=True),
        nullable=True,
    )
    priority_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()")
    )
