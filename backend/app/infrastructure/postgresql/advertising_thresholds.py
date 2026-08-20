"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from uuid import uuid4

from backend.app.domain.advertising_thresholds import AdvertisingThresholds
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresAdvertisingThresholdGateway:
    """按工作区保存广告诊断阈值版本，历史版本只追加不覆盖。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._context = context

    async def save(
        self, *, workspace_id: str, thresholds: AdvertisingThresholds
    ) -> AdvertisingThresholds:
        """执行 save 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    thresholds: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._save, workspace_id, thresholds)

    def _save(
        self, workspace_id: str, thresholds: AdvertisingThresholds
    ) -> AdvertisingThresholds:
        """执行内部步骤 _save，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    thresholds: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO advertising_threshold_versions
                    (id, organization_id, workspace_id, version_no, min_impressions,
                     min_clicks, high_cvr_percent, high_spend_minor)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    thresholds.version, thresholds.min_impressions, thresholds.min_clicks,
                    thresholds.high_cvr_percent, thresholds.high_spend_minor,
                ),
            )
        return thresholds

    async def list_versions(
        self, *, workspace_id: str, limit: int
    ) -> list[AdvertisingThresholds]:
        """执行 list_versions 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list_versions, workspace_id, limit)

    def _list_versions(self, workspace_id: str, limit: int) -> list[AdvertisingThresholds]:
        """执行内部步骤 _list_versions，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT version_no, min_impressions, min_clicks, high_cvr_percent,
                    high_spend_minor FROM advertising_threshold_versions
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY version_no DESC, created_at DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [AdvertisingThresholds(
            version=int(row["version_no"]), min_impressions=int(row["min_impressions"]),
            min_clicks=int(row["min_clicks"]), high_cvr_percent=float(row["high_cvr_percent"]),
            high_spend_minor=int(row["high_spend_minor"]),
        ) for row in rows]
