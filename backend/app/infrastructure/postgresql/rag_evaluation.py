"""RAG 评测案例 PostgreSQL 网关；确认状态跨 API 重启持久保留。"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import timedelta
from typing import Any
from uuid import uuid4

from backend.app.domain.rag_evaluation import EvaluationCase, EvaluationRun, RagEvaluationGateway
from backend.app.infrastructure.postgresql.session import PostgresSessionFactory, TenantContext


class PostgresRagEvaluationGateway(RagEvaluationGateway):
    """在组织 RLS 事务内保存案例、人工确认人和评测运行门禁。"""

    def __init__(self, sessions: PostgresSessionFactory, context: TenantContext) -> None:
        self._sessions = sessions
        self._context = context

    async def seed_fixed_cases(self, cases: Sequence[EvaluationCase]) -> None:
        await asyncio.to_thread(self._seed_fixed_cases, cases)

    def _seed_fixed_cases(self, cases: Sequence[EvaluationCase]) -> None:
        if not cases:
            return
        with self._sessions.transaction(self._context) as connection:
            for case in cases:
                # psycopg 的项目连接类型只暴露参数化 execute；逐条写入仍在同一事务内，
                # ON CONFLICT 保证多实例启动同时种子时不会覆盖人工确认状态。
                connection.execute(
                    """INSERT INTO rag_evaluation_cases
                       (id, organization_id, question, expected_status,
                        expected_sources, safety_tags)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT (id) DO NOTHING""",
                    (case.case_id, self._context.organization_id, case.question,
                     case.expected_status, list(case.expected_sources), list(case.safety_tags)),
                )

    async def create_case(self, case: EvaluationCase) -> EvaluationCase:
        return await asyncio.to_thread(self._create_case, case)

    def _create_case(self, case: EvaluationCase) -> EvaluationCase:
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """INSERT INTO rag_evaluation_cases
                   (id, organization_id, question, expected_status, expected_sources, safety_tags)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING id, question, expected_status, expected_sources,
                             safety_tags, status""",
                (case.case_id, self._context.organization_id, case.question,
                 case.expected_status, list(case.expected_sources), list(case.safety_tags)),
            ).fetchone()
        if row is None:
            raise RuntimeError("评测案例创建后未返回持久化事实")
        return _case(row)

    async def list_cases(self) -> list[EvaluationCase]:
        return await asyncio.to_thread(self._list_cases)

    def _list_cases(self) -> list[EvaluationCase]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT id, question, expected_status, expected_sources, safety_tags, status
                   FROM rag_evaluation_cases
                   WHERE organization_id = %s ORDER BY created_at, id""",
                (self._context.organization_id,),
            ).fetchall()
        return [_case(row) for row in rows]

    async def confirm_case(self, case_id: str, reviewer: str) -> EvaluationCase | None:
        return await asyncio.to_thread(self._confirm_case, case_id, reviewer)

    def _confirm_case(self, case_id: str, reviewer: str) -> EvaluationCase | None:
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """UPDATE rag_evaluation_cases
                   SET status = 'confirmed', reviewer_id = %s, confirmed_at = CURRENT_TIMESTAMP
                   WHERE organization_id = %s AND id = %s AND status IN ('draft', 'confirmed')
                   RETURNING id, question, expected_status, expected_sources,
                             safety_tags, status""",
                (reviewer, self._context.organization_id, case_id),
            ).fetchone()
        return _case(row) if row is not None else None

    async def confirm_cases(self, case_ids: Sequence[str], reviewer: str) -> list[EvaluationCase]:
        return await asyncio.to_thread(self._confirm_cases, list(dict.fromkeys(case_ids)), reviewer)

    def _confirm_cases(self, case_ids: list[str], reviewer: str) -> list[EvaluationCase]:
        if not case_ids:
            return []
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """UPDATE rag_evaluation_cases
                   SET status = 'confirmed', reviewer_id = %s, confirmed_at = CURRENT_TIMESTAMP
                   WHERE organization_id = %s AND id = ANY(%s) AND status IN ('draft', 'confirmed')
                   RETURNING id, question, expected_status, expected_sources,
                             safety_tags, status""",
                (reviewer, self._context.organization_id, case_ids),
            ).fetchall()
        return [_case(row) for row in rows]

    async def create_run(self, suite: str, gate_status: str) -> str:
        return await asyncio.to_thread(self._create_run, suite, gate_status)

    def _create_run(self, suite: str, gate_status: str) -> str:
        run_id = f"rag-eval-{uuid4()}"
        with self._sessions.transaction(self._context) as connection:
            # 先拿事务级 advisory lock，再查询活动批次。这样两个并发点击即使来自
            # 不同 API 实例，也不能同时通过“查询后插入”的检查，避免重复消耗模型额度。
            lock_key = f"rag-evaluation:{self._context.organization_id}:{suite}"
            connection.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (lock_key,))
            # 同一组织、同一评测规模只允许一个活动批次；blocked 批次不进入这里，
            # 门禁不足时由 API 直接返回提示，不污染运行历史。
            existing = connection.execute(
                """SELECT id FROM rag_evaluation_runs
                   WHERE organization_id = %s AND suite = %s
                     AND gate_status = 'ready' AND status IN ('queued', 'running')
                   ORDER BY created_at DESC, id DESC LIMIT 1""",
                (self._context.organization_id, suite),
            ).fetchone()
            if existing is not None:
                return str(existing["id"])
            connection.execute(
                """INSERT INTO rag_evaluation_runs
                   (id, organization_id, suite, status, gate_status)
                   VALUES (%s, %s, %s, 'queued', %s)""",
                (run_id, self._context.organization_id, suite, gate_status),
            )
        return run_id

    async def find_active_run(self, suite: str) -> EvaluationRun | None:
        return await asyncio.to_thread(self._find_active_run, suite)

    def _find_active_run(self, suite: str) -> EvaluationRun | None:
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """SELECT id, suite, status, gate_status, executed_count, passed_count,
                          failed_count, error_count, metrics, error_code
                     FROM rag_evaluation_runs
                     WHERE organization_id = %s AND suite = %s
                       AND gate_status = 'ready' AND status IN ('queued', 'running')
                     ORDER BY created_at DESC, id DESC LIMIT 1""",
                (self._context.organization_id, suite),
            ).fetchone()
        return _run(row) if row is not None else None

    async def dispatchable_run_ids(self, limit: int) -> list[str]:
        return await asyncio.to_thread(self._dispatchable_run_ids, min(max(limit, 1), 100))

    def _dispatchable_run_ids(self, limit: int) -> list[str]:
        with self._sessions.transaction(self._context) as connection:
            # 过期租约先回到 queued，保证 Worker/API 重启后任务可以自动恢复。
            connection.execute(
                """UPDATE rag_evaluation_runs
                   SET status = 'queued', lease_owner = NULL, lease_expires_at = NULL
                   WHERE organization_id = %s AND status = 'running'
                     AND lease_expires_at < CURRENT_TIMESTAMP""",
                (self._context.organization_id,),
            )
            rows = connection.execute(
                """WITH candidates AS (
                       SELECT id FROM rag_evaluation_runs
                       WHERE organization_id = %s AND gate_status = 'ready'
                         AND status = 'queued'
                         AND (lease_expires_at IS NULL OR lease_expires_at < CURRENT_TIMESTAMP)
                       ORDER BY created_at, id
                       LIMIT %s
                       FOR UPDATE SKIP LOCKED
                   )
                   UPDATE rag_evaluation_runs AS runs
                   SET lease_owner = 'scheduler',
                       lease_expires_at = CURRENT_TIMESTAMP + %s
                   FROM candidates
                   WHERE runs.id = candidates.id
                   RETURNING runs.id""",
                (self._context.organization_id, limit, timedelta(seconds=15)),
            ).fetchall()
        return [str(row["id"]) for row in rows]

    async def claim_run(
        self, run_id: str, worker_id: str, lease_seconds: int
    ) -> EvaluationRun | None:
        return await asyncio.to_thread(self._claim_run, run_id, worker_id, lease_seconds)

    def _claim_run(self, run_id: str, worker_id: str, lease_seconds: int) -> EvaluationRun | None:
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """UPDATE rag_evaluation_runs
                   SET status = 'running', attempt_count = attempt_count + 1,
                       started_at = COALESCE(started_at, CURRENT_TIMESTAMP),
                       lease_owner = %s,
                       lease_expires_at = CURRENT_TIMESTAMP + %s
                   WHERE organization_id = %s AND id = %s AND gate_status = 'ready'
                     AND (status = 'queued' OR
                          (status = 'running' AND lease_expires_at < CURRENT_TIMESTAMP))
                   RETURNING id, suite, status, gate_status, executed_count, passed_count,
                             failed_count, error_count, metrics, error_code""",
                (
                    worker_id, timedelta(seconds=lease_seconds),
                    self._context.organization_id, run_id,
                ),
            ).fetchone()
        return _run(row) if row is not None else None

    async def heartbeat_run(self, run_id: str, worker_id: str, lease_seconds: int) -> bool:
        return await asyncio.to_thread(self._heartbeat_run, run_id, worker_id, lease_seconds)

    def _heartbeat_run(self, run_id: str, worker_id: str, lease_seconds: int) -> bool:
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """UPDATE rag_evaluation_runs
                   SET lease_expires_at = CURRENT_TIMESTAMP + %s
                   WHERE organization_id = %s AND id = %s AND status = 'running'
                     AND lease_owner = %s AND lease_expires_at >= CURRENT_TIMESTAMP
                   RETURNING id""",
                (
                    timedelta(seconds=lease_seconds), self._context.organization_id,
                    run_id, worker_id,
                ),
            ).fetchone()
        return row is not None

    async def list_runs(self, limit: int = 20) -> list[EvaluationRun]:
        return await asyncio.to_thread(self._list_runs, min(max(limit, 1), 100))

    def _list_runs(self, limit: int) -> list[EvaluationRun]:
        with self._sessions.transaction(self._context) as connection:
            rows = connection.execute(
                """SELECT id, suite, status, gate_status, executed_count, passed_count,
                          failed_count, error_count, metrics, error_code
                     FROM rag_evaluation_runs WHERE organization_id = %s
                     ORDER BY created_at DESC, id DESC LIMIT %s""",
                (self._context.organization_id, limit),
            ).fetchall()
        return [_run(row) for row in rows]

    async def get_run(self, run_id: str) -> EvaluationRun | None:
        return await asyncio.to_thread(self._get_run, run_id)

    def _get_run(self, run_id: str) -> EvaluationRun | None:
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """SELECT id, suite, status, gate_status, executed_count, passed_count,
                          failed_count, error_count, metrics, error_code
                     FROM rag_evaluation_runs
                     WHERE organization_id = %s AND id = %s""",
                (self._context.organization_id, run_id),
            ).fetchone()
        return _run(row) if row is not None else None

    async def save_run_metrics(
        self, run_id: str, metrics: dict[str, float | str], executed_count: int,
        passed_count: int, failed_count: int, error_count: int, worker_id: str | None = None,
        error_code: str | None = None,
    ) -> EvaluationRun | None:
        return await asyncio.to_thread(
            self._save_run_metrics, run_id, metrics, executed_count,
            passed_count, failed_count, error_count, worker_id, error_code,
        )

    def _save_run_metrics(
        self, run_id: str, metrics: dict[str, float | str], executed_count: int,
        passed_count: int, failed_count: int, error_count: int, worker_id: str | None,
        error_code: str | None,
    ) -> EvaluationRun | None:
        import json
        status = "succeeded" if metrics.get("gate_status") == "passed" else "failed"
        with self._sessions.transaction(self._context) as connection:
            row = connection.execute(
                """UPDATE rag_evaluation_runs
                   SET status = %s, executed_count = %s, passed_count = %s,
                       failed_count = %s, error_count = %s, metrics = %s::jsonb,
                       error_code = %s,
                       completed_at = CURRENT_TIMESTAMP, lease_owner = NULL,
                       lease_expires_at = NULL
                   WHERE organization_id = %s AND id = %s AND gate_status = 'ready'
                     AND status = 'running'
                     AND (%s::text IS NULL OR lease_owner = %s)
                   RETURNING id, suite, status, gate_status, executed_count, passed_count,
                             failed_count, error_count, metrics, error_code""",
                (
                    status, executed_count, passed_count, failed_count, error_count,
                    json.dumps(metrics), error_code,
                    self._context.organization_id, run_id, worker_id, worker_id,
                ),
            ).fetchone()
        return _run(row) if row is not None else None


def _case(row: dict[str, Any]) -> EvaluationCase:
    """将数据库数组字段还原为不可变领域值，避免 API 层携带驱动对象。"""
    return EvaluationCase(
        case_id=row["id"], question=row["question"], expected_status=row["expected_status"],
        expected_sources=tuple(row["expected_sources"] or []),
        safety_tags=tuple(row["safety_tags"] or []), status=row["status"],
    )


def _run(row: dict[str, Any]) -> EvaluationRun:
    """将 JSONB 聚合结果转换为前端可安全展示的脱敏摘要。"""
    return EvaluationRun(
        run_id=row["id"], suite=row["suite"], status=row["status"],
        gate_status=row["gate_status"],
        target_count={"quick": 30, "standard": 120, "full": 240}[row["suite"]],
        executed_count=row.get("executed_count", 0), passed_count=row.get("passed_count", 0),
        failed_count=row.get("failed_count", 0), error_count=row.get("error_count", 0),
        metrics=row.get("metrics") or None, error_code=row.get("error_code"),
    )
