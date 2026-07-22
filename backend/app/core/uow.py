import logging
from typing import Self

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.context import RequestContext, bind_context
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
        # Bind request context so services within this transaction scope can access try_current_context()
        self._context_manager = bind_context(self._context)
        self._context_manager.__enter__()

        self.session = self._session_factory()

        if not self._is_admin:
            # Enforce Row-Level Security by binding active tenant ID on transaction begin.
            # This is registered as a session event to handle automatic re-begins (e.g. after commits/rollbacks).
            if self._context.tenant_id is None:
                raise ValueError(
                    "Cannot open tenant-scoped UnitOfWork without tenant_id."
                )

            @event.listens_for(self.session.sync_session, "after_begin")
            def set_tenant_id(session, transaction, connection):
                connection.execute(
                    text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                    {"tenant_id": str(self._context.tenant_id)},
                )

        if not self.session.in_transaction():
            await self.session.begin()

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
            if hasattr(self, "_context_manager"):
                self._context_manager.__exit__(exc_type, exc_val, exc_tb)
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
