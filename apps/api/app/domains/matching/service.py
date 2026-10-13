from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.models import SupplierProfile
from app.schemas.suppliers import SupplierMatchResponse

PILOT_ACTIVE_CATEGORIES = frozenset(
    {"building-materials", "concrete", "earthworks"}
)
PILOT_REGION_NAMES = frozenset({"ethekwini", "durban"})
PILOT_SERVICE_REGION_NAMES = PILOT_REGION_NAMES | frozenset(
    {"kwazulu-natal", "national", "all"}
)


def is_pilot_region(region: str) -> bool:
    return region.strip().lower() in PILOT_REGION_NAMES


def profile_has_pilot_scope(categories: list[str], service_regions: list[str]) -> bool:
    normalized_categories = {category.strip().lower() for category in categories}
    normalized_regions = {region.strip().lower() for region in service_regions}
    return bool(
        normalized_categories.intersection(PILOT_ACTIVE_CATEGORIES)
        and normalized_regions.intersection(PILOT_SERVICE_REGION_NAMES)
    )


async def match_suppliers_for_item(
    category: str,
    region: str,
    db: AsyncSession,
) -> list[SupplierMatchResponse]:
    """
    Match only the active eThekwini supplier-pilot categories and region.
    """
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

    matched: list[SupplierMatchResponse] = []
    target_category = category.lower().strip()
    target_region = region.lower().strip()
    if target_category not in PILOT_ACTIVE_CATEGORIES or not is_pilot_region(target_region):
        return matched

    for p in profiles:
        org = p.organisation
        if not org or org.type != "supplier":
            continue

        sup_categories = [c.lower().strip() for c in (p.categories or [])]
        sup_regions = [r.lower().strip() for r in (p.service_regions or [])]

        reasons = []

        # Category match
        category_matched = target_category in sup_categories
        if category_matched:
            reasons.append(f"Category matched: '{category}'")

        # Region match
        region_matched = (
            target_region in sup_regions
            or "durban" in sup_regions
            or "kwazulu-natal" in sup_regions
            or "national" in sup_regions
            or "all" in sup_regions
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
