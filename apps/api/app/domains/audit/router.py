from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.models import AuditEvent, BoQ, LineItem, Quote, QuoteRequest, User
from app.core.security import AuthContext, require_contractor
from app.schemas.audit import AuditEventResponse

router = APIRouter(tags=["Audit"])


@router.get("/boqs/{boq_id}/audit", response_model=List[AuditEventResponse])
async def get_boq_audit_trail(
    boq_id: str,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    # Verify BoQ ownership
    boq_stmt = select(BoQ).where(
        BoQ.id == boq_id,
        BoQ.contractor_organisation_id == auth.organisation_id
    )
    boq_res = await db.execute(boq_stmt)
    boq = boq_res.scalar_one_or_none()
    if not boq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BOQ_NOT_FOUND", "message": "BoQ document not found."},
        )

    # Get all line item IDs
    li_stmt = select(LineItem.id).where(LineItem.boq_id == boq_id)
    li_res = await db.execute(li_stmt)
    line_item_ids = [r[0] for r in li_res.all()]

    quote_request_ids = []
    quote_ids = []

    if line_item_ids:
        qr_stmt = select(QuoteRequest.id).where(QuoteRequest.line_item_id.in_(line_item_ids))
        qr_res = await db.execute(qr_stmt)
        quote_request_ids = [r[0] for r in qr_res.all()]

        if quote_request_ids:
            q_stmt = select(Quote.id).where(Quote.quote_request_id.in_(quote_request_ids))
            q_res = await db.execute(q_stmt)
            quote_ids = [r[0] for r in q_res.all()]

    target_ids = [boq_id] + line_item_ids + quote_request_ids + quote_ids

    # Query audit events
    stmt = (
        select(AuditEvent, User.name.label("actor_name"))
        .outerjoin(User, AuditEvent.actor_user_id == User.id)
        .where(
            AuditEvent.entity_id.in_(target_ids),
        )
        .order_by(AuditEvent.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    audit_responses = []
    for event, actor_name in rows:
        resp = AuditEventResponse(
            id=event.id,
            organisation_id=event.organisation_id,
            actor_user_id=event.actor_user_id,
            actor_name=actor_name,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            action=event.action,
            before_json=event.before_json,
            after_json=event.after_json,
            metadata_json=event.metadata_json,
            created_at=event.created_at,
        )
        audit_responses.append(resp)

    return audit_responses
