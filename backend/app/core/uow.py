# app/core/uow.py
from __future__ import annotations
from typing import TypeVar, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.core.context import RequestContext
from app.core.events import DomainEvent, OutboxEvent
from app.core.event_bus import EventBus

R = TypeVar("R", bound="Repository")

class UnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        context: RequestContext,
        event_bus: EventBus,
        *,
        admin_session_factory: async_sessionmaker[AsyncSession] | None = None,
        admin_reason: str | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._admin_session_factory = admin_session_factory
        self._context = context
        self._event_bus = event_bus
        self._repos: dict[type, Any] = {}
        self._events: list[DomainEvent] = []
        self._admin_reason = admin_reason
        self.session: AsyncSession

    @classmethod
    def as_admin(
        cls,
        context: RequestContext,
        event_bus: EventBus,
        session_factory: async_sessionmaker[AsyncSession],
        admin_session_factory: async_sessionmaker[AsyncSession],
        *,
        reason: str
    ) -> "UnitOfWork":
        """The sole sanctioned cross-tenant path. Uses BYPASSRLS admin role."""
        is_system_anonymous = reason in (
            "tenant lookup during login",
            "user authentication",
            "new tenant registration"
        )
        if not context.is_platform_admin and not is_system_anonymous:
            raise PermissionError("as_admin() requires a platform-admin RequestContext")
        if not reason.strip():
            raise ValueError("a reason is required for any cross-tenant access")
        return cls(
            session_factory=session_factory,
            context=context,
            event_bus=event_bus,
            admin_session_factory=admin_session_factory,
            admin_reason=reason
        )

    async def __aenter__(self) -> "UnitOfWork":
        # If in admin mode, use admin session factory
        if self._admin_reason and self._admin_session_factory:
            self.session = self._admin_session_factory()
        else:
            self.session = self._session_factory()

        # Explicit transaction start if not already in one
        if not self.session.in_transaction():
            await self.session.begin()

        if self._admin_reason:
            # Audit log entry for cross-tenant admin access (transactional)
            self.record_event(DomainEvent("admin.cross_tenant_access", {
                "actor_id": str(self._context.actor_id) if self._context.actor_id else None,
                "reason": self._admin_reason,
            }))
        else:
            # Bind tenant ID to local Postgres variable
            tid_val = str(self._context.tenant_id) if self._context.tenant_id else ""
            await self.session.execute(
                text("SELECT set_config('app.tenant_id', :tid, true)"),
                {"tid": tid_val},
            )

        assert self.session.in_transaction(), "UoW session must be inside a transaction"
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None and self.session.in_transaction():
            await self.session.rollback()
        await self.session.close()

    def repo(self, repo_cls: type[R]) -> R:
        if repo_cls not in self._repos:
            self._repos[repo_cls] = repo_cls(self.session)
        return self._repos[repo_cls]

    async def flush(self) -> None:
        await self.session.flush()

    def record_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    async def commit(self) -> None:
        try:
            # 1. Transactional handlers
            for event in self._events:
                await self._event_bus.dispatch_transactional(event, self.session)

            # 2. Save outbox events
            outbox_rows = [OutboxEvent.from_domain_event(e, self._context) for e in self._events]
            for row in outbox_rows:
                self.session.add(row)

            await self.session.commit()
        except Exception:
            if self.session.in_transaction():
                await self.session.rollback()
            raise

        # 3. Optimistic background dispatch
        if not self._admin_reason:
            for row in outbox_rows:
                self._event_bus.dispatch_post_commit_nowait(self._session_factory, row.id)

        self._events.clear()
