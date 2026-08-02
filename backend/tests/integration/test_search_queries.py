import uuid

import pytest
from sqlalchemy import select

from app.modules.documents.models import (
    Document,
    DocumentChunk,
    DocumentStatus,
    Workspace,
)
from app.modules.documents.queries import (
    dense_search,
    sparse_search,
    update_search_vectors,
)
from tests.factories import make_tenant, make_user


@pytest.mark.integration
async def test_dense_search_query(uow, make_tenant_uow):
    """Test pgvector dense similarity search filtering and workspace scoping."""
    tenant = make_tenant()
    uow.session.add(tenant)
    await uow.flush()

    # Create workspace, document, and document chunks
    workspace = Workspace(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Vector Workspace",
        slug="vector-ws",
    )
    doc = Document(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        filename="test.txt",
        mime_type="text/plain",
        file_size=100,
        content_hash="abc",
        storage_key="test-key",
        status=DocumentStatus.ACTIVE,
    )
    # Define simple mock embeddings: dimension matches configuration (e.g. 768)
    from app.core.config import settings

    dim = settings.RAG_EMBEDDING_DIMENSION

    # Chunk A: completely matching vector
    emb_a = [1.0] + [0.0] * (dim - 1)
    chunk_a = DocumentChunk(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        document_id=doc.id,
        workspace_id=workspace.id,
        chunk_index=0,
        content="Matching chunk content",
        token_count=10,
        embedding=emb_a,
        is_active=True,
    )

    # Chunk B: completely orthogonal vector
    emb_b = [0.0, 1.0] + [0.0] * (dim - 2)
    chunk_b = DocumentChunk(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        document_id=doc.id,
        workspace_id=workspace.id,
        chunk_index=1,
        content="Other chunk content",
        token_count=10,
        embedding=emb_b,
        is_active=True,
    )

    uow.session.add_all([workspace, doc, chunk_a, chunk_b])
    await uow.commit()

    async with make_tenant_uow(tenant.id) as tenant_uow:
        # Search query vector
        query_vector = [1.0] + [0.0] * (dim - 1)
        results = await dense_search(
            session=tenant_uow.session,
            embedding=query_vector,
            workspace_ids=[workspace.id],
            limit=5,
        )

        assert len(results) == 2
        # Chunk A should have higher cosine similarity score than Chunk B
        assert results[0].id == chunk_a.id
        assert results[0].cosine_score > results[1].cosine_score


@pytest.mark.integration
async def test_sparse_search_query(uow, make_tenant_uow):
    """Test full-text search indexing, vector updates, and matching logic."""
    tenant = make_tenant()
    uow.session.add(tenant)
    await uow.flush()

    workspace = Workspace(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Text Workspace",
        slug="text-ws",
    )
    doc = Document(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        filename="test.txt",
        mime_type="text/plain",
        file_size=100,
        content_hash="xyz",
        storage_key="test-key",
        status=DocumentStatus.ACTIVE,
    )
    chunk_a = DocumentChunk(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        document_id=doc.id,
        workspace_id=workspace.id,
        chunk_index=0,
        content="The quick brown fox jumps over the lazy dog",
        token_count=10,
        is_active=True,
    )
    chunk_b = DocumentChunk(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        document_id=doc.id,
        workspace_id=workspace.id,
        chunk_index=1,
        content="Python is an interpreted programming language",
        token_count=10,
        is_active=True,
    )

    uow.session.add_all([workspace, doc, chunk_a, chunk_b])
    await uow.commit()

    async with make_tenant_uow(tenant.id) as tenant_uow:
        # Before update_search_vectors, sparse search matches nothing (search_vector is NULL)
        empty_results = await sparse_search(
            session=tenant_uow.session,
            query="fox",
            workspace_ids=[workspace.id],
        )
        assert len(empty_results) == 0

        # Update search vectors
        await update_search_vectors(tenant_uow.session, [chunk_a.id, chunk_b.id])
        await tenant_uow.commit()

        # Search for "fox" (should match Chunk A only)
        results_fox = await sparse_search(
            session=tenant_uow.session,
            query="fox",
            workspace_ids=[workspace.id],
        )
        assert len(results_fox) == 1
        assert results_fox[0].id == chunk_a.id

        # Search for "Python" (should match Chunk B only)
        results_python = await sparse_search(
            session=tenant_uow.session,
            query="Python",
            workspace_ids=[workspace.id],
        )
        assert len(results_python) == 1
        assert results_python[0].id == chunk_b.id


@pytest.mark.integration
async def test_document_scope_filtering(uow, make_tenant_uow):
    """Test dense_search and sparse_search filtering by document_ids."""
    tenant = make_tenant()
    uow.session.add(tenant)
    await uow.flush()

    workspace = Workspace(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Scope Workspace",
        slug="scope-ws",
    )
    doc1 = Document(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        filename="doc1.txt",
        mime_type="text/plain",
        file_size=100,
        content_hash="hash1",
        storage_key="key1",
        status=DocumentStatus.ACTIVE,
    )
    doc2 = Document(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        filename="doc2.txt",
        mime_type="text/plain",
        file_size=100,
        content_hash="hash2",
        storage_key="key2",
        status=DocumentStatus.ACTIVE,
    )

    from app.core.config import settings

    dim = settings.RAG_EMBEDDING_DIMENSION
    vec = [1.0] + [0.0] * (dim - 1)

    chunk_doc1 = DocumentChunk(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        document_id=doc1.id,
        workspace_id=workspace.id,
        chunk_index=0,
        content="Alpha content in doc1",
        token_count=5,
        embedding=vec,
        is_active=True,
    )
    chunk_doc2 = DocumentChunk(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        document_id=doc2.id,
        workspace_id=workspace.id,
        chunk_index=0,
        content="Alpha content in doc2",
        token_count=5,
        embedding=vec,
        is_active=True,
    )

    uow.session.add_all([workspace, doc1, doc2, chunk_doc1, chunk_doc2])
    await uow.commit()

    async with make_tenant_uow(tenant.id) as tenant_uow:
        await update_search_vectors(tenant_uow.session, [chunk_doc1.id, chunk_doc2.id])
        await tenant_uow.commit()

        # Search without document filter returns both chunks
        all_dense = await dense_search(
            session=tenant_uow.session,
            embedding=vec,
            workspace_ids=[workspace.id],
        )
        assert len(all_dense) == 2

        # Search scoped ONLY to doc1 returns only chunk_doc1
        scoped_dense = await dense_search(
            session=tenant_uow.session,
            embedding=vec,
            workspace_ids=[workspace.id],
            document_ids=[doc1.id],
        )
        assert len(scoped_dense) == 1
        assert scoped_dense[0].id == chunk_doc1.id

        # Sparse search scoped ONLY to doc2 returns only chunk_doc2
        scoped_sparse = await sparse_search(
            session=tenant_uow.session,
            query="Alpha",
            workspace_ids=[workspace.id],
            document_ids=[doc2.id],
        )
        assert len(scoped_sparse) == 1
        assert scoped_sparse[0].id == chunk_doc2.id
