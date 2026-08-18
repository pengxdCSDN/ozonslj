"""RAG 质量评测持久化 Worker；API 重启不丢任务，租约过期可自动恢复。"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import suppress

from backend.app.domain.knowledge_runtime import get_knowledge_runtime, resolve_knowledge_engine
from backend.app.domain.rag_evaluation import RagEvaluationGateway, suite_case_limit
from backend.app.domain.rag_metrics import quality_gate_passed
from backend.app.domain.rag_quality_runner import classify_evaluation_error, run_fixed_quality_suite
from backend.app.infrastructure.redis_rag_evaluation import RedisRagEvaluationTaskConsumer

logger = logging.getLogger(__name__)


class RagEvaluationWorker:
    """领取评测运行、执行固定集并将脱敏聚合结果回写 PostgreSQL。"""

    def __init__(
        self,
        runs: RagEvaluationGateway,
        consumer: RedisRagEvaluationTaskConsumer,
        *,
        worker_id: str,
        lease_seconds: int = 300,
    ) -> None:
        self._runs = runs
        self._consumer = consumer
        self._worker_id = worker_id
        self._lease_seconds = lease_seconds

    async def process_one(self, *, block_ms: int = 1_000) -> bool:
        message = await self._consumer.read_one(block_ms=block_ms)
        if message is None:
            return False
        message_id, run_id = message
        run = await self._runs.claim_run(run_id, self._worker_id, self._lease_seconds)
        if run is None:
            await self._consumer.acknowledge(message_id)
            return True
        heartbeat = asyncio.create_task(self._heartbeat(run_id))
        try:
            runtime = get_knowledge_runtime()
            # 生产运行时提供隔离的固定评测索引；本地内存运行时没有该外部 collection，
            # 因此继续使用原有 engine，保持离线契约测试不依赖 Chroma。
            evaluation_builder = getattr(runtime, "evaluation_engine", None)
            engine = (
                await evaluation_builder()
                if evaluation_builder is not None
                else await resolve_knowledge_engine(runtime)
            )
            report = await run_fixed_quality_suite(engine, run.suite)  # type: ignore[arg-type]
            metrics: dict[str, float | str] = {
                "recall": report.metrics.recall,
                "precision": report.metrics.precision,
                "citation_support_rate": report.metrics.citation_support_rate,
                "correct_refusal_rate": report.metrics.correct_refusal_rate,
                "average_latency_ms": report.metrics.average_latency_ms,
                "estimated_cost": report.metrics.estimated_cost,
                "recall_at_5": report.metrics.recall_at_5,
                "recall_at_10": report.metrics.recall_at_10,
                "precision_at_5": report.metrics.precision_at_5,
                "multi_intent_completeness": report.metrics.multi_intent_completeness,
                "safety_pass_rate": report.metrics.safety_pass_rate,
                "degradation_pass_rate": report.metrics.degradation_pass_rate,
                # 只保存稳定错误码及数量，不保存供应商原始响应、请求正文或凭据。
                "error_breakdown": json.dumps(
                    report.error_breakdown, ensure_ascii=False, sort_keys=True
                ),
                "primary_error_code": report.primary_error_code or "none",
                "gate_status": "passed" if quality_gate_passed(report.metrics) else "blocked",
            }
            saved = await self._runs.save_run_metrics(
                run_id,
                metrics,
                report.executed_count,
                report.executed_count if report.status == "completed" else 0,
                max(report.executed_count - report.error_count, 0)
                if report.status != "completed" else 0,
                report.error_count,
                self._worker_id,
                report.primary_error_code,
            )
        except Exception as error:
            error_code = classify_evaluation_error(error)
            # 这里不打印异常正文，避免第三方 SDK 将响应片段或敏感请求信息带入日志。
            logger.error("评测运行 %s 执行失败，error_code=%s", run_id, error_code)
            try:
                saved = await self._runs.save_run_metrics(
                    run_id,
                    {
                        "gate_status": "blocked",
                        "primary_error_code": error_code,
                        "error_breakdown": json.dumps({error_code: suite_case_limit(run.suite)}),
                    },
                    0, 0, 0, suite_case_limit(run.suite), self._worker_id,
                    error_code,
                )
            except Exception:
                # 回写失败不能让 Worker 进程退出；未确认的 Redis 消息会保留，
                # PostgreSQL 租约到期后由 Scheduler 重新投递，避免静默丢任务。
                logger.exception("评测运行 %s 失败结果回写异常", run_id)
                saved = None
        finally:
            heartbeat.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat
        if saved is not None:
            await self._consumer.acknowledge(message_id)
        return saved is not None

    async def _heartbeat(self, run_id: str) -> None:
        interval = max(1, self._lease_seconds // 3)
        while True:
            await asyncio.sleep(interval)
            if not await self._runs.heartbeat_run(run_id, self._worker_id, self._lease_seconds):
                return
