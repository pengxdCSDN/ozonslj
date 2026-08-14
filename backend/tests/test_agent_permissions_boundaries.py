from backend.app.domain.agent_permissions import evaluate_agent_permissions


def test_agent_permissions_deny_non_string_capabilities_without_crashing() -> None:
    result = evaluate_agent_permissions("assistant", ["read_sales", 123])  # type: ignore[list-item]
    assert result.allowed_capabilities == ["read_sales"]
    assert result.denied_capabilities == ["123"]
    assert result.read_only is True
