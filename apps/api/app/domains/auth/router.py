from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.models import Organisation, SupplierProfile, User, utc_now
from app.core.security import (
    AuthContext,
    create_access_token,
    get_current_auth,
    hash_password,
    verify_password,
)
from app.core.rate_limit import rate_limit_auth
from app.domains.audit.service import log_audit_event
from app.schemas.auth import (
    LoginRequest,
    OrganisationResponse,
    SupplierRegisterRequest,
    SupplierRegisterResponse,
    TokenResponse,
    UserResponse,
)
from app.schemas.suppliers import SupplierProfileResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register-supplier", response_model=SupplierRegisterResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit_auth)])
async def register_supplier(
    request: SupplierRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Self-service onboarding endpoint for South African trade suppliers."""
    normalized_email = request.email.lower().strip()

    # Check for existing user or organisation by email
    stmt = select(User).where(User.email == normalized_email)
    existing_user_res = await db.execute(stmt)
    if existing_user_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMAIL_ALREADY_REGISTERED", "message": "An account with this email address already exists."},
        )

    stmt_org = select(Organisation).where(Organisation.email == normalized_email)
    existing_org_res = await db.execute(stmt_org)
    if existing_org_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "ORGANISATION_EXISTS", "message": "An organisation with this email address already exists."},
        )

    # 1. Create Supplier Organisation
    now = utc_now()
    org = Organisation(
        type="supplier",
        legal_name=request.legal_name.strip(),
        trading_name=request.trading_name.strip() if request.trading_name else request.legal_name.strip(),
        email=normalized_email,
        phone=request.phone.strip(),
        region=request.region.strip(),
        created_at=now,
        updated_at=now,
    )
    db.add(org)
    await db.flush()

    # 2. Create Primary Admin / Sales User
    hashed_pwd = hash_password(request.password)
    user = User(
        organisation_id=org.id,
        email=normalized_email,
        name=request.contact_name.strip(),
        role="admin",
        password_hash=hashed_pwd,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    await db.flush()

    # 3. Create Supplier Profile with trade categories and service provinces
    profile = SupplierProfile(
        organisation_id=org.id,
        categories=request.categories if request.categories else ["building-materials"],
        service_regions=request.service_regions if request.service_regions else [request.region.strip()],
        compliance_flags=request.compliance_flags or {},
        preferred_contact_method=request.preferred_contact_method or "whatsapp",
        status="pending",
        active=False,
        created_at=now,
        updated_at=now,
    )
    db.add(profile)
    await db.flush()

    # 4. Audit Log
    await log_audit_event(
        db=db,
        organisation_id=org.id,
        actor_user_id=user.id,
        entity_type="organisation",
        entity_id=org.id,
        action="organisation.registered",
        after_json={
            "legal_name": org.legal_name,
            "type": "supplier",
            "region": org.region,
            "categories": profile.categories,
            "service_regions": profile.service_regions,
        },
    )

    await db.commit()
    await db.refresh(org)
    await db.refresh(user)
    await db.refresh(profile)

    token = create_access_token(
        user_id=user.id,
        organisation_id=org.id,
        organisation_type=org.type,
        email=user.email,
        role=user.role,
    )

    return SupplierRegisterResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        organisation=OrganisationResponse.model_validate(org),
        profile=SupplierProfileResponse.model_validate(profile),
    )


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

    # If the user has a stored password hash, enforce strict password verification
    if user.password_hash:
        if not request.password or not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email address or password."},
            )

    org = user.organisation
    if org.type == "supplier" and (not org.supplier_profile or not org.supplier_profile.active):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "SUPPLIER_PENDING_APPROVAL", "message": "Supplier account is pending approval."},
        )
    role = "platform_operator" if user.email.lower() in settings.operator_emails else user.role
    token = create_access_token(
        user_id=user.id,
        organisation_id=org.id,
        organisation_type=org.type,
        email=user.email,
        role=role,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        organisation=OrganisationResponse.model_validate(org),
    )


@router.post("/supplier-registration", response_model=SupplierRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_supplier(
    request: SupplierRegistrationRequest,
    db: AsyncSession = Depends(get_db),
):
    email = str(request.email).lower().strip()
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_ALREADY_REGISTERED", "message": "An account with this email already exists."},
        )

    now = utc_now()
    organisation = Organisation(
        id=generate_uuid(),
        type="supplier",
        legal_name=request.legal_name.strip(),
        trading_name=request.trading_name.strip() if request.trading_name else None,
        email=email,
        phone=request.phone.strip(),
        region="Durban",
        created_at=now,
        updated_at=now,
    )
    user = User(
        id=generate_uuid(),
        organisation_id=organisation.id,
        email=email,
        name=request.contact_name.strip(),
        role="admin",
        password_hash=hash_password(request.password),
        created_at=now,
        updated_at=now,
    )
    profile = SupplierProfile(
        id=generate_uuid(),
        organisation_id=organisation.id,
        categories=[category.strip().lower() for category in request.categories],
        service_regions=[region.strip() for region in request.service_regions],
        compliance_flags={},
        preferred_contact_method=request.preferred_contact_method,
        approval_status="pending",
        active=False,
        created_at=now,
        updated_at=now,
    )
    db.add_all([organisation, user, profile])
    await db.commit()

    return SupplierRegistrationResponse(
        organisation_id=organisation.id,
        user_id=user.id,
        status="pending_approval",
        message="Registration received. BoQPro will review your supplier profile before activation.",
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
    role = "platform_operator" if user.email.lower() in settings.operator_emails else user.role
    token = create_access_token(
        user_id=user.id,
        organisation_id=org.id,
        organisation_type=org.type,
        email=user.email,
        role=role,
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
