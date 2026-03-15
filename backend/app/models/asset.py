"""Asset model — one cryptographic 'thing' (cert, API, code, DB, network)."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AssetType(str, enum.Enum):
    CERTIFICATE = "certificate"
    API_ENDPOINT = "api_endpoint"
    SOURCE_CODE = "source_code"
    DATABASE = "database"
    NETWORK_PROTOCOL = "network_protocol"


class Lifecycle(str, enum.Enum):
    ACTIVE = "active"
    STALE = "stale"
    REMOVED = "removed"


class MigrationPriority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scope_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("scopes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="asset_type_enum", create_constraint=True), nullable=False
    )
    source_identifier: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    lifecycle: Mapped[Lifecycle] = mapped_column(
        Enum(Lifecycle, name="lifecycle_enum", create_constraint=True), nullable=False, default=Lifecycle.ACTIVE
    )
    migration_priority: Mapped[MigrationPriority | None] = mapped_column(
        Enum(MigrationPriority, name="migration_priority_enum", create_constraint=True), nullable=True
    )
    priority_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority_rationale: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    findings: Mapped[list["CryptoFinding"]] = relationship("CryptoFinding", back_populates="asset", cascade="all, delete-orphan")
