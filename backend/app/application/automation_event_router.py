"""自动化事实事件路由。

本模块只负责把已通过 Redis Consumer 校验的事实变化事件路由到下游质量检查端口。
它不直接刷新页面、不修改规则、不执行外部写操作；质量检查任务的持久化由后续
PostgreSQL 适配器实现，避免复用同步任务表造成任务语义混淆。
"""

from backend.app.domain.automation_orchestration import (
    AutomationEvent,
    AutomationRun,
    build_idempotency_key,
    ensure_trigger_allowed,
)
from backend.app.domain.data_quality import QualityCheckJobGateway


class AutomationEventRouter:
    """将白名单事实事件路由到质量检查，不允许事件反向触发同步。"""

    def __init__(self, quality_checks: QualityCheckJobGateway) -> None:
        self._quality_checks = quality_checks

    async def route(self, event: AutomationEvent) -> bool:
        """路由一个事实变化事件；同一根运行和数据版本只创建一次质量任务。"""
        run = AutomationRun(
            run_id=event.run_id,
            workspace_id=event.workspace_id,
            automation_type="quality_check",
            data_version=event.data_version,
            root_run_id=event.root_run_id,
            parent_run_id=event.run_id,
            depth=1,
        )
        ensure_trigger_allowed(
            event_type=event.event_type,
            target="data_quality",
            run=run,
        )
        return await self._quality_checks.schedule_quality_check(
            workspace_id=event.workspace_id,
            data_version=event.data_version,
            idempotency_key=build_idempotency_key(run),
            parent_run_id=event.run_id,
        )
