"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from backend.app.domain.advertising_keyword_diagnosis import AdvertisingKeywordDiagnosis
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresAdvertisingKeywordDiagnosisGateway:
    """保存广告关键词诊断快照；诊断结果只读，不产生预算或出价写入。"""

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
        self, *, workspace_id: str, diagnoses: list[AdvertisingKeywordDiagnosis]
    ) -> list[AdvertisingKeywordDiagnosis]:
        """执行 save_report 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    diagnoses: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._save, workspace_id, diagnoses)

    def _save(
        self, workspace_id: str, diagnoses: list[AdvertisingKeywordDiagnosis]
    ) -> list[AdvertisingKeywordDiagnosis]:
        """执行内部步骤 _save，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    diagnoses: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            connection.execute(
                """
                INSERT INTO advertising_keyword_diagnosis_reports
                    (id, organization_id, workspace_id, diagnoses)
                VALUES (%s, %s, %s, %s::jsonb)
                """,
                (
                    str(uuid4()), self._context.organization_id, workspace_id,
                    json.dumps([asdict(item) for item in diagnoses], ensure_ascii=False),
                ),
            )
        return diagnoses

    async def list_reports(
        self, *, workspace_id: str, limit: int
    ) -> list[list[AdvertisingKeywordDiagnosis]]:
        """执行 list_reports 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return await asyncio.to_thread(self._list_reports, workspace_id, limit)

    def _list_reports(
        self, workspace_id: str, limit: int
    ) -> list[list[AdvertisingKeywordDiagnosis]]:
        """执行内部步骤 _list_reports，供同一模块的公开流程复用。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT diagnoses FROM advertising_keyword_diagnosis_reports
                    WHERE organization_id=%s AND workspace_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, workspace_id, limit),
            ).fetchall()
        return [[AdvertisingKeywordDiagnosis(**item) for item in row["diagnoses"]]
                for row in rows]
