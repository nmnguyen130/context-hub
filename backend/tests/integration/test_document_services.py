import io
import uuid
from unittest.mock import AsyncMock

import pytest

from app.core.context import RequestContext, UserRole
from app.core.exceptions import ServiceError
from app.core.pagination import CursorParams
from app.infrastructure.storage import StorageProvider
from app.modules.documents.models import Document, DocumentStatus, Workspace
from app.modules.documents.schemas import WorkspaceCreate, WorkspaceUpdate
from app.modules.documents.services.document_service import (
    DocumentService,
    WorkspaceService,
)
from tests.factories import make_tenant, make_user


@pytest.mark.integration
async def test_workspace_service_lifecycle(uow, make_tenant_uow):
    """Test workspace creation, duplicate slug prevention, listing, and updates."""
    tenant = make_tenant()
    uow.session.add(tenant)
    await uow.commit()

    # Step 1: Create Workspace
    async with make_tenant_uow(tenant.id) as tenant_uow:
        service = WorkspaceService(tenant_uow)
        data = WorkspaceCreate(name="Research Project", slug="research-project")
        workspace = await service.create(tenant.id, data)
        await tenant_uow.commit()

        assert workspace.name == "Research Project"
        assert workspace.slug == "research-project"
        assert workspace.tenant_id == tenant.id

        # Step 2: Prevent duplicate slug within same tenant
        with pytest.raises(ServiceError) as exc_info:
            await service.create(tenant.id, data)
        assert exc_info.value.status_code == 409

        # Step 3: List workspaces
        items, next_cursor, has_more = await service.list(
            tenant.id, CursorParams(limit=10)
        )
        assert len(items) == 1
        assert items[0].name == "Research Project"

        # Step 4: Update workspace
        updated = await service.update(
            workspace.id, WorkspaceUpdate(name="Research Project Updated")
        )
        await tenant_uow.commit()
        assert updated.name == "Research Project Updated"


@pytest.mark.integration
async def test_document_service_lifecycle(uow, make_tenant_uow):
    """Test document upload, validation, duplicate prevention, listing, and deletion."""
    tenant = make_tenant()
    uow.session.add(tenant)
    await uow.flush()
    user = make_user(tenant_id=tenant.id)
    uow.session.add(user)
    await uow.commit()

    context = RequestContext(
        request_id="test",
        trace_id="test",
        tenant_id=tenant.id,
        user_id=user.id,
        role=UserRole.MEMBER,
    )

    # Prepare storage mock
    mock_storage = AsyncMock(spec=StorageProvider)
    mock_storage.upload_file = AsyncMock()
    mock_storage.delete_file = AsyncMock()

    async with make_tenant_uow(tenant.id, user_id=user.id) as tenant_uow:
        # Create a workspace first
        ws_service = WorkspaceService(tenant_uow)
        workspace = await ws_service.create(
            tenant.id, WorkspaceCreate(name="My Workspace")
        )
        await tenant_uow.flush()

        doc_service = DocumentService(tenant_uow)
        content = b"Some simple plain text file content for testing"
        filename = "test.txt"

        # Step 1: Upload document
        document = await doc_service.upload(
            workspace_id=workspace.id,
            filename=filename,
            content=content,
            content_type="text/plain",
            storage=mock_storage,
            context=context,
        )
        await tenant_uow.commit()

        assert document.filename == "test.txt"
        assert document.status == DocumentStatus.PENDING
        assert document.tenant_id == tenant.id
        assert document.workspace_id == workspace.id
        mock_storage.upload_file.assert_called_once()

        # Step 2: Prevent upload of duplicate content hash
        with pytest.raises(ServiceError) as exc_info:
            await doc_service.upload(
                workspace_id=workspace.id,
                filename="another_name.txt",
                content=content,
                content_type="text/plain",
                storage=mock_storage,
                context=context,
            )
        assert exc_info.value.status_code == 409

        # Step 3: List documents
        docs, next_cursor, has_more = await doc_service.list_by_workspace(
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            params=CursorParams(limit=10),
        )
        assert len(docs) == 1
        assert docs[0].id == document.id

        # Step 4: Delete document
        await doc_service.delete(document.id, mock_storage)
        await tenant_uow.commit()
        mock_storage.delete_file.assert_called_with(document.storage_key)

        # Retrieve should raise 404
        with pytest.raises(ServiceError) as exc_info:
            await doc_service.get(document.id)
        assert exc_info.value.status_code == 404


@pytest.mark.integration
async def test_document_reingest_version_increment(uow, make_tenant_uow):
    """Test re-ingesting a document updates file metadata and increments version under Level B storage path."""
    tenant = make_tenant()
    uow.session.add(tenant)
    await uow.flush()

    user = make_user(tenant_id=tenant.id)
    workspace = Workspace(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Reingest Workspace",
        slug="reingest-ws",
    )
    uow.session.add_all([user, workspace])
    await uow.commit()

    doc = Document(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        filename="initial.txt",
        mime_type="text/plain",
        file_size=100,
        content_hash="initial_hash",
        storage_key=f"tenants/{tenant.id}/documents/initial.txt",
        status=DocumentStatus.ACTIVE,
        version=1,
    )
    uow.session.add(doc)
    await uow.commit()

    context = RequestContext(
        request_id="test",
        trace_id="test",
        tenant_id=tenant.id,
        user_id=user.id,
        role=UserRole.MEMBER,
    )
    mock_storage = AsyncMock(spec=StorageProvider)
    mock_storage.upload_file = AsyncMock()

    async with make_tenant_uow(tenant.id, user.id) as tenant_uow:
        service = DocumentService(uow=tenant_uow)
        reingested = await service.reingest(
            document_id=doc.id,
            filename="updated.txt",
            content=b"Updated content text for document",
            content_type="text/plain",
            storage=mock_storage,
            context=context,
        )
        await tenant_uow.commit()

        assert reingested.version == 2
        assert reingested.filename == "updated.txt"
        assert (
            reingested.storage_key
            == f"tenants/{tenant.id}/documents/{doc.id}/v2/updated.txt"
        )
        assert reingested.status == DocumentStatus.PENDING
