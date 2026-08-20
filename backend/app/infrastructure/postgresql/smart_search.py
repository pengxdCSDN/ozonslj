"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.smart_search import SmartSearchFinding, SmartSearchReport
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresSmartSearchGateway:
    """保存 Smart Search 检查结果和原文，保证建议可追溯且不修改原始草稿。"""

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
        self, *, workspace_id: str, product_scope: str, source_text: str,
        report: SmartSearchReport
    ) -> SmartSearchReport:
        """执行 save_report 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    product_scope: 参数语义、输入边界和安全约束。
    source_text: 参数语义、输入边界和安全约束。
    report: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(
            self._save, workspace_id, product_scope, source_text, report
        )

    def _save(
        self, workspace_id: str, product_scope: str, source_text: str,
        report: SmartSearchReport
    ) -> SmartSearchReport:
        """执行内部步骤 _save，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    product_scope: 参数语义、输入边界和安全约束。
    source_text: 参数语义、输入边界和安全约束。
    report: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO listing_smart_search_reports
                    (id, organization_id, workspace_id, product_scope, source_text,
                     findings, covered_terms, missing_terms, valid, original_text_preserved)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id, product_scope,
                    source_text,
                    json.dumps([asdict(item) for item in report.findings], ensure_ascii=False),
                    json.dumps(report.covered_terms, ensure_ascii=False),
                    json.dumps(report.missing_terms, ensure_ascii=False), report.valid,
                    report.original_text_preserved,
                ),
            )
        return report

    async def list_reports(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[SmartSearchReport]:
        """执行 list_reports 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list, workspace_id, limit)

    def _list(self, workspace_id: str, limit: int) -> list[SmartSearchReport]:
        # 检查历史只读当前组织和工作区，且报告保留原文不被结果覆盖。
        """执行内部步骤 _list，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """
                SELECT findings, covered_terms, missing_terms, valid, original_text_preserved
                FROM listing_smart_search_reports
                WHERE organization_id = %s AND workspace_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (self._context.organization_id, workspace_id, max(1, min(limit, 200))),
            ).fetchall()
        return [SmartSearchReport(
            findings=tuple(SmartSearchFinding(**item) for item in row["findings"]),
            covered_terms=tuple(row["covered_terms"]),
            missing_terms=tuple(row["missing_terms"]),
            valid=bool(row["valid"]),
            original_text_preserved=bool(row["original_text_preserved"]),
        ) for row in rows]
