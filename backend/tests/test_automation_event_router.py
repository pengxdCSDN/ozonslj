"""事实事件路由到数据质量任务的幂等边界测试。"""

import asyncio
from dataclasses import dataclass, field

from backend.app.application.automation_event_router import AutomationEventRouter
from backend.app.domain.automation_orchestration import AutomationEvent


@dataclass
class FakeQualityChecks:
    requests: list[dict[str, str]] = field(default_factory=list)
    result: bool = True

    async def schedule_quality_check(
        self, *, workspace_id: str, data_version: str, idempotency_key: str, parent_run_id: str
    ) -> bool:
        self.requests.append({
            "workspace_id": workspace_id,
            "data_version": data_version,
            "idempotency_key": idempotency_key,
            "parent_run_id": parent_run_id,
        })
        return self.result


def _event() -> AutomationEvent:
    return AutomationEvent(
        event_id="run-1:external_fact_changed",
        event_type="external_fact_changed",
        workspace_id="workspace-1",
        run_id="run-1",
        root_run_id="run-1",
        source="stock",
        data_version="version-1",
    )


def test_fact_event_routes_to_quality_check_with_parent_context() -> None:
    quality_checks = FakeQualityChecks()
    router = AutomationEventRouter(quality_checks)

    assert asyncio.run(router.route(_event())) is True
    assert quality_checks.requests[0] == {
        "workspace_id": "workspace-1",
        "data_version": "version-1",
        "idempotency_key": "workspace-1:run-1:quality_check:version-1",
        "parent_run_id": "run-1",
    }


def test_quality_check_reuses_idempotency_result() -> None:
    quality_checks = FakeQualityChecks(result=False)
    router = AutomationEventRouter(quality_checks)

    assert asyncio.run(router.route(_event())) is False
    assert len(quality_checks.requests) == 1
