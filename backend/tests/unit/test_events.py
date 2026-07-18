import pytest

from app.core.events import DomainEventsMixin


class DummyModel(DomainEventsMixin):
    pass


@pytest.mark.unit
def test_record_and_pull_events():
    model = DummyModel()
    assert len(model.domain_events) == 0

    model.record_event("user.created", {"user_id": "123"})
    assert len(model.domain_events) == 1

    events = model.pull_events()
    assert len(events) == 1
    assert events[0].event_type == "user.created"
    assert events[0].payload == {"user_id": "123"}

    # Pull should clear the events
    assert len(model.domain_events) == 0
    assert len(model.pull_events()) == 0
