import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import TenantBaseModel


class AuditLog(TenantBaseModel):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., USER_LOGIN, DOCUMENT_DELETE
    resource_type: Mapped[str] = mapped_column(
        String(100), nullable=True
    )  # e.g., Document, Workspace
    resource_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    ip_address: Mapped[str] = mapped_column(
        String(45), nullable=True
    )  # supports IPv4 and IPv6
    payload_diff: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # diff payload {"before": ..., "after": ...}
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    def __repr__(self) -> str:
        return f"<AuditLog action={self.action} user={self.user_id} tenant={self.tenant_id}>"
