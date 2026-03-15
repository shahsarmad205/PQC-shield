"""RemediationEvent — history of what was done (or planned) to fix an asset."""
import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RemediationAction(str, enum.Enum):
    cert_replaced = "cert_replaced"
    tls_upgraded = "tls_upgraded"
    algorithm_rotated = "algorithm_rotated"
    code_updated = "code_updated"
    deferred = "deferred"
    false_positive = "false_positive"


class RemediationStatus(str, enum.Enum):
    planned = "planned"
    in_progress = "in_progress"
    completed = "completed"
    deferred = "deferred"
    cancelled = "cancelled"


class RemediationEvent(Base):
    __tablename__ = "remediation_events"

    __table_args__ = (Index("ix_remediation_events_asset_id_created_at", "asset_id", "created_at"),)

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
    action: Mapped[RemediationAction] = mapped_column(
        Enum(RemediationAction, name="remediation_action_enum", create_constraint=True),
        nullable=False,
    )
    status: Mapped[RemediationStatus] = mapped_column(
        Enum(RemediationStatus, name="remediation_status_enum", create_constraint=True),
        nullable=False,
    )
    performed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    performed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
