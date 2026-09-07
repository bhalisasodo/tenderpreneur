from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.models import Organisation, User
from app.core.security import AuthContext, create_access_token, get_current_auth
from app.core.rate_limit import rate_limit_auth
from app.schemas.auth import LoginRequest, OrganisationResponse, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit_auth)])
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(User)
        .options(selectinload(User.organisation))
        .where(User.email == request.email.lower().strip())
    )
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email address or credentials."},
        )

    org = user.organisation
    token = create_access_token(
        user_id=user.id,
        organisation_id=org.id,
        organisation_type=org.type,
        email=user.email,
        role=user.role,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        organisation=OrganisationResponse.model_validate(org),
    )


@router.get("/me", response_model=TokenResponse)
async def get_current_user_profile(
    auth: AuthContext = Depends(get_current_auth),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(User)
        .options(selectinload(User.organisation))
        .where(User.id == auth.user_id)
    )
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "Authenticated user profile not found."},
        )

    org = user.organisation
    token = create_access_token(
        user_id=user.id,
        organisation_id=org.id,
        organisation_type=org.type,
        email=user.email,
        role=user.role,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        organisation=OrganisationResponse.model_validate(org),
    )


@router.get("/demo-tenants", response_model=List[UserResponse])
async def list_demo_tenants(db: AsyncSession = Depends(get_db)):
    """Returns demo users with organisation info for rapid persona switching."""
    stmt = (
        select(User)
        .options(selectinload(User.organisation))
        .order_by(User.created_at.asc())
    )
    res = await db.execute(stmt)
    users = res.scalars().all()
    return [UserResponse.model_validate(u) for u in users]
