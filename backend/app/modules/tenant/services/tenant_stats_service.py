from uuid import UUID

from app.core.uow import UnitOfWork
from app.modules.tenant.schemas import TenantStatsResponse


class TenantStatsService:
    """Service to aggregate platform metrics and statistics for a specific tenant."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def get_stats(self, tenant_id: UUID) -> TenantStatsResponse:
        """Aggregates tenant resources usage metadata (mocked until schemas are built)."""
        # TODO: Integrate aggregate queries once User and Document modules are implemented:
        # e.g.,
        # user_count = await self.uow.session.scalar(select(func.count(User.id)).where(User.tenant_id == tenant_id))
        # docs_count = await self.uow.session.scalar(select(func.count(Document.id)).where(Document.tenant_id == tenant_id))
        # storage = await self.uow.session.scalar(select(func.sum(Document.file_size_bytes)).where(Document.tenant_id == tenant_id))
        return TenantStatsResponse(
            user_count=1,
            document_count=0,
            storage_used_bytes=0,
        )
