import asyncio

from app.core.database import async_session
from app.infrastructure.outbox import relay_loop


async def main() -> None:
    await relay_loop(
        session_factory=async_session,
    )


if __name__ == "__main__":
    asyncio.run(main())
