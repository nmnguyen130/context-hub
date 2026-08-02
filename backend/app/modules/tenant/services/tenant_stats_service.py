from uuid import UUID

from sqlalchemy import func, select

from app.core.uow import UnitOfWork
from app.modules.auth.models import User
from app.modules.documents.models import Document
from app.modules.tenant.schemas import TenantStatsResponse


class TenantStatsService:
    """Service to aggregate platform metrics and statistics for a specific tenant."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def get_stats(self, tenant_id: UUID) -> TenantStatsResponse:
        """Aggregates tenant resource usage statistics in a single database query."""
        user_count_subq = (
            select(func.count())
            .select_from(User)
            .where(User.tenant_id == tenant_id, User.is_active.is_(True))
            .scalar_subquery()
        )
        doc_count_subq = (
            select(func.count())
            .select_from(Document)
            .where(Document.tenant_id == tenant_id)
            .scalar_subquery()
        )
        storage_bytes_subq = (
            select(func.coalesce(func.sum(Document.file_size), 0))
            .where(Document.tenant_id == tenant_id)
            .scalar_subquery()
        )

        stmt = select(user_count_subq, doc_count_subq, storage_bytes_subq)
        res = await self.uow.session.execute(stmt)
        user_count, doc_count, storage_used = res.one()

        return TenantStatsResponse(
            user_count=user_count,
            document_count=doc_count,
            storage_used_bytes=storage_used,
        )
