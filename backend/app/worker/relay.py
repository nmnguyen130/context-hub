import asyncio

from app.core.database import async_session
from app.infrastructure.outbox import run_outbox_relay


async def main() -> None:
    await run_outbox_relay(
        session_factory=async_session,
    )


if __name__ == "__main__":
    asyncio.run(main())
