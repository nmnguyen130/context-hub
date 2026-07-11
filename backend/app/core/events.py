# app/core/events.py
import uuid
import datetime
import enum
from dataclasses import dataclass, field
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base

@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_type: str
    payload: dict
    occurred_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

class OutboxStatus(str, enum.Enum):
    PENDING = "pending"        # waiting to be dispatched
    PROCESSING = "processing"  # claimed by a dispatcher, handler currently running
    DISPATCHED = "dispatched"  # terminal success
    DEAD_LETTER = "dead_letter"  # terminal failure — exhausted retries

class OutboxEvent(Base):
    __tablename__ = "event_outbox"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(255), index=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    correlation_id: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default=OutboxStatus.PENDING.value, index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    next_retry_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    dispatched_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @classmethod
    def from_domain_event(cls, event: DomainEvent, ctx) -> "OutboxEvent":
        return cls(
            event_type=event.event_type,
            payload=event.payload,
            tenant_id=ctx.tenant_id,
            correlation_id=ctx.correlation_id,
        )
