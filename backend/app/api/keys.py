"""API key CRUD — create (return raw key once), list (prefix + last_used_at), deactivate. JWT only."""
import secrets
from datetime import datetime
from uuid import UUID

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_org_jwt_only
from app.models import ApiKey, Organization

router = APIRouter(prefix="/keys", tags=["keys"], dependencies=[Depends(get_current_org_jwt_only)])


class CreateKeyRequest(BaseModel):
    name: str = Field(default="API Key", max_length=255)


class CreateKeyResponse(BaseModel):
    id: UUID
    name: str
    prefix: str
    key: str = Field(description="Raw API key — shown only once; store securely.")
    warning: str = Field(default="This key will not be shown again. Store it securely.")


class KeyListItem(BaseModel):
    id: UUID
    name: str
    prefix: str
    last_used_at: datetime | None
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


@router.post("", response_model=CreateKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    body: CreateKeyRequest,
    org: Organization = Depends(get_current_org_jwt_only),
    db: AsyncSession = Depends(get_db),
) -> CreateKeyResponse:
    raw_key = "pqc_" + secrets.token_urlsafe(32)
    key_hash = bcrypt.hashpw(raw_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    prefix = raw_key[:8]

    api_key = ApiKey(
        org_id=org.id,
        name=body.name,
        key_hash=key_hash,
        prefix=prefix,
        is_active=True,
    )
    db.add(api_key)
    await db.flush()

    return CreateKeyResponse(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        key=raw_key,
        warning="This key will not be shown again. Store it securely.",
    )


@router.get("", response_model=list[KeyListItem])
async def list_keys(
    org: Organization = Depends(get_current_org_jwt_only),
    db: AsyncSession = Depends(get_db),
) -> list[KeyListItem]:
    result = await db.execute(
        select(ApiKey).where(ApiKey.org_id == org.id).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [KeyListItem.model_validate(k) for k in keys]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_key(
    key_id: UUID,
    org: Organization = Depends(get_current_org_jwt_only),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.org_id == org.id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    api_key.is_active = False
    await db.flush()
