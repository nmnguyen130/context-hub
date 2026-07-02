# Import the Base ORM structure
from app.core.database import Base

# Import all models to register their tables on the metadata object
from app.modules.tenant.models import Tenant
from app.modules.auth.models import User
from app.modules.documents.models import Document, DocumentChunk, Workspace
from app.modules.audit.models import AuditLog

# Expose metadata for Alembic migrations
metadata = Base.metadata

__all__ = [
    "Base",
    "metadata",
    "Tenant",
    "User",
    "Document",
    "DocumentChunk",
    "Workspace",
    "AuditLog"
]
