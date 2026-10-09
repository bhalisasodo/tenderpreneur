from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.models import Organisation, SupplierProfile, utc_now
from app.core.security import AuthContext, get_current_auth, require_platform_admin, require_supplier
from app.domains.audit.service import log_audit_event
from app.domains.matching.service import match_suppliers_for_item
from app.schemas.suppliers import (
    SupplierApprovalResponse,
    SupplierMatchResponse,
    SupplierProfileCreate,
    SupplierProfileResponse,
    SupplierProfileUpdate,
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
            categories=["building-materials"],
            service_regions=["KwaZulu-Natal", "Gauteng"],
            compliance_flags={"csd_registered": True, "bbee_level": "1"},
            preferred_contact_method="whatsapp",
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
            categories=payload.categories or ["building-materials"],
            service_regions=payload.service_regions or ["KwaZulu-Natal"],
            compliance_flags=payload.compliance_flags or {},
            preferred_contact_method=payload.preferred_contact_method or "whatsapp",
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


@router.post("/{supplier_org_id}/approve", response_model=SupplierApprovalResponse)
async def approve_supplier(
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
    profile.status = "approved"
    profile.active = True
    profile.updated_at = utc_now()

    before_active = profile.active
    await log_audit_event(
        db=db,
        organisation_id=supplier_org_id,
        actor_user_id=auth.user_id,
        entity_type="supplier_profile",
        entity_id=profile.id,
        action="supplier.approved",
        before_json={"status": previous_status, "active": before_active},
        after_json={"status": "approved", "active": True},
    )
    await db.commit()
    await db.refresh(profile)
    return SupplierApprovalResponse.model_validate(profile)


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
