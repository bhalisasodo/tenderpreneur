from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.models import Organisation, SupplierProfile, utc_now
from app.core.security import AuthContext, get_current_auth, require_supplier
from app.domains.matching.service import match_suppliers_for_item
from app.schemas.suppliers import (
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
            active=True,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return SupplierProfileResponse.model_validate(profile)


@router.post("/profile", response_model=SupplierProfileResponse)
async def upsert_supplier_profile(
    payload: SupplierProfileCreate,
    auth: AuthContext = Depends(require_supplier),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SupplierProfile).where(SupplierProfile.organisation_id == auth.organisation_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        profile = SupplierProfile(
            organisation_id=auth.organisation_id,
            categories=payload.categories,
            service_regions=payload.service_regions,
            compliance_flags=payload.compliance_flags,
            preferred_contact_method=payload.preferred_contact_method,
            active=payload.active,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(profile)
    else:
        profile.categories = payload.categories
        profile.service_regions = payload.service_regions
        profile.compliance_flags = payload.compliance_flags
        profile.preferred_contact_method = payload.preferred_contact_method
        profile.active = payload.active
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
        .where(SupplierProfile.active.is_(True))
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


@router.get("/match", response_model=List[SupplierMatchResponse])
async def find_matched_suppliers(
    category: str = Query(...),
    region: str = Query(...),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
):
    return await match_suppliers_for_item(category=category, region=region, db=db)
