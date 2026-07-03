import uuid
from unittest.mock import patch

import pymupdf
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.core.storage as storage_module
from app.core.security import create_access_token
from app.core.storage import StorageProvider
from app.modules.auth.models import User
from app.modules.documents.models import Document, Workspace
from app.modules.documents.services import process_document_ingestion
from app.modules.tenant.models import Tenant
from app.worker.tasks import parse_document_task


# 1. Implementation of Memory Storage Provider for testing S3 key uploads
class MemoryStorageProvider(StorageProvider):
    def __init__(self):
        self.storage = {}

    async def upload_file(self, file_obj, key: str) -> None:
        self.storage[key] = file_obj.read()

    async def download_file(self, key: str) -> bytes:
        if key not in self.storage:
            raise RuntimeError(f"Key not found in memory store: {key}")
        return self.storage[key]

    async def delete_file(self, key: str) -> None:
        if key in self.storage:
            del self.storage[key]


# Instantiate and patch S3StorageProvider globally in the storage module
mem_storage = MemoryStorageProvider()
storage_module._storage_client = mem_storage


@pytest.mark.asyncio
async def test_document_ingestion_lifecycle(client: AsyncClient, db: AsyncSession):
    # Setup test Tenant A & Admin User A
    tenant_a = Tenant(name="Tenant A", plan_tier="ENTERPRISE")
    db.add(tenant_a)
    await db.commit()
    await db.refresh(tenant_a)
    tenant_a_id = tenant_a.id

    user_a = User(
        email="user_a@tenant-a.com",
        password_hash="hashedpassword",
        first_name="User",
        last_name="A",
        role="ADMIN",
        tenant_id=tenant_a_id,
    )
    db.add(user_a)
    await db.commit()
    await db.refresh(user_a)

    # Setup Workspace for Tenant A
    workspace_a = Workspace(name="Workspace A", tenant_id=tenant_a_id)
    db.add(workspace_a)
    await db.commit()
    await db.refresh(workspace_a)
    workspace_a_id = workspace_a.id

    # Generate Auth Header for Tenant A
    token_a = create_access_token(user_a.id, tenant_a_id, user_a.role)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Setup Tenant B (for isolation testing)
    tenant_b = Tenant(name="Tenant B", plan_tier="FREE")
    db.add(tenant_b)
    await db.commit()
    await db.refresh(tenant_b)
    tenant_b_id = tenant_b.id

    workspace_b = Workspace(name="Workspace B", tenant_id=tenant_b_id)
    db.add(workspace_b)
    await db.commit()
    await db.refresh(workspace_b)
    workspace_b_id = workspace_b.id

    # Generate Auth Header for Tenant B
    user_b = User(
        email="user_b@tenant-b.com",
        password_hash="hashedpassword",
        role="ADMIN",
        tenant_id=tenant_b_id,
    )
    db.add(user_b)
    await db.commit()
    await db.refresh(user_b)
    token_b = create_access_token(user_b.id, tenant_b_id, user_b.role)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Clear storage dict
    mem_storage.storage.clear()

    # --- Flow 1: Upload a TXT file (Tenant A to Workspace A) ---
    txt_content = b"This is a sample document content to test txt parser."
    files = {"file": ("sample.txt", txt_content, "text/plain")}

    with patch("app.worker.tasks.parse_document_task.delay") as mock_delay:
        response = await client.post(
            f"/api/v1/documents/workspaces/{workspace_a.id}",
            files=files,
            headers=headers_a,
        )
        assert response.status_code == 202
        res_data = response.json()
        assert res_data["status"] == "PENDING"
        assert res_data["name"] == "sample.txt"
        assert res_data["file_type"] == "txt"
        doc_id = res_data["id"]

        # Verify raw file uploaded to memory storage
        raw_key = res_data["object_store_key"]
        assert raw_key == f"{str(tenant_a_id)}/{str(workspace_a_id)}/{doc_id}/raw.txt"
        assert mem_storage.storage[raw_key] == txt_content

        # Run Celery parsing task synchronously
        mock_delay.assert_called_once_with(doc_id)
        with patch(
            "app.core.clients.GeminiEmbeddingClient.get_embeddings_batch",
            side_effect=lambda texts: [[0.1] * 768 for _ in texts],
        ):
            await process_document_ingestion(parse_document_task, doc_id)

    # Verify document status updated to ACTIVE in DB
    db.expire_all()
    stmt = select(Document).where(Document.id == uuid.UUID(doc_id))
    doc = (await db.execute(stmt)).scalar_one()
    assert doc.status == "ACTIVE"
    assert doc.checksum is not None

    # Verify parsed text is uploaded to S3 next to raw file
    extracted_key = f"{str(tenant_a_id)}/{str(workspace_a_id)}/{doc_id}/extracted.txt"
    assert mem_storage.storage[extracted_key] == txt_content

    # --- Flow 2: Upload a PDF file (Tenant A to Workspace A) ---
    # Create valid PDF in memory using PyMuPDF
    pdf_doc = pymupdf.open()
    page = pdf_doc.new_page()
    page.insert_text((50, 50), "Hello from PyMuPDF PDF parser test!")
    pdf_bytes = pdf_doc.write()
    pdf_doc.close()

    files = {"file": ("test.pdf", pdf_bytes, "application/pdf")}
    with patch("app.worker.tasks.parse_document_task.delay") as mock_delay:
        response = await client.post(
            f"/api/v1/documents/workspaces/{workspace_a_id}",
            files=files,
            headers=headers_a,
        )
        assert response.status_code == 202
        res_data = response.json()
        pdf_doc_id = res_data["id"]

        # Run Celery parsing task synchronously
        with patch(
            "app.core.clients.GeminiEmbeddingClient.get_embeddings_batch",
            side_effect=lambda texts: [[0.1] * 768 for _ in texts],
        ):
            await process_document_ingestion(parse_document_task, pdf_doc_id)

    db.expire_all()
    stmt = select(Document).where(Document.id == uuid.UUID(pdf_doc_id))
    doc = (await db.execute(stmt)).scalar_one()
    assert doc.status == "ACTIVE"

    # Download parsed text and verify it contains our PDF text
    pdf_extracted_key = (
        f"{str(tenant_a_id)}/{str(workspace_a_id)}/{pdf_doc_id}/extracted.txt"
    )
    extracted_text = mem_storage.storage[pdf_extracted_key].decode("utf-8")
    assert "Hello from PyMuPDF" in extracted_text

    # --- Flow 3: Workspace Isolation Violation ---
    # Tenant A attempts to upload to Tenant B's Workspace B
    response = await client.post(
        f"/api/v1/documents/workspaces/{workspace_b_id}",
        files={"file": ("unauthorized.txt", b"hack", "text/plain")},
        headers=headers_a,
    )
    assert response.status_code == 404

    # --- Flow 4: GET Document Details and Isolation ---
    # Tenant A retrieves own document
    response = await client.get(f"/api/v1/documents/{doc_id}", headers=headers_a)
    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"

    # Tenant B attempts to retrieve Tenant A's document (should fail with 404)
    response = await client.get(f"/api/v1/documents/{doc_id}", headers=headers_b)
    assert response.status_code == 404

    # --- Flow 5: PDF Ingestion Error Handling (Corrupt file) ---
    files = {
        "file": ("corrupt.pdf", b"corrupt-bytes-not-a-valid-pdf", "application/pdf")
    }
    with patch("app.worker.tasks.parse_document_task.delay") as mock_delay:
        response = await client.post(
            f"/api/v1/documents/workspaces/{workspace_a_id}",
            files=files,
            headers=headers_a,
        )
        assert response.status_code == 202
        corrupt_doc_id = response.json()["id"]

        # Run worker (it should raise Exception during parsing and transition doc to ERROR)
        with pytest.raises(Exception):
            with patch(
                "app.core.clients.GeminiEmbeddingClient.get_embeddings_batch",
                side_effect=lambda texts: [[0.1] * 768 for _ in texts],
            ):
                await process_document_ingestion(parse_document_task, corrupt_doc_id)

    db.expire_all()
    stmt = select(Document).where(Document.id == uuid.UUID(corrupt_doc_id))
    doc = (await db.execute(stmt)).scalar_one()
    assert doc.status == "ERROR"
    assert doc.error_message is not None
    assert (
        "cannot find startxref" in doc.error_message.lower()
        or "parsing failed" in doc.error_message.lower()
    )

    # --- Flow 6: DELETE Document and S3 Assets ---
    # Tenant B tries to delete Tenant A's document (fails 404)
    response = await client.delete(f"/api/v1/documents/{doc_id}", headers=headers_b)
    assert response.status_code == 404

    # Tenant A deletes own document (success 204)
    response = await client.delete(f"/api/v1/documents/{doc_id}", headers=headers_a)
    assert response.status_code == 204

    # Verify deleted from DB
    db.expire_all()
    stmt = select(Document).where(Document.id == uuid.UUID(doc_id))
    result = await db.execute(stmt)
    assert result.scalar_one_or_none() is None

    # Verify S3 assets deleted
    raw_key = f"{str(tenant_a_id)}/{str(workspace_a_id)}/{doc_id}/raw.txt"
    extracted_key = f"{str(tenant_a_id)}/{str(workspace_a_id)}/{doc_id}/extracted.txt"
    assert raw_key not in mem_storage.storage
    assert extracted_key not in mem_storage.storage


@pytest.mark.asyncio
async def test_document_upload_size_limit(client: AsyncClient, db: AsyncSession):
    # Setup Tenant and User
    tenant = Tenant(name="Size Limit Tenant")
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    user = User(
        email="size_test@test.com",
        password_hash="...",
        first_name="Size",
        last_name="Test",
        role="ADMIN",
        tenant_id=tenant.id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    workspace = Workspace(name="Size Space", tenant_id=tenant.id)
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)

    token = create_access_token(user.id, tenant.id, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    # Construct payload exceeding default 20MB limit (25MB)
    large_content = b"x" * (25 * 1024 * 1024)
    files = {"file": ("massive.pdf", large_content, "application/pdf")}

    response = await client.post(
        f"/api/v1/documents/workspaces/{workspace.id}",
        files=files,
        headers=headers,
    )
    assert response.status_code == 400
    assert "exceeds the limit" in response.json()["detail"]
