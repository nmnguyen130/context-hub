# app/worker/outbox_relay.py
import asyncio
import datetime
import logging
from sqlalchemy import select
from app.core.events import OutboxEvent, OutboxStatus
from app.core.event_bus import EventBus, claim_and_dispatch

logger = logging.getLogger(__name__)

async def relay_loop(session_factory, event_bus: EventBus, poll_interval: float = 0.5):
    """Outbox relay poller that claims and dispatches pending events from the outbox table."""
    logger.info("Starting event outbox relay loop...")
    while True:
        try:
            async with session_factory() as session:
                now = datetime.datetime.now(datetime.timezone.utc)
                stmt = (
                    select(OutboxEvent.id)
                    .where(
                        OutboxEvent.status == OutboxStatus.PENDING.value,
                        (OutboxEvent.next_retry_at.is_(None)) | (OutboxEvent.next_retry_at <= now),
                    )
                    .order_by(OutboxEvent.id)
                    .limit(100)
                )
                result = await session.execute(stmt)
                outbox_ids = result.scalars().all()

            for outbox_id in outbox_ids:
                try:
                    await claim_and_dispatch(session_factory, outbox_id, event_bus)
                except Exception as dispatch_err:
                    logger.error(f"Relay failed to dispatch event {outbox_id}: {dispatch_err}")

        except Exception as loop_err:
            logger.error(f"Error in outbox relay loop: {loop_err}")

        await asyncio.sleep(poll_interval)
