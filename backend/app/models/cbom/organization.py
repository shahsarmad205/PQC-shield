"""Organization — tenant (enterprise or government org)."""
from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Plan(str, enum.Enum):
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# Default monthly op quotas per plan (used when Stripe not configured)
PLAN_QUOTAS: dict[Plan, int] = {
    Plan.STARTER: 10_000,
    Plan.PRO: 100_000,
    Plan.ENTERPRISE: 1_000_000,
}


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()")
    )
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Billing
    plan: Mapped[Plan] = mapped_column(
        Enum(Plan, native_enum=False, length=32, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=Plan.STARTER,
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    monthly_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=10_000)
    ops_used_this_month: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="organization",
        lazy="selectin",
    )
