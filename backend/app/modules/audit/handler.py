# app/modules/audit/handler.py
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.context import current_context_or_none
from app.core.events import DomainEvent
from app.modules.audit.models import AuditLog

async def write_audit_log(event: DomainEvent, session: AsyncSession) -> None:
    """Transactional event handler to write audit logs from domain events."""
    ctx = current_context_or_none()
    if not ctx:
        return

    # Skip recording audit log events as audit logs to prevent recursive loop
    if event.event_type == "audit.logged":
        return

    # Extract resource details if present in the payload
    resource_id_str = event.payload.get("document_id") or event.payload.get("workspace_id") or event.payload.get("user_id")
    resource_id = None
    if resource_id_str:
        try:
            resource_id = uuid.UUID(str(resource_id_str))
        except ValueError:
            pass

    resource_type = event.payload.get("resource_type")
    if not resource_type:
        if "document" in event.event_type:
            resource_type = "document"
        elif "workspace" in event.event_type:
            resource_type = "workspace"
        elif "user" in event.event_type:
            resource_type = "user"
        elif "tenant" in event.event_type:
            resource_type = "tenant"

    audit = AuditLog(
        tenant_id=ctx.tenant_id or event.payload.get("tenant_id"),
        user_id=ctx.actor_id or event.payload.get("user_id"),
        action=event.event_type.upper(),
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ctx.ip_address,
        payload_diff=event.payload.get("payload_diff", event.payload),
    )
    session.add(audit)
