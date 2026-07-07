from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.modules.auth.models import User
from app.modules.documents.models import Document
from app.modules.tenant.schemas import TenantStatsResponse


class TenantStatsService:
    """Service to calculate tenant statistics."""

    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db

    async def get_stats(self, tenant_id: UUID) -> TenantStatsResponse:
        """Retrieves tenant usage metrics."""
        users_sub = (
            select(func.count(User.id))
            .where(User.tenant_id == tenant_id)
            .execution_options(skip_tenant_filter=True)
            .scalar_subquery()
        )
        docs_sub = (
            select(func.count(Document.id))
            .where(Document.tenant_id == tenant_id)
            .execution_options(skip_tenant_filter=True)
            .scalar_subquery()
        )
        storage_sub = (
            select(func.coalesce(func.sum(Document.file_size), 0))
            .where(Document.tenant_id == tenant_id)
            .execution_options(skip_tenant_filter=True)
            .scalar_subquery()
        )

        stmt = select(users_sub, docs_sub, storage_sub)
        user_count, doc_count, storage_used = (await self.db.execute(stmt)).tuple()

        return TenantStatsResponse(
            user_count=user_count or 0,
            document_count=doc_count or 0,
            storage_used_bytes=int(storage_used or 0),
        )
