import asyncio
import json
from uuid import uuid4

from backend.app.domain.manual_approval import ManualApproval
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresManualApprovalGateway:
    """保存人工审批状态；本适配器只改变审批记录，不执行任何外部写入。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def create(
        self,
        *, workspace_id: str, command_type: str, payload: dict[str, object],
        idempotency_key: str,
    ) -> ManualApproval:
        return await asyncio.to_thread(
            self._create, workspace_id, command_type, payload, idempotency_key
        )

    def _create(
        self, workspace_id: str, command_type: str, payload: dict[str, object], idempotency_key: str
    ) -> ManualApproval:
        approval_id = str(uuid4())
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute("""INSERT INTO manual_approvals
                (approval_id, organization_id, workspace_id, command_type, payload, status,
                 idempotency_key)
                VALUES (%s, %s, %s, %s, %s::jsonb, 'pending', %s)
                ON CONFLICT (organization_id, workspace_id, idempotency_key)
                DO UPDATE SET idempotency_key = EXCLUDED.idempotency_key
                RETURNING approval_id, workspace_id, command_type, payload,
                    status, reviewer, idempotency_key""", (
                approval_id, self._context.organization_id, workspace_id, command_type,
                json.dumps(payload), idempotency_key,
            )).fetchone()
        if row is None:
            raise RuntimeError("审批幂等记录写入后无法读取")
        return ManualApproval(
            str(row["approval_id"]), str(row["workspace_id"]), str(row["command_type"]),
            row["payload"], str(row["status"]), row["reviewer"], str(row["idempotency_key"]),
        )

    async def approve(self, *, approval_id: str, reviewer: str) -> ManualApproval | None:
        return await asyncio.to_thread(self._approve, approval_id, reviewer)

    async def list_pending(self, *, workspace_id: str, limit: int) -> list[ManualApproval]:
        return await asyncio.to_thread(self._list_pending, workspace_id, limit)

    def _list_pending(self, workspace_id: str, limit: int) -> list[ManualApproval]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT approval_id, workspace_id, command_type, payload, status,
                    reviewer, idempotency_key FROM manual_approvals
                    WHERE organization_id=%s AND workspace_id=%s AND status='pending'
                    ORDER BY created_at ASC, approval_id ASC LIMIT %s""",
                (self._context.organization_id, workspace_id, max(1, min(limit, 100))),
            ).fetchall()
        return [
            ManualApproval(
                str(row["approval_id"]), str(row["workspace_id"]),
                str(row["command_type"]), row["payload"], str(row["status"]),
                row["reviewer"], str(row["idempotency_key"]),
            )
            for row in rows
        ]

    def _approve(self, approval_id: str, reviewer: str) -> ManualApproval | None:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute("""UPDATE manual_approvals SET status='approved',
                reviewer=%s, decided_at=NOW()
                WHERE approval_id=%s AND organization_id=%s AND status='pending'
                RETURNING approval_id, workspace_id, command_type, payload, status, reviewer,
                    idempotency_key""", (
                reviewer, approval_id, self._context.organization_id,
            )).fetchall()
        if not rows:
            return None
        row = rows[0]
        return ManualApproval(
            str(row["approval_id"]), str(row["workspace_id"]), str(row["command_type"]),
            row["payload"], str(row["status"]), row["reviewer"], str(row["idempotency_key"]),
        )
