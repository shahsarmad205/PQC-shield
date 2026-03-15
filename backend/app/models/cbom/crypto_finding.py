"""CryptoFinding — one algorithm (and usage) on one asset."""
import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FindingUsage(str, enum.Enum):
    key_exchange = "key_exchange"
    signing = "signing"
    encryption = "encryption"
    hashing = "hashing"
    unknown = "unknown"


class QuantumStatus(str, enum.Enum):
    vulnerable = "vulnerable"
    hybrid = "hybrid"
    quantum_safe = "quantum_safe"


class CryptoFinding(Base):
    __tablename__ = "crypto_findings"

    __table_args__ = (Index("ix_crypto_findings_asset_id", "asset_id"),)

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    asset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    algorithm: Mapped[str] = mapped_column(String(128), nullable=False)
    usage: Mapped[FindingUsage] = mapped_column(
        Enum(FindingUsage, name="finding_usage_enum", create_constraint=True),
        nullable=False,
    )
    quantum_status: Mapped[QuantumStatus] = mapped_column(
        Enum(QuantumStatus, name="quantum_status_enum", create_constraint=True),
        nullable=False,
    )
    key_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    key_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finding_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cve_refs: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()")
    )
