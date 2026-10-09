from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.models import Organisation, SupplierProfile, User
from app.core.rate_limit import rate_limit_auth
from app.core.security import (
    AuthContext,
    create_access_token,
    get_current_auth,
    hash_password,
    verify_password,
)
from app.domains.audit.service import log_audit_event
from app.schemas.auth import (
    LoginRequest,
    OrganisationResponse,
    RegistrationRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _create_token_response(
    user: User,
    organisation: Organisation,
    supplier_status: str | None = None,
) -> TokenResponse:
    token = create_access_token(
        user_id=user.id,
        organisation_id=organisation.id,
        organisation_type=organisation.type,
        email=user.email,
        role=user.role,
    )
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
        organisation=OrganisationResponse.model_validate(organisation),
        supplier_approval_status=supplier_status,
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

    if not user.is_active or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email address or password."},
        )

    org = user.organisation
    supplier_status = None
    if org.type == "supplier":
        profile_result = await db.execute(
            select(SupplierProfile.status).where(SupplierProfile.organisation_id == org.id)
        )
        supplier_status = profile_result.scalar_one_or_none()
    return _create_token_response(user, org, supplier_status)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_auth)],
)
async def register(request: RegistrationRequest, db: AsyncSession = Depends(get_db)):
    email = request.email
    existing_result = await db.execute(
        select(User.id)
        .where(func.lower(User.email) == email)
        .union(select(Organisation.id).where(func.lower(Organisation.email) == email))
    )
    if existing_result.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ACCOUNT_ALREADY_EXISTS", "message": "An account already uses this email address."},
        )

    if request.organisation_type == "supplier" and (
        not request.supplier_categories or not request.supplier_service_regions
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "SUPPLIER_PROFILE_REQUIRED",
                "message": "Select at least one supply category and service region.",
            },
        )

    organisation = Organisation(
        type=request.organisation_type,
        legal_name=request.legal_name,
        trading_name=request.trading_name or None,
        email=email,
        phone=request.phone or None,
        region=request.region,
    )
    user = User(
        organisation=organisation,
        email=email,
        name=request.name,
        role="admin",
        password_hash=hash_password(request.password),
        is_active=True,
    )
    db.add(organisation)
    db.add(user)

    supplier_status = None
    if request.organisation_type == "supplier":
        supplier_status = "pending"
        profile = SupplierProfile(
            organisation=organisation,
            categories=request.supplier_categories,
            service_regions=request.supplier_service_regions,
            preferred_contact_method=request.preferred_contact_method,
            compliance_flags={},
            status=supplier_status,
            active=False,
        )
        db.add(profile)

    try:
        await db.flush()
        if supplier_status:
            await log_audit_event(
                db=db,
                organisation_id=organisation.id,
                actor_user_id=user.id,
                entity_type="supplier_profile",
                entity_id=profile.id,
                action="supplier.registered",
                after_json={
                    "status": supplier_status,
                    "categories": request.supplier_categories,
                    "service_regions": request.supplier_service_regions,
                },
            )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ACCOUNT_ALREADY_EXISTS", "message": "An account already uses this email address."},
        ) from exc

    return _create_token_response(user, organisation, supplier_status)


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
    supplier_status = None
    if org.type == "supplier":
        profile_result = await db.execute(
            select(SupplierProfile.status).where(SupplierProfile.organisation_id == org.id)
        )
        supplier_status = profile_result.scalar_one_or_none()
    return _create_token_response(user, org, supplier_status)
