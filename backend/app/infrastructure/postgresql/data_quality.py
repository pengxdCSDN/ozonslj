import asyncio
from datetime import datetime
from typing import Any

from backend.app.domain.data_quality import (
    QualityFinding,
    QualityFindingRecord,
    QualityFindingStatus,
)
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresQualityFindingGateway:
    """质量隔离记录的 PostgreSQL 适配器；查询始终带组织和工作区条件。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def list_findings(
        self, *, workspace_id: str, status: QualityFindingStatus | None, limit: int
    ) -> list[QualityFindingRecord]:
        return await asyncio.to_thread(self._list_findings, workspace_id, status, limit)

    async def create_findings(
        self, *, workspace_id: str, findings: list[QualityFinding]
    ) -> list[QualityFindingRecord]:
        return await asyncio.to_thread(self._create_findings, workspace_id, findings)

    def _create_findings(
        self, workspace_id: str, findings: list[QualityFinding]
    ) -> list[QualityFindingRecord]:
        from uuid import uuid4

        with self._sessions.transaction(self._context) as connection:
            records: list[QualityFindingRecord] = []
            for finding in findings:
                existing = connection.execute(
                    """
                    SELECT id, workspace_id, rule_code, field_name, severity,
                           message, status, source, created_at
                    FROM data_quality_findings
                    WHERE organization_id = %s AND workspace_id = %s
                      AND rule_code = %s AND field_name = %s
                      AND message = %s AND status = 'open'
                    LIMIT 1
                    """,
                    (self._context.organization_id, workspace_id, finding.rule_code,
                     finding.field_name, finding.message),
                ).fetchone()
                if existing is not None:
                    records.append(_record_from_row(existing))
                    continue
                row = connection.execute(
                    """
                    INSERT INTO data_quality_findings
                        (id, organization_id, workspace_id, rule_code, field_name,
                         severity, message)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, workspace_id, rule_code, field_name, severity,
                              message, status, source, created_at
                    """,
                    (str(uuid4()), self._context.organization_id, workspace_id,
                     finding.rule_code, finding.field_name, finding.severity, finding.message),
                ).fetchone()
                if row is not None:
                    records.append(_record_from_row(row))
        return records

    def _list_findings(
        self, workspace_id: str, status: QualityFindingStatus | None, limit: int
    ) -> list[QualityFindingRecord]:
        with self._sessions.transaction(self._context) as connection:
            select_sql = """
                SELECT id, workspace_id, rule_code, field_name, severity, message,
                       status, source, created_at
                FROM data_quality_findings
                WHERE organization_id = %s AND workspace_id = %s
            """
            order_limit_sql = """
                ORDER BY created_at DESC, id DESC
                LIMIT %s
            """
            if status is None:
                # 不把 NULL 状态参数送入 PostgreSQL，避免数据库无法推断参数类型。
                # 该分支仍然只返回当前组织和工作区的数据，不能绕过租户隔离。
                rows = connection.execute(
                    select_sql + order_limit_sql,
                    (self._context.organization_id, workspace_id, limit),
                ).fetchall()
            else:
                # 指定状态时使用独立的参数化条件，保持状态值不可注入且可利用索引。
                rows = connection.execute(
                    select_sql + " AND status = %s\n" + order_limit_sql,
                    (self._context.organization_id, workspace_id, status, limit),
                ).fetchall()
        return [_record_from_row(row) for row in rows]

    async def update_status(
        self, *, finding_id: str, status: QualityFindingStatus
    ) -> QualityFindingRecord | None:
        return await asyncio.to_thread(self._update_status, finding_id, status)

    def _update_status(
        self, finding_id: str, status: QualityFindingStatus
    ) -> QualityFindingRecord | None:
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """
                UPDATE data_quality_findings
                SET status = %s,
                    resolved_at = CASE WHEN %s = 'resolved'
                        THEN CURRENT_TIMESTAMP ELSE NULL END
                WHERE id = %s AND organization_id = %s
                RETURNING id, workspace_id, rule_code, field_name, severity, message,
                          status, source, created_at
                """,
                (status, status, finding_id, self._context.organization_id),
            ).fetchone()
        return _record_from_row(row) if row is not None else None


def _record_from_row(row: dict[str, Any]) -> QualityFindingRecord:
    created_at = row["created_at"]
    if not isinstance(created_at, datetime):
        raise ValueError("质量记录 created_at 必须是有效时间")
    return QualityFindingRecord(
        id=str(row["id"]), workspace_id=str(row["workspace_id"]), rule_code=str(row["rule_code"]),
        field_name=str(row["field_name"]), severity=row["severity"], message=str(row["message"]),
        status=row["status"], source=row["source"], created_at=created_at,
    )
