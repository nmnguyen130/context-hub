from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog


from fastapi import Depends
from app.api.deps import get_db


class AuditService:
    """Centralized audit logging service."""

    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db

    async def log(
        self,
        tenant_id: UUID,
        user_id: UUID | None,
        action: str,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        ip_address: str | None = None,
        payload_diff: dict | None = None,
    ) -> None:
        """Records an audit event to the audit_logs table."""
        entry = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            payload_diff=payload_diff or {},
        )
        self.db.add(entry)
        # Note: the caller is responsible for committing the session
