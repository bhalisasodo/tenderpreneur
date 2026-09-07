import hashlib
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.models import AuditEvent, BoQ, Document, LineItem, QuoteRequest, utc_now
from app.core.security import AuthContext, require_contractor
from app.domains.audit.service import log_audit_event
from app.integrations.storage import get_storage_provider
from app.schemas.boq import (
    BoQCreate,
    BoQResponse,
    BoQSummaryResponse,
    BoQUpdate,
    DocumentResponse,
    LineItemCreate,
    LineItemResponse,
    LineItemUpdate,
)

router = APIRouter(prefix="/boqs", tags=["BoQs"])


@router.post("", response_model=BoQResponse, status_code=status.HTTP_201_CREATED)
async def create_boq(
    payload: BoQCreate,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    boq = BoQ(
        contractor_organisation_id=auth.organisation_id,
        title=payload.title,
        tender_reference=payload.tender_reference,
        tender_deadline=payload.tender_deadline,
        region=payload.region,
        status="draft",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(boq)
    await db.flush()

    await log_audit_event(
        db=db,
        organisation_id=auth.organisation_id,
        actor_user_id=auth.user_id,
        entity_type="boq",
        entity_id=boq.id,
        action="boq.created",
        after_json={"title": boq.title, "tender_reference": boq.tender_reference, "region": boq.region},
    )

    await db.commit()
    await db.refresh(boq)
    return BoQResponse.model_validate(boq)


@router.get("", response_model=List[BoQSummaryResponse])
async def list_contractor_boqs(
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(BoQ)
        .options(selectinload(BoQ.line_items))
        .where(BoQ.contractor_organisation_id == auth.organisation_id)
        .order_by(BoQ.created_at.desc())
    )
    res = await db.execute(stmt)
    boqs = res.scalars().all()

    summaries = []
    for b in boqs:
        total_priced = sum(
            int((li.final_price_minor or 0) * (li.quantity or 1.0))
            for li in b.line_items
            if li.final_price_minor
        )
        summaries.append(
            BoQSummaryResponse(
                id=b.id,
                contractor_organisation_id=b.contractor_organisation_id,
                title=b.title,
                tender_reference=b.tender_reference,
                tender_deadline=b.tender_deadline,
                region=b.region,
                status=b.status,
                line_item_count=len(b.line_items),
                total_priced_minor=total_priced,
                created_at=b.created_at,
                updated_at=b.updated_at,
            )
        )
    return summaries


@router.get("/{boq_id}", response_model=BoQResponse)
async def get_boq_details(
    boq_id: str,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(BoQ)
        .options(selectinload(BoQ.source_document), selectinload(BoQ.line_items))
        .where(BoQ.id == boq_id, BoQ.contractor_organisation_id == auth.organisation_id)
    )
    res = await db.execute(stmt)
    boq = res.scalar_one_or_none()
    if not boq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BOQ_NOT_FOUND", "message": "BoQ not found or access denied."},
        )
    return BoQResponse.model_validate(boq)


@router.patch("/{boq_id}", response_model=BoQResponse)
async def update_boq(
    boq_id: str,
    payload: BoQUpdate,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(BoQ)
        .options(selectinload(BoQ.source_document), selectinload(BoQ.line_items))
        .where(BoQ.id == boq_id, BoQ.contractor_organisation_id == auth.organisation_id)
    )
    res = await db.execute(stmt)
    boq = res.scalar_one_or_none()
    if not boq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BOQ_NOT_FOUND", "message": "BoQ not found."},
        )

    if payload.title is not None:
        boq.title = payload.title
    if payload.tender_reference is not None:
        boq.tender_reference = payload.tender_reference
    if payload.tender_deadline is not None:
        boq.tender_deadline = payload.tender_deadline
    if payload.region is not None:
        boq.region = payload.region
    if payload.status is not None:
        boq.status = payload.status

    boq.updated_at = utc_now()
    await db.commit()
    await db.refresh(boq)
    return BoQResponse.model_validate(boq)


@router.delete("/{boq_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_boq(
    boq_id: str,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    """Permanently deletes a BoQ, cascading to line items, quote requests, quotes, and cleaning up source documents."""
    stmt = (
        select(BoQ)
        .options(
            selectinload(BoQ.source_document),
            selectinload(BoQ.line_items)
            .selectinload(LineItem.quote_requests)
            .selectinload(QuoteRequest.suppliers),
            selectinload(BoQ.line_items)
            .selectinload(LineItem.quote_requests)
            .selectinload(QuoteRequest.quotes),
        )
        .where(BoQ.id == boq_id, BoQ.contractor_organisation_id == auth.organisation_id)
    )
    res = await db.execute(stmt)
    boq = res.scalar_one_or_none()
    if not boq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BOQ_NOT_FOUND", "message": "BoQ not found or access denied."},
        )

    # 1. Log audit event before deletion to preserve audit history and provenance
    await log_audit_event(
        db=db,
        organisation_id=auth.organisation_id,
        actor_user_id=auth.user_id,
        entity_type="boq",
        entity_id=boq_id,
        action="boq.deleted",
        before_json={
            "id": boq.id,
            "title": boq.title,
            "tender_reference": boq.tender_reference,
            "region": boq.region,
            "status": boq.status,
            "line_item_count": len(boq.line_items),
        },
    )

    # 2. Cleanup linked source document if not referenced by any other BoQ
    source_doc = boq.source_document
    if source_doc:
        boq.source_document_id = None
        other_boq_stmt = select(func.count(BoQ.id)).where(BoQ.source_document_id == source_doc.id, BoQ.id != boq_id)
        other_count_res = await db.execute(other_boq_stmt)
        other_count = other_count_res.scalar() or 0
        if other_count == 0:
            storage_provider = get_storage_provider()
            try:
                await storage_provider.delete_file(source_doc.storage_key)
            except Exception:
                pass
            await db.delete(source_doc)

    # 3. Delete BoQ (SQLAlchemy relationship cascades will delete line items, quote requests, suppliers, quotes)
    await db.delete(boq)
    await db.commit()


@router.post("/{boq_id}/documents", response_model=DocumentResponse)
async def upload_boq_document(
    boq_id: str,
    file: UploadFile = File(...),
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    # Verify BoQ ownership
    boq_stmt = select(BoQ).where(BoQ.id == boq_id, BoQ.contractor_organisation_id == auth.organisation_id)
    boq_res = await db.execute(boq_stmt)
    boq = boq_res.scalar_one_or_none()
    if not boq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BOQ_NOT_FOUND", "message": "BoQ not found."},
        )

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_FILE", "message": "Uploaded file cannot be empty."},
        )

    if len(contents) > settings.max_upload_size_bytes:
        max_mb = settings.max_upload_size_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"Uploaded file ({len(contents) / (1024 * 1024):.1f}MB) exceeds the maximum allowed size of {max_mb}MB.",
            },
        )

    allowed_extensions = {"pdf", "xlsx", "xls", "csv", "txt"}
    extension = (file.filename.split(".")[-1] if "." in file.filename else "bin").lower()
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "code": "UNSUPPORTED_MEDIA_TYPE",
                "message": f"File extension '.{extension}' is not supported. Allowed formats: PDF, Excel (.xlsx, .xls), CSV, or text.",
            },
        )

    # Compute checksum
    checksum = hashlib.sha256(contents).hexdigest()
    storage_provider = get_storage_provider()
    
    # Store with secure key
    storage_key = f"documents/{auth.organisation_id}/{boq_id}/{uuid.uuid4()}.{extension}"
    await storage_provider.upload_file(storage_key, contents, file.content_type or "application/octet-stream")

    doc = Document(
        owner_organisation_id=auth.organisation_id,
        storage_key=storage_key,
        original_filename=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(contents),
        checksum=checksum,
        created_at=utc_now(),
    )
    db.add(doc)
    await db.flush()

    boq.source_document_id = doc.id
    boq.updated_at = utc_now()

    await log_audit_event(
        db=db,
        organisation_id=auth.organisation_id,
        actor_user_id=auth.user_id,
        entity_type="boq",
        entity_id=boq_id,
        action="document.uploaded",
        after_json={"filename": file.filename, "size_bytes": len(contents), "document_id": doc.id},
    )

    await db.commit()
    await db.refresh(doc)
    return DocumentResponse.model_validate(doc)


@router.post("/{boq_id}/line-items", response_model=LineItemResponse, status_code=status.HTTP_201_CREATED)
async def add_line_item(
    boq_id: str,
    payload: LineItemCreate,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    boq_stmt = select(BoQ).where(BoQ.id == boq_id, BoQ.contractor_organisation_id == auth.organisation_id)
    boq_res = await db.execute(boq_stmt)
    boq = boq_res.scalar_one_or_none()
    if not boq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BOQ_NOT_FOUND", "message": "BoQ not found."},
        )

    item = LineItem(
        boq_id=boq_id,
        source_row_reference=payload.source_row_reference,
        description=payload.description,
        unit=payload.unit,
        quantity=payload.quantity,
        category=payload.category,
        benchmark_min_minor=payload.benchmark_min_minor,
        benchmark_max_minor=payload.benchmark_max_minor,
        benchmark_source=payload.benchmark_source,
        benchmark_currency=payload.benchmark_currency,
        pricing_status="unsourced",
        parsing_confidence=1.0,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(item)
    await db.flush()

    await log_audit_event(
        db=db,
        organisation_id=auth.organisation_id,
        actor_user_id=auth.user_id,
        entity_type="line_item",
        entity_id=item.id,
        action="line_item.created",
        after_json={"description": item.description, "quantity": item.quantity, "unit": item.unit},
    )

    await db.commit()
    await db.refresh(item)
    return LineItemResponse.model_validate(item)


@router.patch("/{boq_id}/line-items/{line_item_id}", response_model=LineItemResponse)
async def correct_line_item(
    boq_id: str,
    line_item_id: str,
    payload: LineItemUpdate,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    # Verify BoQ ownership
    boq_stmt = select(BoQ).where(BoQ.id == boq_id, BoQ.contractor_organisation_id == auth.organisation_id)
    boq_res = await db.execute(boq_stmt)
    boq = boq_res.scalar_one_or_none()
    if not boq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BOQ_NOT_FOUND", "message": "BoQ not found."},
        )

    item_stmt = select(LineItem).where(LineItem.id == line_item_id, LineItem.boq_id == boq_id)
    item_res = await db.execute(item_stmt)
    item = item_res.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LINE_ITEM_NOT_FOUND", "message": "Line item not found in this BoQ."},
        )

    before_state = {
        "description": item.description,
        "unit": item.unit,
        "quantity": item.quantity,
        "category": item.category,
        "final_price_minor": item.final_price_minor,
        "review_status": item.review_status,
    }

    changed_fields = []
    if payload.description is not None:
        item.description = payload.description
        changed_fields.append("description")
    if payload.unit is not None:
        item.unit = payload.unit
        changed_fields.append("unit")
    if payload.quantity is not None:
        item.quantity = payload.quantity
        changed_fields.append("quantity")
    if payload.category is not None:
        item.category = payload.category
        changed_fields.append("category")
    if payload.benchmark_min_minor is not None:
        item.benchmark_min_minor = payload.benchmark_min_minor
    if payload.benchmark_max_minor is not None:
        item.benchmark_max_minor = payload.benchmark_max_minor
    if payload.benchmark_source is not None:
        item.benchmark_source = payload.benchmark_source
    if payload.final_price_minor is not None:
        item.final_price_minor = payload.final_price_minor
    if payload.pricing_status is not None:
        item.pricing_status = payload.pricing_status
    if payload.review_status is not None:
        item.review_status = payload.review_status
        changed_fields.append("review_status")
    if payload.exclusion_reason is not None:
        item.exclusion_reason = payload.exclusion_reason

    # Mark as accepted once contractor explicitly reviews and corrects it
    if item.review_status == "needs_review" and payload.review_status is None:
        item.review_status = "accepted"

    item.updated_at = utc_now()

    after_state = {
        "description": item.description,
        "unit": item.unit,
        "quantity": item.quantity,
        "category": item.category,
        "final_price_minor": item.final_price_minor,
        "review_status": item.review_status,
    }

    # Record general edit audit event
    await log_audit_event(
        db=db,
        organisation_id=auth.organisation_id,
        actor_user_id=auth.user_id,
        entity_type="line_item",
        entity_id=item.id,
        action="line_item.edited",
        before_json=before_state,
        after_json=after_state,
    )

    # Record structured parser learning/correction feedback
    await log_audit_event(
        db=db,
        organisation_id=auth.organisation_id,
        actor_user_id=auth.user_id,
        entity_type="line_item",
        entity_id=item.id,
        action="parser.candidate_corrected",
        before_json=before_state,
        after_json={
            "corrected_state": after_state,
            "fields_changed": changed_fields,
            "original_confidence": item.parsing_confidence,
        },
    )

    await db.commit()
    await db.refresh(item)
    return LineItemResponse.model_validate(item)


@router.post("/{boq_id}/line-items/{line_item_id}/restore", response_model=LineItemResponse)
async def restore_line_item(
    boq_id: str,
    line_item_id: str,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    """Restores an excluded or low-confidence candidate back into the active BoQ queue."""
    boq_stmt = select(BoQ).where(BoQ.id == boq_id, BoQ.contractor_organisation_id == auth.organisation_id)
    boq_res = await db.execute(boq_stmt)
    boq = boq_res.scalar_one_or_none()
    if not boq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "BOQ_NOT_FOUND", "message": "BoQ not found."})

    item_stmt = select(LineItem).where(LineItem.id == line_item_id, LineItem.boq_id == boq_id)
    item_res = await db.execute(item_stmt)
    item = item_res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "LINE_ITEM_NOT_FOUND", "message": "Line item not found."})

    before_status = item.review_status
    item.review_status = "accepted"
    item.exclusion_reason = None
    item.updated_at = utc_now()

    await log_audit_event(
        db=db,
        organisation_id=auth.organisation_id,
        actor_user_id=auth.user_id,
        entity_type="line_item",
        entity_id=item.id,
        action="parser.candidate_restored",
        before_json={"review_status": before_status},
        after_json={"review_status": "accepted", "description": item.description},
    )

    await db.commit()
    await db.refresh(item)
    return LineItemResponse.model_validate(item)


@router.delete("/{boq_id}/line-items/{line_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_line_item(
    boq_id: str,
    line_item_id: str,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    boq_stmt = select(BoQ).where(BoQ.id == boq_id, BoQ.contractor_organisation_id == auth.organisation_id)
    boq_res = await db.execute(boq_stmt)
    boq = boq_res.scalar_one_or_none()
    if not boq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "BOQ_NOT_FOUND", "message": "BoQ not found."})

    item_stmt = select(LineItem).where(LineItem.id == line_item_id, LineItem.boq_id == boq_id)
    item_res = await db.execute(item_stmt)
    item = item_res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "LINE_ITEM_NOT_FOUND", "message": "Line item not found."})

    await db.delete(item)
    await log_audit_event(
        db=db,
        organisation_id=auth.organisation_id,
        actor_user_id=auth.user_id,
        entity_type="line_item",
        entity_id=line_item_id,
        action="line_item.deleted",
        before_json={"description": item.description},
    )
    # Record structured parser learning/removal feedback
    await log_audit_event(
        db=db,
        organisation_id=auth.organisation_id,
        actor_user_id=auth.user_id,
        entity_type="line_item",
        entity_id=line_item_id,
        action="parser.candidate_removed",
        before_json={
            "description": item.description,
            "unit": item.unit,
            "quantity": item.quantity,
            "category": item.category,
            "parsing_confidence": item.parsing_confidence,
            "source_row_reference": item.source_row_reference,
        },
    )
    await db.commit()


class BulkDeleteLineItemsRequest(BaseModel):
    line_item_ids: List[str]


@router.post("/{boq_id}/line-items/bulk-delete", status_code=status.HTTP_200_OK)
async def bulk_delete_line_items(
    boq_id: str,
    payload: BulkDeleteLineItemsRequest,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    boq_stmt = select(BoQ).where(BoQ.id == boq_id, BoQ.contractor_organisation_id == auth.organisation_id)
    boq_res = await db.execute(boq_stmt)
    boq = boq_res.scalar_one_or_none()
    if not boq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "BOQ_NOT_FOUND", "message": "BoQ not found."})

    if not payload.line_item_ids:
        return {"deleted_count": 0}

    # Fetch items before delete to capture learning feedback
    items_stmt = select(LineItem).where(
        LineItem.id.in_(payload.line_item_ids),
        LineItem.boq_id == boq_id,
    )
    items_res = await db.execute(items_stmt)
    items_to_delete = items_res.scalars().all()

    delete_stmt = delete(LineItem).where(
        LineItem.id.in_(payload.line_item_ids),
        LineItem.boq_id == boq_id,
    )
    res = await db.execute(delete_stmt)
    deleted_count = res.rowcount

    await log_audit_event(
        db=db,
        organisation_id=auth.organisation_id,
        actor_user_id=auth.user_id,
        entity_type="boq",
        entity_id=boq_id,
        action="line_items.bulk_deleted",
        after_json={"deleted_count": deleted_count, "line_item_ids": payload.line_item_ids},
    )

    # Record parser removal feedback for each deleted candidate
    for item in items_to_delete:
        await log_audit_event(
            db=db,
            organisation_id=auth.organisation_id,
            actor_user_id=auth.user_id,
            entity_type="line_item",
            entity_id=item.id,
            action="parser.candidate_removed",
            before_json={
                "description": item.description,
                "unit": item.unit,
                "quantity": item.quantity,
                "category": item.category,
                "parsing_confidence": item.parsing_confidence,
            },
        )

    await db.commit()
    return {"deleted_count": deleted_count}


@router.get("/parser/feedback-summary", status_code=status.HTTP_200_OK)
async def get_parser_feedback_summary(
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    """Observability & learning data endpoint: Queries contractor parser correction and removal patterns."""
    stmt = (
        select(AuditEvent)
        .where(
            AuditEvent.organisation_id == auth.organisation_id,
            AuditEvent.action.in_(["parser.candidate_corrected", "parser.candidate_removed", "parser.candidate_restored"]),
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(100)
    )
    res = await db.execute(stmt)
    events = res.scalars().all()

    corrections_count = sum(1 for e in events if e.action == "parser.candidate_corrected")
    removals_count = sum(1 for e in events if e.action == "parser.candidate_removed")
    restorations_count = sum(1 for e in events if e.action == "parser.candidate_restored")

    # Aggregate corrected fields
    field_counts: dict[str, int] = {}
    for e in events:
        if e.action == "parser.candidate_corrected" and e.after_json:
            for field in e.after_json.get("fields_changed", []):
                field_counts[field] = field_counts.get(field, 0) + 1

    return {
        "total_feedback_events": len(events),
        "corrections_count": corrections_count,
        "removals_count": removals_count,
        "restorations_count": restorations_count,
        "top_corrected_fields": field_counts,
        "recent_feedback": [
            {
                "id": e.id,
                "action": e.action,
                "entity_id": e.entity_id,
                "details": e.after_json or e.before_json,
                "timestamp": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events[:20]
        ],
    }


