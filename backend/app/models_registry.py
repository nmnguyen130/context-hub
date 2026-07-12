from app.core.database import Base
from app.core.events import OutboxEvent

metadata = Base.metadata

__all__ = [
    "Base",
    "OutboxEvent",
    "metadata",
]
