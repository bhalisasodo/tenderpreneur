import io
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.models import AuditEvent, BoQ, LineItem, Quote, QuoteRequest, User, utc_now
from app.core.security import AuthContext, get_current_auth, require_contractor
from app.domains.audit.service import log_audit_event
from app.integrations.exports import get_export_renderer
from app.integrations.storage import get_storage_provider
from app.schemas.exports import ExportCreateRequest, ExportResponse

router = APIRouter(tags=["Exports"])


@router.post("/boqs/{boq_id}/exports", response_model=ExportResponse)
async def generate_boq_export(
    boq_id: str,
    payload: ExportCreateRequest,
    auth: AuthContext = Depends(require_contractor),
    db: AsyncSession = Depends(get_db),
):
    # Fetch BoQ with line items and selected quotes
    stmt = (
        select(BoQ)
        .options(
            selectinload(BoQ.line_items)
            .selectinload(LineItem.quote_requests)
            .selectinload(QuoteRequest.quotes)
            .selectinload(Quote.supplier_organisation)
        )
        .where(BoQ.id == boq_id, BoQ.contractor_organisation_id == auth.organisation_id)
    )
    res = await db.execute(stmt)
    boq = res.scalar_one_or_none()
    if not boq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BOQ_NOT_FOUND", "message": "BoQ not found."},
        )

    # Fetch audit events
    audit_stmt = (
        select(AuditEvent, User.name.label("actor_name"))
        .outerjoin(User, AuditEvent.actor_user_id == User.id)
        .where(AuditEvent.organisation_id == auth.organisation_id)
        .order_by(AuditEvent.created_at.desc())
    )
    audit_res = await db.execute(audit_stmt)
    audit_rows = audit_res.all()

    audit_events_data = [
        {
            "created_at": event.created_at.strftime("%Y-%m-%d %H:%M:%S") if event.created_at else "",
            "entity_type": event.entity_type,
            "action": event.action,
            "actor_name": actor_name,
            "actor_user_id": event.actor_user_id,
            "before_json": str(event.before_json) if event.before_json else "",
            "after_json": str(event.after_json) if event.after_json else "",
            "metadata_json": str(event.metadata_json) if event.metadata_json else "",
        }
        for event, actor_name in audit_rows
    ]

    # Prepare line items data
    line_items_data = []
    for li in boq.line_items:
        quote_ref = None
        override_reason = None

        if li.quote_requests:
            for qr in li.quote_requests:
                for q in qr.quotes:
                    if q.is_selected:
                        sup_name = q.supplier_organisation.legal_name if q.supplier_organisation else "Supplier"
                        quote_ref = f"Quote #{q.id[:8]} by {sup_name}"
                        break

        # Check if manual override in audit
        for ae in audit_events_data:
            if ae.get("action") == "line_item.price_overridden" and ae.get("entity_id") == li.id:
                override_reason = f"Manual override: {ae.get('metadata_json')}"
                break

        line_items_data.append(
            {
                "id": li.id,
                "source_row_reference": li.source_row_reference,
                "description": li.description,
                "category": li.category,
                "unit": li.unit,
                "quantity": li.quantity,
                "final_price_minor": li.final_price_minor,
                "pricing_status": li.pricing_status,
                "quote_reference": quote_ref,
                "override_reason": override_reason,
            }
        )

    boq_data = {
        "id": boq.id,
        "title": boq.title,
        "tender_reference": boq.tender_reference,
        "region": boq.region,
        "status": boq.status,
    }

    renderer = get_export_renderer()
    storage = get_storage_provider()

    export_id = str(uuid.uuid4())
    fmt = payload.format.lower().strip()
    if fmt not in ["xlsx", "pdf"]:
        fmt = "xlsx"

    if fmt == "xlsx":
        file_bytes = await renderer.render_excel(boq_data, line_items_data, audit_events_data)
        filename = f"Tenderpreneur_BoQ_{boq.tender_reference or boq.id[:8]}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        file_bytes = await renderer.render_pdf(boq_data, line_items_data, audit_events_data)
        filename = f"Tenderpreneur_BoQ_{boq.tender_reference or boq.id[:8]}_{datetime.now().strftime('%Y%m%d')}.pdf"
        mime = "application/pdf"

    storage_key = f"exports/{auth.organisation_id}/{boq.id}/{export_id}_{filename}"
    await storage.upload_file(storage_key, file_bytes, mime)

    await log_audit_event(
        db=db,
        organisation_id=auth.organisation_id,
        actor_user_id=auth.user_id,
        entity_type="boq",
        entity_id=boq.id,
        action="export.generated",
        after_json={"format": fmt, "filename": filename, "size_bytes": len(file_bytes), "export_id": export_id},
    )
    await db.commit()

    return ExportResponse(
        export_id=export_id,
        boq_id=boq.id,
        format=fmt,
        filename=filename,
        status="completed",
        download_url=f"/api/v1/boqs/{boq.id}/exports/{export_id}/download",
        generated_at=utc_now(),
    )


@router.get("/boqs/{boq_id}/exports/{export_id}/download")
async def download_boq_export(
    boq_id: str,
    export_id: str,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_contractor),
):
    storage = get_storage_provider()
    # Search in storage for key matching export_id
    # Format: exports/{org_id}/{boq_id}/{export_id}_{filename}
    export_dir = f"exports/{auth.organisation_id}/{boq_id}"
    
    # We can reconstruct or read the storage file
    local_path = storage.get_local_path(export_dir)
    import os
    if os.path.exists(local_path):
        for fname in os.listdir(local_path):
            if fname.startswith(export_id):
                full_key = f"{export_dir}/{fname}"
                file_bytes = await storage.get_file(full_key)
                media_type = "application/pdf" if fname.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                clean_filename = fname.split("_", 1)[1] if "_" in fname else fname
                return Response(
                    content=file_bytes,
                    media_type=media_type,
                    headers={"Content-Disposition": f'attachment; filename="{clean_filename}"'},
                )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "EXPORT_NOT_FOUND", "message": "Export file not found or expired."},
    )
