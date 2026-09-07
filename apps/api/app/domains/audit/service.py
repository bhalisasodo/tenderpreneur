from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.models import AuditEvent, utc_now


async def log_audit_event(
    db: AsyncSession,
    organisation_id: str,
    entity_type: str,
    entity_id: str,
    action: str,
    actor_user_id: Optional[str] = None,
    before_json: Optional[Dict[str, Any]] = None,
    after_json: Optional[Dict[str, Any]] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
) -> AuditEvent:
    """Creates and persists an immutable audit event record."""
    event = AuditEvent(
        organisation_id=organisation_id,
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        before_json=before_json,
        after_json=after_json,
        metadata_json=metadata_json,
        created_at=utc_now(),
    )
    db.add(event)
    await db.flush()
    return event
