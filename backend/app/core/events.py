import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Mapping

from sqlalchemy import JSON, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_type: str
    payload: Mapping[str, Any] = field(default_factory=dict)


class DomainEventsMixin:
    """Mixin for ORM entities to record and clear domain events."""

    _domain_events: list[DomainEvent]

    @property
    def domain_events(self) -> list[DomainEvent]:
        if not hasattr(self, "_domain_events"):
            self._domain_events = []
        return self._domain_events

    def record_event(self, event: DomainEvent) -> None:
        self.domain_events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        events = list(self.domain_events)
        self.domain_events.clear()
        return events


class OutboxStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class OutboxEvent(Base):
    __tablename__ = "event_outbox"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(index=True)

    event_type: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(OutboxStatus), default=OutboxStatus.PENDING, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
