from backend.app.domain.readonly_tool import authorize_readonly_tool


def test_only_whitelisted_parameterized_tools_are_allowed() -> None:
    result = authorize_readonly_tool("sales_summary", {"workspace_id": "ws-1", "window": "7d"})
    assert result.allowed is True
    assert result.parameters == {"workspace_id": "ws-1", "window": "7d"}
    assert result.sql_allowed is False


def test_sql_and_unknown_tools_are_rejected() -> None:
    assert authorize_readonly_tool("sales_summary", {"sql": "SELECT 1"}).allowed is False
    assert authorize_readonly_tool("execute_sql", {}).allowed is False


def test_readonly_tool_requires_workspace_context() -> None:
    assert authorize_readonly_tool("sales_summary", {"window": "7d"}).allowed is False
