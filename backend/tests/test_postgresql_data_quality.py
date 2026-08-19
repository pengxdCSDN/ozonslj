from datetime import UTC, datetime
from typing import Any

from backend.app.infrastructure.postgresql.data_quality import PostgresQualityFindingGateway


class _Connection:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def execute(self, sql: str, params: tuple[object, ...]) -> "_Result":
        self.calls.append((sql, params))
        return _Result(self.rows)


class _Result:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def fetchall(self) -> list[dict[str, Any]]:
        return self.rows


class _Transaction:
    def __init__(self, connection: _Connection) -> None:
        self.connection = connection

    def __enter__(self) -> _Connection:
        return self.connection

    def __exit__(self, *_args: object) -> None:
        return None


class _Sessions:
    def __init__(self, connection: _Connection) -> None:
        self.connection = connection

    def transaction(self, _context: object) -> _Transaction:
        return _Transaction(self.connection)


def _gateway(connection: _Connection) -> PostgresQualityFindingGateway:
    context = type("Context", (), {"organization_id": "org-1"})()
    return PostgresQualityFindingGateway(_Sessions(connection), context)  # type: ignore[arg-type]


def _row() -> dict[str, Any]:
    return {
        "id": "finding-1",
        "workspace_id": "workspace-1",
        "rule_code": "DQ-001",
        "field_name": "offer_id",
        "severity": "warning",
        "message": "需要确认",
        "status": "open",
        "source": "derived_quality",
        "created_at": datetime.now(UTC),
    }


def test_list_findings_without_status_does_not_bind_nullable_status_parameter() -> None:
    connection = _Connection([_row()])

    records = _gateway(connection)._list_findings("workspace-1", None, 100)

    assert len(records) == 1
    sql, params = connection.calls[0]
    assert "status = %s" not in sql
    assert params == ("org-1", "workspace-1", 100)


def test_list_findings_with_status_keeps_status_filter_parameterized() -> None:
    connection = _Connection([_row()])

    records = _gateway(connection)._list_findings("workspace-1", "open", 100)

    assert len(records) == 1
    sql, params = connection.calls[0]
    assert "AND status = %s" in sql
    assert params == ("org-1", "workspace-1", "open", 100)
