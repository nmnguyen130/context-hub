import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.modules.auth.models import User
from app.modules.documents.models import Workspace
from app.modules.tenant.models import Tenant


@pytest.mark.asyncio
async def test_chat_stream_flow(client: AsyncClient, db: AsyncSession):
    # 1. Setup Tenants and Workspaces
    tenant_a = Tenant(name="Tenant A")
    tenant_b = Tenant(name="Tenant B")
    db.add_all([tenant_a, tenant_b])
    await db.commit()
    await db.refresh(tenant_a)
    await db.refresh(tenant_b)

    workspace_a = Workspace(name="Workspace A", tenant_id=tenant_a.id)
    workspace_b = Workspace(name="Workspace B", tenant_id=tenant_b.id)
    db.add_all([workspace_a, workspace_b])
    await db.commit()
    await db.refresh(workspace_a)
    await db.refresh(workspace_b)

    user_a = User(
        email="user_a@test.com",
        password_hash="...",
        first_name="User",
        last_name="A",
        role="ADMIN",
        tenant_id=tenant_a.id,
    )
    db.add(user_a)
    await db.commit()
    await db.refresh(user_a)

    token_a = create_access_token(user_a.id, tenant_a.id, user_a.role)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # --- Flow 1: Tenant A tries to query Workspace B (Logical multi-tenancy check) ---
    req_payload = {
        "query": "How is multi-tenancy implemented?",
        "workspace_id": str(workspace_b.id),
    }
    response = await client.post(
        "/api/v1/chat/stream", json=req_payload, headers=headers_a
    )
    assert response.status_code == 404

    # --- Flow 2: Cache Hit Check ---
    req_payload["workspace_id"] = str(workspace_a.id)

    with patch(
        "app.core.clients.GeminiEmbeddingClient.get_embedding",
        return_value=[0.1] * 768,
    ):
        with patch(
            "app.modules.documents.semantic_cache.SemanticCacheManager.get",
            return_value="Cached: Multi-tenancy is logical.",
        ) as mock_get:
            response = await client.post(
                "/api/v1/chat/stream", json=req_payload, headers=headers_a
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            # Parse SSE events
            lines = response.text.split("\n\n")
            events = [line.strip() for line in lines if line.strip()]

            assert len(events) >= 2
            event_1 = json.loads(events[0].replace("data: ", ""))
            assert event_1["type"] == "text"
            assert event_1["content"] == "Cached: Multi-tenancy is logical."

            event_2 = json.loads(events[1].replace("data: ", ""))
            assert event_2["type"] == "done"
            mock_get.assert_called_once()

    # --- Flow 3: Cache Miss and Grounded Chat Stream ---
    chunk_id = str(uuid.uuid4())
    mock_chunks = [
        {
            "id": chunk_id,
            "content": "Fact: ContextHub uses tenant_id column partitioning.",
            "metadata": {"document_name": "arch.md", "page_number": 3},
        }
    ]

    async def mock_stream_chat(*args, **kwargs):
        yield "According to source, ContextHub uses "
        yield f"tenant_id column partitioning [^[{chunk_id}]]."

    with patch(
        "app.core.clients.GeminiEmbeddingClient.get_embedding",
        return_value=[0.1] * 768,
    ):
        with patch(
            "app.modules.documents.semantic_cache.SemanticCacheManager.get",
            return_value=None,
        ):
            with patch(
                "app.modules.documents.chat_router.retrieve_grounding_chunks",
                return_value=mock_chunks,
            ) as mock_retrieval:
                with patch(
                    "app.core.clients.GeminiChatClient.stream_chat",
                    side_effect=mock_stream_chat,
                ):
                    with patch(
                        "app.modules.documents.semantic_cache.SemanticCacheManager.set",
                        new_callable=AsyncMock,
                    ) as mock_set:
                        response = await client.post(
                            "/api/v1/chat/stream",
                            json=req_payload,
                            headers=headers_a,
                        )
                        assert response.status_code == 200

                        lines = response.text.split("\n\n")
                        events = [
                            json.loads(line.replace("data: ", "").strip())
                            for line in lines
                            if line.strip()
                        ]

                        # Validate events streamed
                        assert len(events) >= 4
                        assert events[0]["type"] == "text"
                        assert "According to source" in events[0]["content"]

                        assert events[1]["type"] == "text"
                        assert "tenant_id" in events[1]["content"]

                        # Verify citation block
                        citation_event = next(
                            e for e in events if e["type"] == "citations"
                        )
                        assert len(citation_event["data"]) == 1
                        assert citation_event["data"][0]["chunk_id"] == chunk_id
                        assert citation_event["data"][0]["document_name"] == "arch.md"
                        assert citation_event["data"][0]["page_number"] == 3

                        # Verify cache set was called
                        mock_set.assert_called_once()
