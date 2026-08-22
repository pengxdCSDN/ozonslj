"""利润对账批次和明细的 PostgreSQL 事实存储适配器。"""

import asyncio
from datetime import datetime
from typing import Any
from uuid import uuid4

from backend.app.domain.profit_reconciliation_record import (
    ProfitReconciliationBatch,
    ProfitReconciliationRecord,
)
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresProfitReconciliationGateway:
    """保存和读取工作区范围内的对账事实；重复幂等键复用原批次。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def create_batch(
        self,
        *,
        workspace_id: str,
        idempotency_key: str,
        source: str,
        status: str,
        records: list[ProfitReconciliationRecord],
    ) -> ProfitReconciliationBatch:
        return await asyncio.to_thread(
            self._create_batch, workspace_id, idempotency_key, source, status, records
        )

    def _create_batch(
        self,
        workspace_id: str,
        idempotency_key: str,
        source: str,
        status: str,
        records: list[ProfitReconciliationRecord],
    ) -> ProfitReconciliationBatch:
        with self._sessions.transaction(self._context) as connection:
            existing = connection.execute(
                """SELECT id, workspace_id, idempotency_key, source, status, created_at
                   FROM profit_reconciliation_batches
                   WHERE organization_id = %s AND workspace_id = %s AND idempotency_key = %s""",
                (self._context.organization_id, workspace_id, idempotency_key),
            ).fetchone()
            if existing is not None:
                return _batch_from_row(existing)
            batch_id = str(uuid4())
            row = connection.execute(
                """INSERT INTO profit_reconciliation_batches
                   (id, organization_id, workspace_id, idempotency_key, source, status)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING id, workspace_id, idempotency_key, source, status, created_at""",
                (
                    batch_id,
                    self._context.organization_id,
                    workspace_id,
                    idempotency_key,
                    source,
                    status,
                ),
            ).fetchone()
            if row is None:
                raise RuntimeError("对账批次写入后未返回批次记录")
            for record in records:
                connection.execute(
                    """INSERT INTO profit_reconciliation_records
                       (id, organization_id, batch_id, workspace_id, order_id, sku_id,
                        estimated_profit_minor, actual_profit_minor, variance_minor, side, source)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        record.id,
                        self._context.organization_id,
                        batch_id,
                        workspace_id,
                        record.order_id,
                        record.sku_id,
                        record.estimated_profit_minor,
                        record.actual_profit_minor,
                        record.variance_minor,
                        record.side,
                        record.source,
                    ),
                )
            return _batch_from_row(row)

    async def list_records(
        self,
        *,
        workspace_id: str,
        batch_id: str | None = None,
        limit: int = 100,
    ) -> list[ProfitReconciliationRecord]:
        return await asyncio.to_thread(self._list_records, workspace_id, batch_id, limit)

    def _list_records(
        self,
        workspace_id: str,
        batch_id: str | None,
        limit: int,
    ) -> list[ProfitReconciliationRecord]:
        where = "organization_id = %s AND workspace_id = %s"
        params: list[object] = [self._context.organization_id, workspace_id]
        if batch_id is not None:
            where += " AND batch_id = %s"
            params.append(batch_id)
        params.append(limit)
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                f"""SELECT id, batch_id, workspace_id, order_id, sku_id,
                           estimated_profit_minor, actual_profit_minor, variance_minor,
                           side, source, created_at
                    FROM profit_reconciliation_records
                    WHERE {where}
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                tuple(params),
            ).fetchall()
        return [_record_from_row(row) for row in rows]


def _batch_from_row(row: dict[str, Any]) -> ProfitReconciliationBatch:
    return ProfitReconciliationBatch(
        id=str(row["id"]),
        workspace_id=str(row["workspace_id"]),
        idempotency_key=str(row["idempotency_key"]),
        source=str(row["source"]),
        status=row["status"],
        created_at=_required_datetime(row["created_at"]),
    )


def _record_from_row(row: dict[str, Any]) -> ProfitReconciliationRecord:
    return ProfitReconciliationRecord(
        id=str(row["id"]),
        batch_id=str(row["batch_id"]),
        workspace_id=str(row["workspace_id"]),
        order_id=str(row["order_id"]),
        sku_id=str(row["sku_id"]),
        estimated_profit_minor=row["estimated_profit_minor"],
        actual_profit_minor=row["actual_profit_minor"],
        variance_minor=row["variance_minor"],
        side=row["side"],
        source=str(row["source"]),
        created_at=_required_datetime(row["created_at"]),
    )


def _required_datetime(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError("对账记录 created_at 必须是时间")
    return value
