from backend.app.domain.agent_permissions import evaluate_agent_permissions


def test_agent_permissions_deny_write_sql_and_credentials() -> None:
    result = evaluate_agent_permissions(
        "sales_agent", ["read_sales", "create_report", "execute_sql", "write_price"]
    )
    assert result.allowed_capabilities == ["read_sales", "create_report"]
    assert result.denied_capabilities == ["execute_sql", "write_price"]
    assert result.sql_access is False
    assert result.credential_access is False
    assert result.external_write_access is False
    assert result.read_only is True
