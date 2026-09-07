import random
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.models import (
    AuditEvent,
    BoQ,
    LineItem,
    Organisation,
    Quote,
    QuoteRequest,
    QuoteRequestSupplier,
    SupplierProfile,
    generate_uuid,
    utc_now,
)
from app.domains.audit.service import log_audit_event
from app.domains.matching.service import match_suppliers_for_item

# Sample supplier remarks and trade notes for realism
SUPPLIER_REMARKS = [
    "Stock available in warehouse. Delivery to site within standard turnaround.",
    "SABS / SANAS approved quality materials. Price includes offloading on site.",
    "Immediate dispatch upon order confirmation. 30-day quote validity.",
    "Direct mill / factory delivery. SCM compliant invoice and batch certificates provided.",
    "Bulk order pricing applied. Subject to standard site access terms.",
]


async def simulate_supplier_quotes_for_request(
    quote_request_id: str,
    db: AsyncSession,
    actor_user_id: Optional[str] = None,
) -> List[Quote]:
    """Simulates realistic supplier quote submissions for an active quote request."""
    stmt = (
        select(QuoteRequest)
        .options(
            selectinload(QuoteRequest.line_item).selectinload(LineItem.boq),
            selectinload(QuoteRequest.suppliers).selectinload(QuoteRequestSupplier.supplier_organisation),
            selectinload(QuoteRequest.quotes),
        )
        .where(QuoteRequest.id == quote_request_id)
    )
    res = await db.execute(stmt)
    qr = res.scalar_one_or_none()
    if not qr or qr.status != "open":
        return []

    line_item = qr.line_item
    boq = line_item.boq

    # Find supplier recipients
    suppliers_to_quote = []
    if qr.suppliers:
        for qrs in qr.suppliers:
            # Check if this supplier has already submitted
            has_submitted = any(q.supplier_organisation_id == qrs.supplier_organisation_id for q in qr.quotes)
            if not has_submitted:
                supp_name = qrs.supplier_organisation.trading_name or qrs.supplier_organisation.legal_name if qrs.supplier_organisation else "Supplier"
                suppliers_to_quote.append((qrs.supplier_organisation_id, supp_name, qrs))
    else:
        # Match suppliers dynamically if broadcast was not run yet
        matched = await match_suppliers_for_item(
            db=db,
            category=line_item.category,
            region=boq.region,
        )
        for supp in matched:
            has_submitted = any(q.supplier_organisation_id == supp.organisation_id for q in qr.quotes)
            if not has_submitted:
                # Create broadcast entry
                qrs = QuoteRequestSupplier(
                    id=generate_uuid(),
                    quote_request_id=qr.id,
                    supplier_organisation_id=supp.organisation_id,
                    delivered_at=utc_now(),
                    status="sent",
                )
                db.add(qrs)
                suppliers_to_quote.append((supp.organisation_id, supp.trading_name or supp.legal_name, qrs))

    if not suppliers_to_quote:
        return []

    # Calculate baseline unit price in cents
    min_b = line_item.benchmark_min_minor or 10000
    max_b = line_item.benchmark_max_minor or int(min_b * 1.5)
    base_center = (min_b + max_b) // 2

    created_quotes = []
    for idx, (supp_org_id, supp_name, qrs) in enumerate(suppliers_to_quote):
        # Introduce variation per supplier (-12% to +15%)
        variation_factor = 0.88 + (idx * 0.08) + random.uniform(-0.03, 0.03)
        unit_price = max(int(base_center * variation_factor), 100)
        total_price = int(unit_price * line_item.quantity)
        lead_time = random.choice([1, 2, 3, 5, 7])
        notes = random.choice(SUPPLIER_REMARKS)

        quote = Quote(
            id=generate_uuid(),
            quote_request_id=qr.id,
            supplier_organisation_id=supp_org_id,
            unit_price_minor=unit_price,
            total_price_minor=total_price,
            currency="ZAR",
            lead_time_days=lead_time,
            notes=f"{notes} ({supp_name})",
            is_selected=False,
            submitted_at=utc_now(),
        )
        db.add(quote)
        created_quotes.append(quote)

        # Update supplier request status
        qrs.status = "submitted"
        qrs.viewed_at = utc_now()

        # Audit log
        await log_audit_event(
            db=db,
            organisation_id=supp_org_id,
            actor_user_id=actor_user_id,
            entity_type="quote",
            entity_id=quote.id,
            action="quote.submitted.simulated",
            after_json={
                "quote_request_id": qr.id,
                "unit_price_minor": unit_price,
                "total_price_minor": total_price,
                "currency": "ZAR",
                "lead_time_days": lead_time,
            },
        )

    line_item.pricing_status = "quoted"
    line_item.updated_at = utc_now()

    await db.commit()
    return created_quotes


async def simulate_all_quotes_for_boq(
    boq_id: str,
    db: AsyncSession,
    actor_user_id: Optional[str] = None,
) -> int:
    """Finds all open quote requests on a BoQ and simulates quotes for them."""
    stmt = (
        select(QuoteRequest)
        .join(LineItem, QuoteRequest.line_item_id == LineItem.id)
        .where(LineItem.boq_id == boq_id, QuoteRequest.status == "open")
    )
    res = await db.execute(stmt)
    quote_requests = res.scalars().all()

    total_quotes = 0
    for qr in quote_requests:
        simulated = await simulate_supplier_quotes_for_request(qr.id, db, actor_user_id)
        total_quotes += len(simulated)

    return total_quotes
