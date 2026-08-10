import pytest

from backend.app.domain.agent_trigger import create_agent_trigger


def test_agent_trigger_supports_three_modes_and_is_read_only() -> None:
    for trigger_type, schedule, event_name in [
        ("scheduled", "0 9 * * *", None), ("event", None, "stock_below_safety"),
        ("manual", None, None),
    ]:
        result = create_agent_trigger(
            trigger_type=trigger_type, target="sales_agent", schedule=schedule,
            event_name=event_name, enabled=True,
        )
        assert result.read_only is True


def test_agent_trigger_requires_mode_specific_parameter() -> None:
    with pytest.raises(ValueError, match="周期"):
        create_agent_trigger(
            trigger_type="scheduled", target="sales", schedule=None,
            event_name=None, enabled=False,
        )
