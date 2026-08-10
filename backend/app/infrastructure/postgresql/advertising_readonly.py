import asyncio
from uuid import uuid4

from backend.app.domain.advertising_readonly import AdvertisingReadOnlyDecision
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresAdvertisingBoundaryGateway:
    """记录广告动作边界判定，确保被阻断的写动作也可审计。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def save_check(
        self, *, workspace_id: str, decision: AdvertisingReadOnlyDecision
    ) -> AdvertisingReadOnlyDecision:
        return await asyncio.to_thread(self._save, workspace_id, decision)

    def _save(
        self, workspace_id: str, decision: AdvertisingReadOnlyDecision
    ) -> AdvertisingReadOnlyDecision:
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO advertising_boundary_checks
                    (id, organization_id, workspace_id, action, allowed, reason, audit_required)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    decision.action, decision.allowed, decision.reason, decision.audit_required,
                ),
            )
        return decision

    async def list_checks(
        self, *, workspace_id: str, limit: int
    ) -> list[AdvertisingReadOnlyDecision]:
        return await asyncio.to_thread(self._list_checks, workspace_id, limit)

    def _list_checks(self, workspace_id: str, limit: int) -> list[AdvertisingReadOnlyDecision]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT action, allowed, reason, audit_required
                    FROM advertising_boundary_checks
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [AdvertisingReadOnlyDecision(
            action=str(row["action"]), allowed=bool(row["allowed"]),
            reason=str(row["reason"]), audit_required=bool(row["audit_required"]),
        ) for row in rows]
