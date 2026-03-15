"""CryptoFinding model — one algorithm/usage on one asset."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FindingUsage(str, enum.Enum):
    KEY_EXCHANGE = "key_exchange"
    SIGNING = "signing"
    ENCRYPTION = "encryption"
    HASHING = "hashing"
    UNKNOWN = "unknown"


class QuantumStatus(str, enum.Enum):
    VULNERABLE = "vulnerable"
    HYBRID = "hybrid"
    QUANTUM_SAFE = "quantum_safe"


class CryptoFinding(Base):
    __tablename__ = "crypto_findings"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    algorithm: Mapped[str] = mapped_column(String(128), nullable=False)
    usage: Mapped[FindingUsage] = mapped_column(
        Enum(FindingUsage, name="finding_usage_enum", create_constraint=True), nullable=False, default=FindingUsage.UNKNOWN
    )
    quantum_status: Mapped[QuantumStatus] = mapped_column(
        Enum(QuantumStatus, name="quantum_status_enum", create_constraint=True), nullable=False
    )
    key_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    key_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    asset: Mapped["Asset"] = relationship("Asset", back_populates="findings")
