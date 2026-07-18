import logging
from typing import Self

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.context import RequestContext
from app.core.events import DomainEventsMixin, OutboxEvent

logger = logging.getLogger(__name__)


class UnitOfWork:
    """Manages transactional boundaries and PostgreSQL Row-Level Security (RLS)."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        context: RequestContext,
        is_admin: bool = False,
    ) -> None:
        self._session_factory = session_factory
        self._context = context
        self._is_admin = is_admin
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self.session = self._session_factory()
        if not self.session.in_transaction():
            await self.session.begin()

        if self._is_admin:
            # Owner pool — superuser / owner bypasses RLS naturally, no GUC needed
            pass
        else:
            # Enforce Row-Level Security by binding active tenant ID
            if self._context.tenant_id is None:
                raise ValueError(
                    "Cannot open tenant-scoped UnitOfWork without tenant_id."
                )

            await self.session.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                {"tenant_id": str(self._context.tenant_id)},
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            if exc_type is not None:
                await self.rollback()
            elif self.session and self.session.in_transaction():
                # Only log warning if transaction has pending mutations that were not committed
                if self.session.new or self.session.dirty or self.session.deleted:
                    logger.warning(
                        "UnitOfWork exited with pending changes but without commit(); rolling back transaction."
                    )
                await self.rollback()
        finally:
            if self.session:
                await self.session.close()

    async def flush(self) -> None:
        """Flushes session modifications. Used to resolve database primary keys before commit."""
        if self.session is None:
            raise RuntimeError("UnitOfWork session is not active.")

        await self.session.flush()

    async def commit(self) -> None:
        """Collects domain events from modified session entities, writes outbox rows, and commits."""
        if self.session is None:
            raise RuntimeError("UnitOfWork session is not active.")

        # Scan only newly added, modified, or deleted entities.
        # Bypasses unmodified read-only entities in identity_map to boost query performance.
        tracked_objects = (
            set(self.session.new) | set(self.session.dirty) | set(self.session.deleted)
        )

        outbox_events: list[OutboxEvent] = []

        for obj in tracked_objects:
            if not isinstance(obj, DomainEventsMixin):
                continue

            tenant_id = getattr(obj, "tenant_id", None) or self._context.tenant_id

            for event in obj.pull_events():
                outbox_events.append(
                    OutboxEvent(
                        tenant_id=tenant_id,
                        event_type=event.event_type,
                        payload={
                            "data": event.payload,
                            "trace_id": self._context.trace_id,
                            "request_id": self._context.request_id,
                        },
                    )
                )

        if outbox_events:
            self.session.add_all(outbox_events)

        await self.session.commit()

    async def rollback(self) -> None:
        if self.session and self.session.in_transaction():
            await self.session.rollback()
