import asyncio
import logging
import random
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.events import OutboxEvent, OutboxStatus
from app.worker.tasks import celery_app

logger = logging.getLogger(__name__)


MAX_RETRY = 5
BATCH_SIZE = 100


async def _dispatch_to_celery(
    event_type: str,
    payload: dict,
    context: dict,
) -> None:
    """Dispatches an outbox event to Celery without blocking async loop."""
    await asyncio.to_thread(
        celery_app.send_task,
        event_type,
        args=[payload],
        kwargs={"context": context},
    )


async def process_outbox_event(
    session_factory: async_sessionmaker[AsyncSession],
    event_id: UUID,
) -> None:
    """Claims and sends a single outbox event."""
    async with session_factory() as session:
        async with session.begin():
            stmt = (
                select(OutboxEvent)
                .where(
                    OutboxEvent.id == event_id,
                    OutboxEvent.status == OutboxStatus.PENDING,
                )
                .with_for_update(skip_locked=True)
            )

            event = await session.scalar(stmt)
            if event is None:
                return

            try:
                await _dispatch_to_celery(
                    event.event_type,
                    event.payload.get("data", {}),
                    {
                        "request_id": event.payload.get("request_id"),
                        "trace_id": event.payload.get("trace_id"),
                    },
                )
                event.status = OutboxStatus.SENT
                event.processed_at = datetime.now(UTC)

            except Exception as exc:
                logger.exception("Failed dispatching outbox event %s", event.id)
                event.retry_count += 1
                event.error_message = str(exc)[:500]

                if event.retry_count >= MAX_RETRY:
                    event.status = OutboxStatus.FAILED
                else:
                    delay = (2**event.retry_count) + random.random()
                    event.next_retry_at = datetime.now(UTC) + timedelta(seconds=delay)


async def run_outbox_relay(
    session_factory: async_sessionmaker[AsyncSession],
    interval: float = 1.0,
    concurrency: int = 20,
) -> None:
    """Continuously relays pending outbox events to Celery."""
    logger.info("Outbox relay started")
    semaphore = asyncio.Semaphore(concurrency)

    async def process(event_id: UUID) -> None:
        async with semaphore:
            try:
                await process_outbox_event(session_factory, event_id)
            except Exception:
                logger.exception("Outbox processing failed for %s", event_id)

    while True:
        try:
            async with session_factory() as session:
                now = datetime.now(UTC)

                stmt = (
                    select(OutboxEvent.id)
                    .where(
                        OutboxEvent.status == OutboxStatus.PENDING,
                        (
                            OutboxEvent.next_retry_at.is_(None)
                            | (OutboxEvent.next_retry_at <= now)
                        ),
                    )
                    .order_by(OutboxEvent.created_at)
                    .limit(BATCH_SIZE)
                )
                event_ids = (await session.scalars(stmt)).all()

            if event_ids:
                async with asyncio.TaskGroup() as group:
                    for event_id in event_ids:
                        group.create_task(process(event_id))

        except Exception:
            logger.exception("Outbox relay loop failed")

        await asyncio.sleep(interval)
