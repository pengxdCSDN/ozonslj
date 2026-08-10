import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from urllib.parse import urlparse

from backend.app.domain.sampling_policy import SamplingPolicyDecision, check_sampling_policy


@dataclass(frozen=True, slots=True)
class SamplingRequest:
    url: str
    robots_allowed: bool = True
    rate_limited: bool = False
    stop_requested: bool = False


@dataclass(frozen=True, slots=True)
class SamplingResult:
    url: str
    allowed: bool
    status_code: int | None
    attempts: int
    message: str


FetchPage = Callable[[str], Awaitable[int | tuple[int, float | None]]]


class PublicSampler:
    """执行受控公开采样：全局最多 2 个请求，单域名始终串行。"""

    def __init__(
        self, fetch_page: FetchPage, *, global_limit: int = 2, max_attempts: int = 3
    ) -> None:
        if global_limit < 1 or max_attempts < 1:
            raise ValueError("采样并发和重试次数必须为正数")
        self._fetch_page = fetch_page
        self._global_limit = asyncio.Semaphore(global_limit)
        self._domain_locks: dict[str, asyncio.Lock] = {}
        self._max_attempts = max_attempts

    async def sample(self, requests: Sequence[SamplingRequest]) -> list[SamplingResult]:
        return list(await asyncio.gather(*(self._sample_one(item) for item in requests)))

    async def _sample_one(self, item: SamplingRequest) -> SamplingResult:
        decision = check_sampling_policy(
            item.url,
            robots_allowed=item.robots_allowed,
            rate_limited=item.rate_limited,
            stop_requested=item.stop_requested,
        )
        if not decision.allowed or decision.normalized_url is None:
            return _blocked_result(item.url, decision)
        domain = urlparse(decision.normalized_url).hostname or ""
        lock = self._domain_locks.setdefault(domain, asyncio.Lock())
        async with lock:
            return await self._fetch_with_backoff(decision.normalized_url)

    async def _fetch_with_backoff(self, url: str) -> SamplingResult:
        last_status: int | None = None
        for attempt in range(1, self._max_attempts + 1):
            async with self._global_limit:
                response = await self._fetch_page(url)
            retry_after: float | None = None
            if isinstance(response, tuple):
                last_status, retry_after = response
            else:
                last_status = response
            if last_status not in {429, 503}:
                return SamplingResult(url, True, last_status, attempt, "请求完成")
            if attempt < self._max_attempts:
                await asyncio.sleep(max(0.0, min(retry_after or 0.0, 60.0)))
        return SamplingResult(url, False, last_status, self._max_attempts, "达到退避重试上限")


def _blocked_result(url: str, decision: SamplingPolicyDecision) -> SamplingResult:
    return SamplingResult(url, False, None, 0, f"{decision.code}: {decision.message}")
