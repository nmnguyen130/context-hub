# app/modules/tenant/services/tenant_stats_service.py
from uuid import UUID
from fastapi import Depends
from sqlalchemy import func, select
from app.api.deps import get_uow
from app.core.uow import UnitOfWork
from app.modules.auth.models import User
from app.modules.documents.models import Document
from app.modules.tenant.schemas import TenantStatsResponse

class TenantStatsService:
    """Service to calculate tenant statistics."""

    def __init__(self, uow: UnitOfWork = Depends(get_uow)):
        self.uow = uow

    async def get_stats(self, tenant_id: UUID) -> TenantStatsResponse:
        """Retrieves tenant usage metrics."""
        users_sub = (
            select(func.count(User.id))
            .where(User.tenant_id == tenant_id)
            .scalar_subquery()
        )
        docs_sub = (
            select(func.count(Document.id))
            .where(Document.tenant_id == tenant_id)
            .scalar_subquery()
        )
        storage_sub = (
            select(func.coalesce(func.sum(Document.file_size), 0))
            .where(Document.tenant_id == tenant_id)
            .scalar_subquery()
        )

        stmt = select(users_sub, docs_sub, storage_sub)
        user_count, doc_count, storage_used = (await self.uow.session.execute(stmt)).tuple()

        return TenantStatsResponse(
            user_count=user_count or 0,
            document_count=doc_count or 0,
            storage_used_bytes=int(storage_used or 0),
        )
