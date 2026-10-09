from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.models import SupplierProfile, utc_now
from app.core.security import AuthContext, get_current_auth, require_operator, require_platform_admin, require_supplier
from app.domains.audit.service import log_audit_event
from app.domains.matching.service import match_suppliers_for_item
from app.schemas.suppliers import (
    SupplierApprovalResponse,
    SupplierMatchResponse,
    SupplierProfileResponse,
    SupplierProfileUpdate,
    SupplierApprovalRequest,
    SupplierReviewResponse,
)

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@router.get("/profile", response_model=SupplierProfileResponse)
async def get_supplier_profile(
    auth: AuthContext = Depends(require_supplier),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SupplierProfile).where(SupplierProfile.organisation_id == auth.organisation_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if not profile:
        # Create default empty profile if none exists yet
        profile = SupplierProfile(
            organisation_id=auth.organisation_id,
            categories=[],
            service_regions=[],
            compliance_flags={},
            preferred_contact_method="email",
            status="pending",
            active=False,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return SupplierProfileResponse.model_validate(profile)


@router.post("/profile", response_model=SupplierProfileResponse)
async def upsert_supplier_profile(
    payload: SupplierProfileUpdate,
    auth: AuthContext = Depends(require_supplier),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SupplierProfile).where(SupplierProfile.organisation_id == auth.organisation_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        profile = SupplierProfile(
            organisation_id=auth.organisation_id,
            categories=payload.categories or [],
            service_regions=payload.service_regions or [],
            compliance_flags=payload.compliance_flags or {},
            preferred_contact_method=payload.preferred_contact_method or "email",
            status="pending",
            active=False,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(profile)
    else:
        if payload.categories is not None:
            profile.categories = payload.categories
        if payload.service_regions is not None:
            profile.service_regions = payload.service_regions
        if payload.compliance_flags is not None:
            profile.compliance_flags = payload.compliance_flags
        if payload.preferred_contact_method is not None:
            profile.preferred_contact_method = payload.preferred_contact_method
        profile.active = profile.status == "approved"
        profile.updated_at = utc_now()

    await db.commit()
    await db.refresh(profile)
    return SupplierProfileResponse.model_validate(profile)


@router.get("/review", response_model=List[SupplierReviewResponse])
async def list_supplier_review_queue(
    auth: AuthContext = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(SupplierProfile)
        .options(selectinload(SupplierProfile.organisation))
        .where(SupplierProfile.status.in_(["pending", "suspended", "rejected"]))
        .order_by(SupplierProfile.created_at.asc())
    )
    result = await db.execute(stmt)
    return [
        SupplierReviewResponse(
            id=profile.id,
            organisation_id=profile.organisation_id,
            legal_name=profile.organisation.legal_name,
            trading_name=profile.organisation.trading_name,
            email=profile.organisation.email,
            phone=profile.organisation.phone,
            region=profile.organisation.region,
            categories=profile.categories or [],
            service_regions=profile.service_regions or [],
            approval_status=profile.status,
            status=profile.status,
            active=profile.active,
        )
        for profile in result.scalars().all()
        if profile.organisation
    ]


@router.post("/{organisation_id}/approve", response_model=SupplierReviewResponse)
async def approve_supplier(
    organisation_id: str,
    payload: Optional[SupplierApprovalRequest] = None,
    auth: AuthContext = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    return await _set_supplier_approval(
        organisation_id=organisation_id,
        approval_status="approved",
        active=True,
        reason=payload.reason if payload else None,
        auth=auth,
        db=db,
    )


@router.post("/{organisation_id}/suspend", response_model=SupplierReviewResponse)
async def suspend_supplier(
    organisation_id: str,
    payload: Optional[SupplierApprovalRequest] = None,
    auth: AuthContext = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    return await _set_supplier_approval(
        organisation_id=organisation_id,
        approval_status="suspended",
        active=False,
        reason=payload.reason if payload else None,
        auth=auth,
        db=db,
    )


async def _set_supplier_approval(
    organisation_id: str,
    approval_status: str,
    active: bool,
    reason: Optional[str],
    auth: AuthContext,
    db: AsyncSession,
) -> SupplierReviewResponse:
    stmt = (
        select(SupplierProfile)
        .options(selectinload(SupplierProfile.organisation))
        .where(SupplierProfile.organisation_id == organisation_id)
    )
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    if not profile or not profile.organisation or profile.organisation.type != "supplier":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SUPPLIER_NOT_FOUND", "message": "Supplier organisation not found."},
        )

    before = {"approval_status": profile.status, "active": profile.active}
    profile.status = approval_status
    profile.active = active
    profile.updated_at = utc_now()
    await log_audit_event(
        db=db,
        organisation_id=organisation_id,
        actor_user_id=auth.user_id,
        entity_type="supplier_profile",
        entity_id=profile.id,
        action=f"supplier.{approval_status}",
        before_json=before,
        after_json={"approval_status": approval_status, "active": active},
        metadata_json={"reason": reason} if reason else None,
    )
    await db.commit()
    await db.refresh(profile)

    return SupplierReviewResponse(
        id=profile.id,
        organisation_id=profile.organisation_id,
        legal_name=profile.organisation.legal_name,
        trading_name=profile.organisation.trading_name,
        email=profile.organisation.email,
        phone=profile.organisation.phone,
        region=profile.organisation.region,
        categories=profile.categories or [],
        service_regions=profile.service_regions or [],
        approval_status=profile.status,
        status=profile.status,
        active=profile.active,
    )


@router.get("/all", response_model=List[SupplierMatchResponse])
async def list_all_suppliers(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
):
    stmt = (
        select(SupplierProfile)
        .options(selectinload(SupplierProfile.organisation))
        .where(
            SupplierProfile.status == "approved",
            SupplierProfile.active.is_(True),
        )
    )
    result = await db.execute(stmt)
    profiles = result.scalars().all()

    suppliers = []
    for p in profiles:
        org = p.organisation
        if org:
            suppliers.append(
                SupplierMatchResponse(
                    organisation_id=org.id,
                    legal_name=org.legal_name,
                    trading_name=org.trading_name,
                    email=org.email,
                    phone=org.phone,
                    categories=p.categories or [],
                    service_regions=p.service_regions or [],
                    preferred_contact_method=p.preferred_contact_method or "whatsapp",
                    match_reasons=[],
                )
            )
    return suppliers


@router.post("/{supplier_org_id}/reject", response_model=SupplierApprovalResponse)
async def reject_supplier(
    supplier_org_id: str,
    auth: AuthContext = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SupplierProfile).where(SupplierProfile.organisation_id == supplier_org_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SUPPLIER_NOT_FOUND", "message": "Supplier profile not found."},
        )

    previous_status = profile.status
    previous_active = profile.active
    profile.status = "rejected"
    profile.active = False
    profile.updated_at = utc_now()

    await log_audit_event(
        db=db,
        organisation_id=supplier_org_id,
        actor_user_id=auth.user_id,
        entity_type="supplier_profile",
        entity_id=profile.id,
        action="supplier.rejected",
        before_json={"status": previous_status, "active": previous_active},
        after_json={"status": "rejected", "active": False},
    )
    await db.commit()
    await db.refresh(profile)
    return SupplierApprovalResponse.model_validate(profile)


@router.get("/match", response_model=List[SupplierMatchResponse])
async def find_matched_suppliers(
    category: str = Query(...),
    region: str = Query(...),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
):
    return await match_suppliers_for_item(category=category, region=region, db=db)
