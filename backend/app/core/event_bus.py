# app/core/event_bus.py
import asyncio
import datetime
import random
import logging
from collections import defaultdict
from typing import Awaitable, Callable
from sqlalchemy import update
from app.core.events import DomainEvent, OutboxEvent, OutboxStatus

logger = logging.getLogger(__name__)

TransactionalHandler = Callable[[DomainEvent, "AsyncSession"], Awaitable[None]]
PostCommitHandler = Callable[[DomainEvent], Awaitable[None]]

MAX_ATTEMPTS = 8
BASE_BACKOFF_SECONDS = 2

def _next_backoff(attempts: int) -> datetime.timedelta:
    exp = min(BASE_BACKOFF_SECONDS * (2 ** attempts), 900)  # cap at 15 minutes
    jitter = random.uniform(0, exp * 0.2)  # avoid thundering-herd retries
    return datetime.timedelta(seconds=exp + jitter)

async def claim_and_dispatch(session_factory, outbox_id, event_bus: "EventBus") -> None:
    """The ONLY place post-commit handlers are ever invoked from.
    Atomic claim pattern via UPDATE ensures exactly-once/at-least-once safety."""
    async with session_factory() as session:
        result = await session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == outbox_id, OutboxEvent.status == OutboxStatus.PENDING.value)
            .values(status=OutboxStatus.PROCESSING.value)
            .returning(OutboxEvent)
        )
        row = result.scalar_one_or_none()
        await session.commit()
        if row is None:
            return  # already claimed/dispatched by someone else

        event = DomainEvent(event_type=row.event_type, payload=row.payload)
        try:
            for handler in event_bus._post_commit[event.event_type]:
                await handler(event)
        except Exception as exc:
            logger.exception(f"Error executing post-commit handlers for outbox {outbox_id}: {exc}")
            row.attempts += 1
            if row.attempts >= MAX_ATTEMPTS:
                row.status = OutboxStatus.DEAD_LETTER.value
                row.last_error = str(exc)
            else:
                row.status = OutboxStatus.PENDING.value
                row.next_retry_at = datetime.datetime.now(datetime.timezone.utc) + _next_backoff(row.attempts)
                row.last_error = str(exc)
            await session.merge(row)
            await session.commit()
            return

        row.status = OutboxStatus.DISPATCHED.value
        row.dispatched_at = datetime.datetime.now(datetime.timezone.utc)
        await session.merge(row)
        await session.commit()

class EventBus:
    def __init__(self) -> None:
        self._transactional: dict[str, list[TransactionalHandler]] = defaultdict(list)
        self._post_commit: dict[str, list[PostCommitHandler]] = defaultdict(list)

    def on_transactional(self, event_type: str, handler: TransactionalHandler) -> None:
        self._transactional[event_type].append(handler)

    def on_post_commit(self, event_type: str, handler: PostCommitHandler) -> None:
        self._post_commit[event_type].append(handler)

    async def dispatch_transactional(self, event: DomainEvent, session) -> None:
        # Wildcard support for event dispatching (e.g. audit logging matching all events)
        handlers = self._transactional[event.event_type] + self._transactional["*"]
        for handler in handlers:
            await handler(event, session)

    def dispatch_post_commit_nowait(self, session_factory, outbox_id) -> None:
        """Latency optimization: triggers immediate optimistic background dispatch."""
        asyncio.create_task(claim_and_dispatch(session_factory, outbox_id, self))

# Global singleton event bus
event_bus = EventBus()

# Register global transactional audit logger
from app.modules.audit.handler import write_audit_log
event_bus.on_transactional("*", write_audit_log)
