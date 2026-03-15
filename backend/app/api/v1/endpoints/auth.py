"""Auth endpoints: register (org + user), login, me."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.cbom import Organization, User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


# --- Schemas ---

class RegisterBody(BaseModel):
    email: str
    password: str
    full_name: str
    organization_name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class OrgRead(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class UserMeRead(BaseModel):
    id: UUID
    email: str
    full_name: str
    is_active: bool
    is_admin: bool
    organization_id: UUID
    organization: OrgRead | None = None

    class Config:
        from_attributes = True


# --- Endpoints ---

@router.post("/register", response_model=TokenResponse)
async def register(
    body: RegisterBody,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Create Organization + User in one transaction; return JWT (24h expiry)."""
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    org = Organization(name=body.organization_name)
    db.add(org)
    await db.flush()
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        organization_id=org.id,
        is_active=True,
        is_admin=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(org)
    await db.refresh(user)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=None,  # uses default 24h
    )
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Verify email/password (form), return JWT."""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")
    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserMeRead)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserMeRead:
    """Return current user + organization (requires Bearer token)."""
    if current_user.organization is None:
        await db.refresh(current_user, ["organization"])
    org_read = OrgRead.model_validate(current_user.organization) if current_user.organization else None
    return UserMeRead(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        organization_id=current_user.organization_id,
        organization=org_read,
    )
