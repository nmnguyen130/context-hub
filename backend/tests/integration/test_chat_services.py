import uuid

import pytest

from app.modules.chat.memory.session_service import ChatSessionService
from app.modules.chat.models import ChatMessage, ChatSession
from app.modules.documents.models import Workspace
from tests.factories import make_tenant, make_user


@pytest.mark.integration
async def test_message_feedback_update(uow, make_tenant_uow):
    """Test setting thumbs up/down feedback rating and note on a ChatMessage."""
    tenant = make_tenant()
    uow.session.add(tenant)
    await uow.commit()

    user = make_user(tenant_id=tenant.id)
    workspace = Workspace(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Feedback Workspace",
        slug="feedback-ws",
    )
    uow.session.add_all([user, workspace])
    await uow.commit()

    session = ChatSession(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        workspace_id=workspace.id,
        title="Feedback Session",
    )
    msg = ChatMessage(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        session_id=session.id,
        role="assistant",
        content="Answer content",
        token_count=10,
    )
    uow.session.add_all([session, msg])
    await uow.commit()

    async with make_tenant_uow(tenant.id, user.id) as tenant_uow:
        service = ChatSessionService(uow=tenant_uow)
        updated_msg = await service.set_message_feedback(
            tenant_id=tenant.id,
            message_id=msg.id,
            feedback="up",
            feedback_note="Accurate response",
        )
        await tenant_uow.commit()

        assert updated_msg.feedback == "up"
        assert updated_msg.feedback_note == "Accurate response"
