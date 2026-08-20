"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.search_attributes import SearchAttributesReport, SearchAttributeSuggestion
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresSearchAttributesGateway:
    """保存 Search Attributes 建议及覆盖报告，保持可编辑只读边界。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        """初始化对象依赖和运行时状态。

Args:
    sessions: 参数语义、输入边界和安全约束。
    context: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._sessions = sessions
        self._context = context

    async def save_report(
        self, *, workspace_id: str, product_scope: str, report: SearchAttributesReport
    ) -> SearchAttributesReport:
        """执行 save_report 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    product_scope: 参数语义、输入边界和安全约束。
    report: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._save, workspace_id, product_scope, report)

    def _save(
        self, workspace_id: str, product_scope: str, report: SearchAttributesReport
    ) -> SearchAttributesReport:
        """执行内部步骤 _save，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    product_scope: 参数语义、输入边界和安全约束。
    report: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO search_attributes_reports
                    (id, organization_id, workspace_id, product_scope, report, coverage_percent,
                     missing_required, editable)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id, product_scope,
                    json.dumps(asdict(report), ensure_ascii=False), report.coverage_percent,
                    json.dumps(report.missing_required, ensure_ascii=False), report.editable,
                ),
            )
        return report

    async def list_reports(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[SearchAttributesReport]:
        """执行 list_reports 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list, workspace_id, limit)

    def _list(self, workspace_id: str, limit: int) -> list[SearchAttributesReport]:
        # 报告历史仅按当前组织和工作区读取，保证属性建议不会跨工作区串用。
        """执行内部步骤 _list，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT report
                FROM search_attributes_reports
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (self._context.organization_id, workspace_id, max(1, min(limit, 200))),
            ).fetchall()
        return [SearchAttributesReport(
            suggestions=tuple(
                SearchAttributeSuggestion(**item)
                for item in row["report"]["suggestions"]
            ),
            coverage_percent=float(row["report"]["coverage_percent"]),
            missing_required=tuple(row["report"]["missing_required"]),
            editable=bool(row["report"]["editable"]),
        ) for row in rows]
