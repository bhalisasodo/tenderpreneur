from typing import List, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.models import Organisation, SupplierProfile
from app.schemas.suppliers import SupplierMatchResponse


async def match_suppliers_for_item(
    category: str,
    region: str,
    db: AsyncSession,
) -> List[SupplierMatchResponse]:
    """
    Deterministic supplier matcher:
    Finds active supplier organisations where supplier category matches item category
    and supplier service regions include the tender region.
    """
    stmt = (
        select(SupplierProfile)
        .options(selectinload(SupplierProfile.organisation))
        .where(SupplierProfile.active.is_(True))
    )
    result = await db.execute(stmt)
    profiles = result.scalars().all()

    matched: List[SupplierMatchResponse] = []
    target_category = category.lower().strip()
    target_region = region.lower().strip()

    for p in profiles:
        org = p.organisation
        if not org or org.type != "supplier":
            continue

        sup_categories = [c.lower().strip() for c in (p.categories or [])]
        sup_regions = [r.lower().strip() for r in (p.service_regions or [])]

        reasons = []

        # Category match
        category_matched = (
            target_category in sup_categories
            or "all" in sup_categories
            or "general-building" in sup_categories
            or target_category == "general-building"
        )
        if category_matched:
            reasons.append(f"Category matched: '{category}'")

        # Region match
        region_matched = (
            target_region in sup_regions
            or "national" in sup_regions
            or "all" in sup_regions
            or not sup_regions
        )
        if region_matched:
            reasons.append(f"Region matched: '{region}'")

        if category_matched and region_matched:
            matched.append(
                SupplierMatchResponse(
                    organisation_id=org.id,
                    legal_name=org.legal_name,
                    trading_name=org.trading_name,
                    email=org.email,
                    phone=org.phone,
                    categories=p.categories or [],
                    service_regions=p.service_regions or [],
                    preferred_contact_method=p.preferred_contact_method or "whatsapp",
                    match_reasons=reasons,
                )
            )

    return matched
