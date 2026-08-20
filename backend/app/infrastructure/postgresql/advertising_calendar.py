"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
import json
from dataclasses import asdict
from datetime import date
from uuid import uuid4

from backend.app.domain.advertising_calendar import AdvertisingCalendarDay
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresAdvertisingCalendarGateway:
    """保存新品 30 天建议快照；建议只读，不执行预算、出价或否定词变更。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。"""
        self._sessions = sessions
        self._context = context

    async def save_calendar(
        self, *, workspace_id: str, start_date: date,
        days: list[AdvertisingCalendarDay]
    ) -> list[AdvertisingCalendarDay]:
        """执行 save_calendar 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._save, workspace_id, start_date, days)

    def _save(
        self, workspace_id: str, start_date: date,
        days: list[AdvertisingCalendarDay]
    ) -> list[AdvertisingCalendarDay]:
        """执行内部步骤 _save，供同一模块的公开流程复用。"""
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO advertising_calendars
                    (id, organization_id, workspace_id, start_date, days)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id, start_date,
                    json.dumps(
                        [asdict(item) | {"date": item.date.isoformat()} for item in days],
                        ensure_ascii=False,
                    ),
                ),
            )
        return days

    async def list_calendars(
        self, *, workspace_id: str, limit: int
    ) -> list[list[AdvertisingCalendarDay]]:
        """执行 list_calendars 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._list_calendars, workspace_id, limit)

    def _list_calendars(
        self, workspace_id: str, limit: int
    ) -> list[list[AdvertisingCalendarDay]]:
        """执行内部步骤 _list_calendars，供同一模块的公开流程复用。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT days FROM advertising_calendars
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [[AdvertisingCalendarDay(
            day=int(item["day"]), date=date.fromisoformat(str(item["date"])),
            phase=str(item["phase"]), recommendation=str(item["recommendation"]),
            read_only=bool(item["read_only"]),
        ) for item in row["days"]] for row in rows]
