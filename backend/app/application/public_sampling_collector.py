"""把受控公开采样、快照解析和工作区持久化编排成单向应用流程。"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from backend.app.domain.automation_orchestration import AutomationEvent, AutomationEventPublisher
from backend.app.domain.public_sampling import (
    FetchResponse,
    PublicSampler,
    SamplingRequest,
    SamplingResult,
)
from backend.app.domain.public_snapshot import PublicSnapshot, PublicSnapshotGateway
from backend.app.domain.public_snapshot_parser import parse_public_snapshot_html

FetchPage = Callable[[str], Awaitable[int | tuple[int, float | None] | FetchResponse]]


class PublicSamplingCollector:
    """只保存成功且可解析的公开字段，阻断或解析失败只返回结果。"""

    def __init__(
        self,
        snapshots: PublicSnapshotGateway,
        fetch_page: FetchPage,
        event_publisher: AutomationEventPublisher | None = None,
    ) -> None:
        self._snapshots = snapshots
        self._fetch_page = fetch_page
        self._event_publisher = event_publisher

    async def collect(
        self, *, workspace_id: str, urls: list[str], global_limit: int, max_attempts: int
    ) -> tuple[list[SamplingResult], list[PublicSnapshot]]:
        bodies: dict[str, str] = {}

        async def fetch(url: str) -> int | tuple[int, float | None] | FetchResponse:
            response = await self._fetch_page(url)
            if isinstance(response, FetchResponse) and response.body is not None:
                bodies[url] = response.body
            return response

        results = await PublicSampler(
            fetch, global_limit=global_limit, max_attempts=max_attempts
        ).sample([SamplingRequest(url) for url in urls])
        saved: list[PublicSnapshot] = []
        for result in results:
            body = bodies.get(result.url)
            if not result.allowed or body is None:
                continue
            try:
                snapshot = parse_public_snapshot_html(
                    url=result.url, html=body, sampled_at=datetime.now(UTC)
                )
            except ValueError:
                continue
            persisted = await self._snapshots.save_snapshot(
                workspace_id=workspace_id, snapshot=snapshot
            )
            saved.append(persisted)
            if self._event_publisher is not None:
                run_id = (
                    f"public-snapshot:{workspace_id}:{snapshot.url}:"
                    f"{snapshot.sampled_at.isoformat()}"
                )
                await self._event_publisher.publish_once(
                    AutomationEvent(
                        event_id=f"{run_id}:external_fact_changed",
                        event_type="external_fact_changed",
                        workspace_id=workspace_id,
                        run_id=run_id,
                        root_run_id=run_id,
                        source="public_sampling",
                        data_version=snapshot.sampled_at.isoformat(),
                    )
                )
        return results, saved
