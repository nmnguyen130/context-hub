# tests/models.py
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.events import DomainEventsMixin


class MockTenant(Base):
    __tablename__ = "mock_tenants"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50))


class MockScopedModel(Base, DomainEventsMixin):
    __tablename__ = "mock_scoped_models"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mock_tenants.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(50))
