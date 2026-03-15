"""API Keys: list, create (returns raw key once), deactivate."""
import hashlib
import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_org
from app.models.cbom import ApiKey, Organization

router = APIRouter()

PREFIX = "pqcs_"
KEY_BYTES = 32  # 64 hex chars


def _generate_key() -> tuple[str, str, str]:
    raw = secrets.token_hex(KEY_BYTES)
    full = PREFIX + raw
    prefix_display = full[:12] + "..."  # e.g. pqcs_3f7a1b2c...
    key_hash = hashlib.sha256(full.encode()).hexdigest()
    return full, prefix_display, key_hash


class CreateKeyBody(BaseModel):
    name: str


class KeyCreateResponse(BaseModel):
    id: UUID
    name: str
    key: str
    prefix: str
    created_at: datetime


class KeyListItem(BaseModel):
    id: UUID
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None
    is_active: bool


@router.get("", response_model=list[KeyListItem])
async def list_keys(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> list[KeyListItem]:
    """List API keys for the current organization."""
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.organization_id == org.id)
        .order_by(ApiKey.created_at.desc())
    )
    keys = list(result.scalars().all())
    return [
        KeyListItem(
            id=k.id,
            name=k.name,
            prefix=k.key_prefix,
            created_at=k.created_at,
            last_used_at=k.last_used_at,
            is_active=k.is_active,
        )
        for k in keys
    ]


@router.post("", response_model=KeyCreateResponse)
async def create_key(
    body: CreateKeyBody,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> KeyCreateResponse:
    """Create an API key. The raw key is returned only once."""
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, detail="name is required")
    full_key, prefix_display, key_hash = _generate_key()
    record = ApiKey(
        organization_id=org.id,
        name=name,
        key_prefix=prefix_display,
        key_hash=key_hash,
        is_active=True,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return KeyCreateResponse(
        id=record.id,
        name=record.name,
        key=full_key,
        prefix=prefix_display,
        created_at=record.created_at,
    )


@router.delete("/{key_id}", status_code=204)
async def deactivate_key(
    key_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> None:
    """Deactivate an API key (soft delete)."""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.organization_id == org.id,
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(404, detail="API key not found")
    key.is_active = False
    await db.flush()
    return None
