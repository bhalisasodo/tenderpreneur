from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.models import (
    AuditEvent,
    BoQ,
    LineItem,
    Organisation,
    Quote,
    QuoteRequest,
    QuoteRequestSupplier,
    SupplierProfile,
    utc_now,
)
from app.core.security import AuthContext, get_current_auth, require_contractor, require_supplier
from app.domains.audit.service import log_audit_event
from app.domains.matching.service import match_suppliers_for_item
from app.domains.quotes.simulator import simulate_all_quotes_for_boq, simulate_supplier_quotes_for_request
from app.integrations.notifications import get_notification_provider
from pydantic import BaseModel

from app.domains.parsing.segmentation import is_text_corrupted
from app.schemas.quotes import (
    BoQQuoteComparisonResponse,
    LineItemComparisonResponse,
    PriceOverrideRequest,
    QuoteRequestBroadcastRequest,
    QuoteRequestCreate,
    QuoteRequestResponse,
    QuoteResponse,
    QuoteSelectRequest,
    QuoteSubmitRequest,
)

router = APIRouter(tags=["Quotes"])


class ValidateBroadcastRequest(BaseModel):
    line_item_ids: List[str]


class CorruptedItemReport(BaseModel):
    id: str
    line_item_id: Optional[str] = None
    description: str
    reason: str
    corruption_ratio: float


class ValidateBroadcastResponse(BaseModel):
    is_safe: bool
    safe: Optional[bool] = None
    total_items: int
    valid_items_count: int
    corrupted_items_count: int
    corrupted_items: List[CorruptedItemReport] = []
    message: str


def check_is_expired(deadline: Optional[datetime]) -> bool:
    if not deadline:
        return False
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return deadline < utc_now()


@router.post("/quote-requests", response_model=QuoteRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_quote_request(
    payload: QuoteRequestCreate,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(LineItem)
        .join(BoQ, LineItem.boq_id == BoQ.id)
        .options(selectinload(LineItem.boq))
        .where(LineItem.id == payload.line_item_id, BoQ.contractor_organisation_id == auth.organisation_id)
    )
    res = await db.execute(stmt)
    line_item = res.scalar_one_or_none()
    if not line_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LINE_ITEM_NOT_FOUND", "message": "Line item not found in contractor's BoQs."},
        )

    # Pre-broadcast safety gate: verify line item text quality
    is_corrupted, ratio, corrupt_reason = is_text_corrupted(line_item.description, is_line_item=True)
    if is_corrupted:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "CORRUPTED_LINE_ITEM",
                "message": f"Pre-broadcast safety gate blocked: Line item description contains garbled or corrupted text ({corrupt_reason}). Please edit or remove this item.",
            },
        )

    deadline = payload.response_deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    if deadline <= utc_now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_DEADLINE", "message": "Response deadline must be in the future."},
        )

    qr = QuoteRequest(
        line_item_id=line_item.id,
        requested_by_user_id=auth.user_id,
        response_deadline=deadline,
        status="open",
        created_at=utc_now(),
    )
    db.add(qr)

    line_item.pricing_status = "awaiting_quotes"
    line_item.updated_at = utc_now()
    if line_item.boq.status == "parsed":
        line_item.boq.status = "in_sourcing"
        line_item.boq.updated_at = utc_now()

    await db.flush()

    await log_audit_event(
        db=db,
        organisation_id=auth.organisation_id,
        actor_user_id=auth.user_id,
        entity_type="quote_request",
        entity_id=qr.id,
        action="quote_request.created",
        after_json={
            "line_item_id": line_item.id,
            "description": line_item.description,
            "deadline": deadline.isoformat(),
        },
    )

    await db.commit()
    await db.refresh(qr)

    return QuoteRequestResponse(
        id=qr.id,
        line_item_id=line_item.id,
        line_item_description=line_item.description,
        line_item_quantity=line_item.quantity,
        line_item_unit=line_item.unit,
        line_item_category=line_item.category,
        boq_id=line_item.boq_id,
        boq_title=line_item.boq.title,
        boq_region=line_item.boq.region,
        requested_by_user_id=qr.requested_by_user_id,
        response_deadline=qr.response_deadline,
        status=qr.status,
        created_at=qr.created_at,
        is_expired=check_is_expired(qr.response_deadline),
        quotes=[],
        supplier_count=0,
    )


@router.post("/quote-requests/{quote_request_id}/broadcast", response_model=QuoteRequestResponse)
async def broadcast_quote_request(
    quote_request_id: str,
    payload: Optional[QuoteRequestBroadcastRequest] = None,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(QuoteRequest)
        .join(LineItem, QuoteRequest.line_item_id == LineItem.id)
        .join(BoQ, LineItem.boq_id == BoQ.id)
        .options(
            selectinload(QuoteRequest.line_item).selectinload(LineItem.boq),
            selectinload(QuoteRequest.suppliers),
        )
        .where(QuoteRequest.id == quote_request_id, BoQ.contractor_organisation_id == auth.organisation_id)
    )
    res = await db.execute(stmt)
    qr = res.scalar_one_or_none()
    if not qr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "QUOTE_REQUEST_NOT_FOUND", "message": "Quote request not found."},
        )

    line_item = qr.line_item
    boq = line_item.boq

    # Pre-broadcast safety gate: verify line item text quality before broadcasting
    is_corrupted, ratio, corrupt_reason = is_text_corrupted(line_item.description, is_line_item=True)
    if is_corrupted:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "BROADCAST_BLOCKED_CORRUPTED_ITEM",
                "message": f"Pre-broadcast safety gate blocked: Cannot broadcast to suppliers because line item description contains garbled or corrupted text ({corrupt_reason}). Please edit or remove this item.",
            },
        )

    target_supplier_ids = []
    if payload and payload.supplier_organisation_ids:
        target_supplier_ids = payload.supplier_organisation_ids
    else:
        matched = await match_suppliers_for_item(category=line_item.category, region=boq.region, db=db)
        target_supplier_ids = [m.organisation_id for m in matched]

    if not target_supplier_ids:
        all_sup_stmt = select(Organisation.id).where(Organisation.type == "supplier")
        sup_res = await db.execute(all_sup_stmt)
        target_supplier_ids = [r[0] for r in sup_res.all()]

    existing_supplier_ids = {s.supplier_organisation_id for s in qr.suppliers}
    notification_provider = get_notification_provider()

    broadcast_count = 0
    for sup_id in target_supplier_ids:
        if sup_id not in existing_supplier_ids:
            qrs = QuoteRequestSupplier(
                quote_request_id=qr.id,
                supplier_organisation_id=sup_id,
                delivered_at=utc_now(),
                status="sent",
            )
            db.add(qrs)
            broadcast_count += 1

            sup_stmt = select(Organisation).where(Organisation.id == sup_id)
            sup_res = await db.execute(sup_stmt)
            supplier_org = sup_res.scalar_one_or_none()
            if supplier_org:
                await notification_provider.send_quote_request_notification(
                    supplier_id=supplier_org.id,
                    supplier_name=supplier_org.legal_name,
                    supplier_contact=supplier_org.phone or supplier_org.email,
                    channel="whatsapp",
                    boq_title=boq.title,
                    line_item_description=line_item.description,
                    quantity=line_item.quantity,
                    unit=line_item.unit,
                    response_deadline_iso=qr.response_deadline.isoformat(),
                    submission_link=f"/supplier/quote-requests/{qr.id}",
                )

    await log_audit_event(
        db=db,
        organisation_id=auth.organisation_id,
        actor_user_id=auth.user_id,
        entity_type="quote_request",
        entity_id=qr.id,
        action="quote_request.broadcast",
        after_json={"broadcast_count": broadcast_count, "total_suppliers": len(target_supplier_ids)},
    )

    await db.commit()
    await db.refresh(qr)

    return QuoteRequestResponse(
        id=qr.id,
        line_item_id=line_item.id,
        line_item_description=line_item.description,
        line_item_quantity=line_item.quantity,
        line_item_unit=line_item.unit,
        line_item_category=line_item.category,
        boq_id=boq.id,
        boq_title=boq.title,
        boq_region=boq.region,
        requested_by_user_id=qr.requested_by_user_id,
        response_deadline=qr.response_deadline,
        status=qr.status,
        created_at=qr.created_at,
        is_expired=check_is_expired(qr.response_deadline),
        quotes=[],
        supplier_count=broadcast_count or len(target_supplier_ids) or len(qr.suppliers),
    )


@router.post("/boqs/{boq_id}/validate-broadcast", response_model=ValidateBroadcastResponse)
async def validate_boq_broadcast_safety(
    boq_id: str,
    payload: ValidateBroadcastRequest,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    """Hard Pre-Broadcast Safety Gate: Validates that selected line items contain readable,
    uncorrupted text before any RFQs can be broadcast to suppliers.
    """
    boq_stmt = select(BoQ).where(BoQ.id == boq_id, BoQ.contractor_organisation_id == auth.organisation_id)
    boq_res = await db.execute(boq_stmt)
    boq = boq_res.scalar_one_or_none()
    if not boq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "BOQ_NOT_FOUND", "message": "BoQ not found."})

    if not payload.line_item_ids:
        return ValidateBroadcastResponse(
            is_safe=True,
            safe=True,
            total_items=0,
            valid_items_count=0,
            corrupted_items_count=0,
            corrupted_items=[],
            message="No line items provided for validation.",
        )

    stmt = select(LineItem).where(LineItem.id.in_(payload.line_item_ids), LineItem.boq_id == boq_id)
    res = await db.execute(stmt)
    items = res.scalars().all()

    corrupted_reports: List[CorruptedItemReport] = []
    for item in items:
        is_corrupted, ratio, corrupt_reason = is_text_corrupted(item.description, is_line_item=True)
        if is_corrupted:
            corrupted_reports.append(
                CorruptedItemReport(
                    id=item.id,
                    line_item_id=item.id,
                    description=item.description,
                    reason=corrupt_reason,
                    corruption_ratio=ratio,
                )
            )

    is_safe = len(corrupted_reports) == 0
    valid_count = len(items) - len(corrupted_reports)
    if is_safe:
        msg = f"All {len(items)} selected line items passed text quality validation."
    else:
        msg = f"Pre-broadcast safety gate active: {len(corrupted_reports)} of {len(items)} selected line items contain corrupted text. Broadcast is blocked."

    return ValidateBroadcastResponse(
        is_safe=is_safe,
        safe=is_safe,
        total_items=len(items),
        valid_items_count=valid_count,
        corrupted_items_count=len(corrupted_reports),
        corrupted_items=corrupted_reports,
        message=msg,
    )


@router.get("/quote-requests", response_model=List[QuoteRequestResponse])
async def list_contractor_quote_requests(
    boq_id: Optional[str] = None,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(QuoteRequest)
        .join(LineItem, QuoteRequest.line_item_id == LineItem.id)
        .join(BoQ, LineItem.boq_id == BoQ.id)
        .options(
            selectinload(QuoteRequest.line_item).selectinload(LineItem.boq),
            selectinload(QuoteRequest.suppliers),
            selectinload(QuoteRequest.quotes).selectinload(Quote.supplier_organisation),
        )
        .where(BoQ.contractor_organisation_id == auth.organisation_id)
    )
    if boq_id:
        stmt = stmt.where(BoQ.id == boq_id)

    res = await db.execute(stmt)
    requests = res.scalars().all()

    output = []
    for qr in requests:
        li = qr.line_item
        boq = li.boq
        quotes_resp = [
            QuoteResponse(
                id=q.id,
                quote_request_id=q.quote_request_id,
                supplier_organisation_id=q.supplier_organisation_id,
                supplier_name=q.supplier_organisation.legal_name if q.supplier_organisation else None,
                unit_price_minor=q.unit_price_minor,
                total_price_minor=q.total_price_minor,
                currency=q.currency,
                lead_time_days=q.lead_time_days,
                notes=q.notes,
                is_selected=q.is_selected,
                submitted_at=q.submitted_at,
                created_at=q.created_at,
            )
            for q in qr.quotes
        ]
        output.append(
            QuoteRequestResponse(
                id=qr.id,
                line_item_id=li.id,
                line_item_description=li.description,
                line_item_quantity=li.quantity,
                line_item_unit=li.unit,
                line_item_category=li.category,
                boq_id=boq.id,
                boq_title=boq.title,
                boq_region=boq.region,
                requested_by_user_id=qr.requested_by_user_id,
                response_deadline=qr.response_deadline,
                status=qr.status,
                created_at=qr.created_at,
                is_expired=check_is_expired(qr.response_deadline),
                quotes=quotes_resp,
                supplier_count=len(qr.suppliers),
            )
        )
    return output


@router.get("/suppliers/quote-requests", response_model=List[QuoteRequestResponse])
async def list_supplier_quote_requests(
    auth: AuthContext = Depends(require_supplier),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(QuoteRequest)
        .join(QuoteRequestSupplier, QuoteRequest.id == QuoteRequestSupplier.quote_request_id)
        .join(LineItem, QuoteRequest.line_item_id == LineItem.id)
        .join(BoQ, LineItem.boq_id == BoQ.id)
        .options(
            selectinload(QuoteRequest.line_item).selectinload(LineItem.boq),
            selectinload(QuoteRequest.quotes).selectinload(Quote.supplier_organisation),
        )
        .where(QuoteRequestSupplier.supplier_organisation_id == auth.organisation_id)
        .order_by(QuoteRequest.response_deadline.asc())
    )
    res = await db.execute(stmt)
    requests = res.scalars().all()

    output = []
    for qr in requests:
        li = qr.line_item
        boq = li.boq
        my_quotes = [
            QuoteResponse(
                id=q.id,
                quote_request_id=q.quote_request_id,
                supplier_organisation_id=q.supplier_organisation_id,
                supplier_name=q.supplier_organisation.legal_name if q.supplier_organisation else None,
                unit_price_minor=q.unit_price_minor,
                total_price_minor=q.total_price_minor,
                currency=q.currency,
                lead_time_days=q.lead_time_days,
                notes=q.notes,
                is_selected=q.is_selected,
                submitted_at=q.submitted_at,
                created_at=q.created_at,
            )
            for q in qr.quotes
            if q.supplier_organisation_id == auth.organisation_id
        ]
        output.append(
            QuoteRequestResponse(
                id=qr.id,
                line_item_id=li.id,
                line_item_description=li.description,
                line_item_quantity=li.quantity,
                line_item_unit=li.unit,
                line_item_category=li.category,
                boq_id=boq.id,
                boq_title=boq.title,
                boq_region=boq.region,
                requested_by_user_id=qr.requested_by_user_id,
                response_deadline=qr.response_deadline,
                status=qr.status,
                created_at=qr.created_at,
                is_expired=check_is_expired(qr.response_deadline),
                quotes=my_quotes,
                supplier_count=1,
            )
        )
    return output


@router.get("/suppliers/quote-requests/{quote_request_id}", response_model=QuoteRequestResponse)
async def get_supplier_quote_request(
    quote_request_id: str,
    auth: AuthContext = Depends(require_supplier),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(QuoteRequest)
        .join(QuoteRequestSupplier, QuoteRequest.id == QuoteRequestSupplier.quote_request_id)
        .join(LineItem, QuoteRequest.line_item_id == LineItem.id)
        .join(BoQ, LineItem.boq_id == BoQ.id)
        .options(
            selectinload(QuoteRequest.line_item).selectinload(LineItem.boq),
            selectinload(QuoteRequest.quotes).selectinload(Quote.supplier_organisation),
        )
        .where(
            QuoteRequest.id == quote_request_id,
            QuoteRequestSupplier.supplier_organisation_id == auth.organisation_id,
        )
    )
    res = await db.execute(stmt)
    qr = res.scalar_one_or_none()
    if not qr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "REQUEST_NOT_FOUND", "message": "Quote request not found or not addressed to your organisation."},
        )

    view_stmt = select(QuoteRequestSupplier).where(
        QuoteRequestSupplier.quote_request_id == quote_request_id,
        QuoteRequestSupplier.supplier_organisation_id == auth.organisation_id,
    )
    v_res = await db.execute(view_stmt)
    delivery = v_res.scalar_one_or_none()
    if delivery and not delivery.viewed_at:
        delivery.viewed_at = utc_now()
        delivery.status = "viewed"
        await db.commit()

    li = qr.line_item
    boq = li.boq
    my_quotes = [
        QuoteResponse(
            id=q.id,
            quote_request_id=q.quote_request_id,
            supplier_organisation_id=q.supplier_organisation_id,
            supplier_name=q.supplier_organisation.legal_name if q.supplier_organisation else None,
            unit_price_minor=q.unit_price_minor,
            total_price_minor=q.total_price_minor,
            currency=q.currency,
            lead_time_days=q.lead_time_days,
            notes=q.notes,
            is_selected=q.is_selected,
            submitted_at=q.submitted_at,
            created_at=q.created_at,
        )
        for q in qr.quotes
        if q.supplier_organisation_id == auth.organisation_id
    ]

    return QuoteRequestResponse(
        id=qr.id,
        line_item_id=li.id,
        line_item_description=li.description,
        line_item_quantity=li.quantity,
        line_item_unit=li.unit,
        line_item_category=li.category,
        boq_id=boq.id,
        boq_title=boq.title,
        boq_region=boq.region,
        requested_by_user_id=qr.requested_by_user_id,
        response_deadline=qr.response_deadline,
        status=qr.status,
        created_at=qr.created_at,
        is_expired=check_is_expired(qr.response_deadline),
        quotes=my_quotes,
        supplier_count=1,
    )


@router.post("/quote-requests/{quote_request_id}/quotes", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def submit_quote(
    quote_request_id: str,
    payload: QuoteSubmitRequest,
    auth: AuthContext = Depends(require_supplier),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(QuoteRequest)
        .join(QuoteRequestSupplier, QuoteRequest.id == QuoteRequestSupplier.quote_request_id)
        .options(selectinload(QuoteRequest.line_item))
        .where(
            QuoteRequest.id == quote_request_id,
            QuoteRequestSupplier.supplier_organisation_id == auth.organisation_id,
        )
    )
    res = await db.execute(stmt)
    qr = res.scalar_one_or_none()
    if not qr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "REQUEST_NOT_FOUND", "message": "Quote request not found or not assigned to you."},
        )

    # Server-side deadline check
    if check_is_expired(qr.response_deadline):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "DEADLINE_EXPIRED",
                "message": "The submission deadline for this quote request has passed.",
                "deadline": qr.response_deadline.isoformat(),
            },
        )

    line_item = qr.line_item
    total_price = int(payload.unit_price_minor * line_item.quantity)
    now = utc_now()

    existing_quote_stmt = select(Quote).where(
        Quote.quote_request_id == quote_request_id,
        Quote.supplier_organisation_id == auth.organisation_id,
    )
    eq_res = await db.execute(existing_quote_stmt)
    quote = eq_res.scalar_one_or_none()

    if quote:
        quote.unit_price_minor = payload.unit_price_minor
        quote.total_price_minor = total_price
        quote.currency = payload.currency
        quote.lead_time_days = payload.lead_time_days
        quote.notes = payload.notes
        quote.submitted_at = now
    else:
        quote = Quote(
            quote_request_id=qr.id,
            supplier_organisation_id=auth.organisation_id,
            unit_price_minor=payload.unit_price_minor,
            total_price_minor=total_price,
            currency=payload.currency,
            lead_time_days=payload.lead_time_days,
            notes=payload.notes,
            is_selected=False,
            submitted_at=now,
            created_at=now,
        )
        db.add(quote)

    qrs_stmt = select(QuoteRequestSupplier).where(
        QuoteRequestSupplier.quote_request_id == qr.id,
        QuoteRequestSupplier.supplier_organisation_id == auth.organisation_id,
    )
    qrs_res = await db.execute(qrs_stmt)
    qrs = qrs_res.scalar_one_or_none()
    if qrs:
        qrs.status = "submitted"

    if line_item.pricing_status == "awaiting_quotes":
        line_item.pricing_status = "quoted"
        line_item.updated_at = now

    await db.flush()

    await log_audit_event(
        db=db,
        organisation_id=auth.organisation_id,
        actor_user_id=auth.user_id,
        entity_type="quote",
        entity_id=quote.id,
        action="quote.submitted",
        after_json={
            "unit_price_minor": quote.unit_price_minor,
            "total_price_minor": quote.total_price_minor,
            "lead_time_days": quote.lead_time_days,
        },
    )

    await db.commit()
    await db.refresh(quote)

    return QuoteResponse(
        id=quote.id,
        quote_request_id=quote.quote_request_id,
        supplier_organisation_id=quote.supplier_organisation_id,
        unit_price_minor=quote.unit_price_minor,
        total_price_minor=quote.total_price_minor,
        currency=quote.currency,
        lead_time_days=quote.lead_time_days,
        notes=quote.notes,
        is_selected=quote.is_selected,
        submitted_at=quote.submitted_at,
        created_at=quote.created_at,
    )


@router.get("/boqs/{boq_id}/quote-comparison", response_model=BoQQuoteComparisonResponse)
async def get_boq_quote_comparison(
    boq_id: str,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    boq_stmt = (
        select(BoQ)
        .options(
            selectinload(BoQ.line_items)
            .selectinload(LineItem.quote_requests)
            .selectinload(QuoteRequest.quotes)
            .selectinload(Quote.supplier_organisation)
        )
        .where(BoQ.id == boq_id, BoQ.contractor_organisation_id == auth.organisation_id)
    )
    res = await db.execute(boq_stmt)
    boq = res.scalar_one_or_none()
    if not boq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BOQ_NOT_FOUND", "message": "BoQ not found."},
        )

    line_item_comparisons = []
    total_priced = 0
    total_estimated = 0

    for li in boq.line_items:
        active_qr = li.quote_requests[-1] if li.quote_requests else None
        qr_quotes = active_qr.quotes if active_qr else []

        quotes_list: List[QuoteResponse] = []
        for q in qr_quotes:
            quotes_list.append(
                QuoteResponse(
                    id=q.id,
                    quote_request_id=q.quote_request_id,
                    supplier_organisation_id=q.supplier_organisation_id,
                    supplier_name=q.supplier_organisation.legal_name if q.supplier_organisation else "Unknown Supplier",
                    unit_price_minor=q.unit_price_minor,
                    total_price_minor=q.total_price_minor,
                    currency=q.currency,
                    lead_time_days=q.lead_time_days,
                    notes=q.notes,
                    is_selected=q.is_selected,
                    submitted_at=q.submitted_at,
                    created_at=q.created_at,
                )
            )

        lowest_quote = min(quotes_list, key=lambda q: q.unit_price_minor) if quotes_list else None
        quotes_with_lead = [q for q in quotes_list if q.lead_time_days is not None]
        fastest_quote = min(quotes_with_lead, key=lambda q: q.lead_time_days) if quotes_with_lead else None
        selected_quote = next((q for q in quotes_list if q.is_selected), None)

        if li.final_price_minor:
            total_priced += int(li.final_price_minor * li.quantity)
        elif lowest_quote:
            total_estimated += int(lowest_quote.unit_price_minor * li.quantity)
        elif li.benchmark_max_minor:
            total_estimated += int(li.benchmark_max_minor * li.quantity)

        deadline = active_qr.response_deadline if active_qr else None
        is_passed = check_is_expired(deadline) if deadline else False

        line_item_comparisons.append(
            LineItemComparisonResponse(
                line_item_id=li.id,
                description=li.description,
                unit=li.unit,
                quantity=li.quantity,
                category=li.category,
                benchmark_min_minor=li.benchmark_min_minor,
                benchmark_max_minor=li.benchmark_max_minor,
                final_price_minor=li.final_price_minor,
                pricing_status=li.pricing_status,
                quote_request_id=active_qr.id if active_qr else None,
                response_deadline=deadline,
                is_deadline_passed=is_passed,
                quotes=quotes_list,
                lowest_quote=lowest_quote,
                fastest_quote=fastest_quote,
                selected_quote=selected_quote,
            )
        )

    return BoQQuoteComparisonResponse(
        boq_id=boq.id,
        title=boq.title,
        region=boq.region,
        tender_deadline=boq.tender_deadline,
        line_items=line_item_comparisons,
        total_estimated_minor=total_estimated,
        total_priced_minor=total_priced,
    )


@router.post("/quote-requests/{quote_request_id}/select", response_model=LineItemComparisonResponse)
async def select_winning_quote(
    quote_request_id: str,
    payload: QuoteSelectRequest,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(QuoteRequest)
        .join(LineItem, QuoteRequest.line_item_id == LineItem.id)
        .join(BoQ, LineItem.boq_id == BoQ.id)
        .options(
            selectinload(QuoteRequest.line_item).selectinload(LineItem.boq),
            selectinload(QuoteRequest.quotes).selectinload(Quote.supplier_organisation),
        )
        .where(QuoteRequest.id == quote_request_id, BoQ.contractor_organisation_id == auth.organisation_id)
    )
    res = await db.execute(stmt)
    qr = res.scalar_one_or_none()
    if not qr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "REQUEST_NOT_FOUND", "message": "Quote request not found."})

    target_quote = next((q for q in qr.quotes if q.id == payload.quote_id), None)
    if not target_quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "QUOTE_NOT_FOUND", "message": "Quote ID not found in this request."})

    for q in qr.quotes:
        q.is_selected = (q.id == payload.quote_id)

    line_item = qr.line_item
    before_price = line_item.final_price_minor
    line_item.final_price_minor = target_quote.unit_price_minor
    line_item.pricing_status = "selected"
    line_item.updated_at = utc_now()

    await log_audit_event(
        db=db,
        organisation_id=auth.organisation_id,
        actor_user_id=auth.user_id,
        entity_type="line_item",
        entity_id=line_item.id,
        action="quote.selected",
        before_json={"final_price_minor": before_price},
        after_json={
            "final_price_minor": target_quote.unit_price_minor,
            "quote_id": target_quote.id,
            "supplier_id": target_quote.supplier_organisation_id,
            "supplier_name": target_quote.supplier_organisation.legal_name if target_quote.supplier_organisation else None,
        },
    )

    await db.commit()

    quotes_list = [
        QuoteResponse(
            id=q.id,
            quote_request_id=q.quote_request_id,
            supplier_organisation_id=q.supplier_organisation_id,
            supplier_name=q.supplier_organisation.legal_name if q.supplier_organisation else None,
            unit_price_minor=q.unit_price_minor,
            total_price_minor=q.total_price_minor,
            currency=q.currency,
            lead_time_days=q.lead_time_days,
            notes=q.notes,
            is_selected=q.is_selected,
            submitted_at=q.submitted_at,
            created_at=q.created_at,
        )
        for q in qr.quotes
    ]

    lowest = min(quotes_list, key=lambda q: q.unit_price_minor) if quotes_list else None
    quotes_with_lead = [q for q in quotes_list if q.lead_time_days is not None]
    fastest = min(quotes_with_lead, key=lambda q: q.lead_time_days) if quotes_with_lead else None
    selected = next((q for q in quotes_list if q.is_selected), None)

    return LineItemComparisonResponse(
        line_item_id=line_item.id,
        description=line_item.description,
        unit=line_item.unit,
        quantity=line_item.quantity,
        category=line_item.category,
        benchmark_min_minor=line_item.benchmark_min_minor,
        benchmark_max_minor=line_item.benchmark_max_minor,
        final_price_minor=line_item.final_price_minor,
        pricing_status=line_item.pricing_status,
        quote_request_id=qr.id,
        response_deadline=qr.response_deadline,
        is_deadline_passed=check_is_expired(qr.response_deadline),
        quotes=quotes_list,
        lowest_quote=lowest,
        fastest_quote=fastest,
        selected_quote=selected,
    )


@router.post("/boqs/{boq_id}/line-items/{line_item_id}/price-override", response_model=LineItemComparisonResponse)
async def override_line_item_price(
    boq_id: str,
    line_item_id: str,
    payload: PriceOverrideRequest,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(LineItem)
        .join(BoQ, LineItem.boq_id == BoQ.id)
        .options(
            selectinload(LineItem.quote_requests).selectinload(QuoteRequest.quotes).selectinload(Quote.supplier_organisation)
        )
        .where(LineItem.id == line_item_id, BoQ.id == boq_id, BoQ.contractor_organisation_id == auth.organisation_id)
    )
    res = await db.execute(stmt)
    line_item = res.scalar_one_or_none()
    if not line_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LINE_ITEM_NOT_FOUND", "message": "Line item not found in this BoQ."},
        )

    before_price = line_item.final_price_minor
    line_item.final_price_minor = payload.price_minor
    line_item.pricing_status = "manually_priced"
    line_item.updated_at = utc_now()

    for qr in line_item.quote_requests:
        for q in qr.quotes:
            q.is_selected = False

    await log_audit_event(
        db=db,
        organisation_id=auth.organisation_id,
        actor_user_id=auth.user_id,
        entity_type="line_item",
        entity_id=line_item.id,
        action="line_item.price_overridden",
        before_json={"final_price_minor": before_price},
        after_json={"final_price_minor": payload.price_minor, "reason": payload.reason},
        metadata_json={"reason": payload.reason},
    )

    await db.commit()

    active_qr = line_item.quote_requests[-1] if line_item.quote_requests else None
    quotes_list = []
    if active_qr:
        quotes_list = [
            QuoteResponse(
                id=q.id,
                quote_request_id=q.quote_request_id,
                supplier_organisation_id=q.supplier_organisation_id,
                supplier_name=q.supplier_organisation.legal_name if q.supplier_organisation else None,
                unit_price_minor=q.unit_price_minor,
                total_price_minor=q.total_price_minor,
                currency=q.currency,
                lead_time_days=q.lead_time_days,
                notes=q.notes,
                is_selected=q.is_selected,
                submitted_at=q.submitted_at,
                created_at=q.created_at,
            )
            for q in active_qr.quotes
        ]

    return LineItemComparisonResponse(
        line_item_id=line_item.id,
        description=line_item.description,
        unit=line_item.unit,
        quantity=line_item.quantity,
        category=line_item.category,
        benchmark_min_minor=line_item.benchmark_min_minor,
        benchmark_max_minor=line_item.benchmark_max_minor,
        final_price_minor=line_item.final_price_minor,
        pricing_status=line_item.pricing_status,
        quote_request_id=active_qr.id if active_qr else None,
        response_deadline=active_qr.response_deadline if active_qr else None,
        is_deadline_passed=check_is_expired(active_qr.response_deadline) if active_qr else False,
        quotes=quotes_list,
        lowest_quote=None,
        fastest_quote=None,
        selected_quote=None,
    )


@router.post("/quote-requests/{id}/simulate-responses", status_code=status.HTTP_200_OK)
async def simulate_quote_request_responses(
    id: str,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    """Demo simulation endpoint: Simulates realistic competitive supplier quote submissions for an open request."""
    quotes = await simulate_supplier_quotes_for_request(
        quote_request_id=id,
        db=db,
        actor_user_id=auth.user_id,
    )
    return {
        "status": "success",
        "message": f"Generated {len(quotes)} simulated supplier quote(s).",
        "quotes_count": len(quotes),
    }


@router.post("/boqs/{id}/simulate-quotes", status_code=status.HTTP_200_OK)
async def simulate_all_boq_quotes(
    id: str,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    """Demo simulation endpoint: Simulates supplier quotes across all open quote requests on a BoQ."""
    total = await simulate_all_quotes_for_boq(
        boq_id=id,
        db=db,
        actor_user_id=auth.user_id,
    )
    return {
        "status": "success",
        "message": f"Generated {total} simulated supplier quote(s) across all open requests.",
        "total_quotes": total,
    }


@router.post("/boqs/{id}/auto-select-best-quotes", status_code=status.HTTP_200_OK)
async def auto_select_best_quotes_for_boq(
    id: str,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    """Automatically selects the lowest submitted quote for each line item of a BoQ."""
    boq_stmt = select(BoQ).where(BoQ.id == id, BoQ.contractor_organisation_id == auth.organisation_id)
    boq_res = await db.execute(boq_stmt)
    boq = boq_res.scalar_one_or_none()
    if not boq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BOQ_NOT_FOUND", "message": "BoQ not found or access denied."},
        )

    qr_stmt = (
        select(QuoteRequest)
        .join(LineItem, QuoteRequest.line_item_id == LineItem.id)
        .options(
            selectinload(QuoteRequest.quotes).selectinload(Quote.supplier_organisation),
            selectinload(QuoteRequest.line_item),
        )
        .where(LineItem.boq_id == id)
    )
    qr_res = await db.execute(qr_stmt)
    quote_requests = qr_res.scalars().all()

    selected_count = 0
    updated_items = []

    for qr in quote_requests:
        if not qr.quotes:
            continue

        cheapest_quote = min(qr.quotes, key=lambda q: q.unit_price_minor)

        for q in qr.quotes:
            q.is_selected = (q.id == cheapest_quote.id)

        qr.updated_at = utc_now()

        li = qr.line_item
        if li:
            li.final_price_minor = cheapest_quote.unit_price_minor
            li.pricing_status = "priced_from_quote"
            li.updated_at = utc_now()

            await log_audit_event(
                db=db,
                organisation_id=auth.organisation_id,
                actor_user_id=auth.user_id,
                entity_type="line_item",
                entity_id=li.id,
                action="quote.auto_selected",
                after_json={
                    "quote_id": cheapest_quote.id,
                    "quote_request_id": qr.id,
                    "unit_price_minor": cheapest_quote.unit_price_minor,
                    "supplier_organisation_id": cheapest_quote.supplier_organisation_id,
                    "selection_method": "auto_best_price",
                },
            )
            selected_count += 1
            updated_items.append({
                "line_item_id": li.id,
                "description": li.description,
                "selected_price_minor": cheapest_quote.unit_price_minor,
                "supplier_id": cheapest_quote.supplier_organisation_id,
            })

    # Recalculate total priced across all line items of this BoQ
    all_li_stmt = select(LineItem).where(LineItem.boq_id == id)
    all_li_res = await db.execute(all_li_stmt)
    all_line_items = all_li_res.scalars().all()

    total_priced_minor = sum(
        int((li.final_price_minor or 0) * (li.quantity or 1.0))
        for li in all_line_items
        if li.final_price_minor
    )

    await db.commit()

    return {
        "status": "success",
        "selected_count": selected_count,
        "total_priced_minor": total_priced_minor,
        "updated_items": updated_items,
        "message": f"Automatically selected the lowest quote for {selected_count} line items.",
    }


