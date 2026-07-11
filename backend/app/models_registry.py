# Import the Base ORM structure
from app.core.database import Base
from app.modules.auth.models import Invitation, RefreshToken, User
from app.modules.documents.models import Document, DocumentChunk, Workspace
from app.modules.tenant.models import Tenant
from app.core.events import OutboxEvent
from app.modules.audit.models import AuditLog

# Import all models to register their tables on the metadata object
metadata = Base.metadata

__all__ = [
    "Base",
    "metadata",
    "Tenant",
    "User",
    "RefreshToken",
    "Invitation",
    "Document",
    "DocumentChunk",
    "Workspace",
    "OutboxEvent",
    "AuditLog",
]
