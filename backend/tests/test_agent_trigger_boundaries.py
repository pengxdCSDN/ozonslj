import pytest

from backend.app.domain.agent_trigger import create_agent_trigger


def test_agent_trigger_rejects_cross_mode_fields_and_non_boolean_enabled() -> None:
    with pytest.raises(ValueError):
        create_agent_trigger(
            trigger_type="scheduled", target="sales", schedule="0 9 * * *",
            event_name="stock_changed", enabled=True,
        )
    with pytest.raises(ValueError):
        create_agent_trigger(
            trigger_type="manual", target="sales", schedule=None,
            event_name=None, enabled=1,  # type: ignore[arg-type]
        )
