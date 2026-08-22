"""把受控公开采样、快照解析和工作区持久化编排成单向应用流程。"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

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

    def __init__(self, snapshots: PublicSnapshotGateway, fetch_page: FetchPage) -> None:
        self._snapshots = snapshots
        self._fetch_page = fetch_page

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
            saved.append(
                await self._snapshots.save_snapshot(
                    workspace_id=workspace_id, snapshot=snapshot
                )
            )
        return results, saved
