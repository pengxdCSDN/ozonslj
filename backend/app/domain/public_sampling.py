"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from urllib.parse import urlparse

from backend.app.domain.sampling_policy import SamplingPolicyDecision, check_sampling_policy


@dataclass(frozen=True, slots=True)
class SamplingRequest:
    """说明 SamplingRequest 的职责、状态边界和对外协作关系。"""
    url: str
    robots_allowed: bool = True
    rate_limited: bool = False
    stop_requested: bool = False


@dataclass(frozen=True, slots=True)
class SamplingResult:
    """说明 SamplingResult 的职责、状态边界和对外协作关系。"""
    url: str
    allowed: bool
    status_code: int | None
    attempts: int
    message: str


@dataclass(frozen=True, slots=True)
class FetchResponse:
    """页面适配器结果；策略阻断必须在发送页面请求前显式返回。"""

    status_code: int | None
    allowed: bool = True
    message: str = "请求完成"


FetchPage = Callable[[str], Awaitable[int | tuple[int, float | None] | FetchResponse]]


class PublicSampler:
    """执行受控公开采样：全局最多 2 个请求，单域名始终串行。"""

    def __init__(
        self, fetch_page: FetchPage, *, global_limit: int = 2, max_attempts: int = 3
    ) -> None:
        """初始化对象依赖和运行时状态。

Args:
    fetch_page: 参数语义、输入边界和安全约束。
    global_limit: 参数语义、输入边界和安全约束。
    max_attempts: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
        if global_limit < 1 or max_attempts < 1:
            raise ValueError("采样并发和重试次数必须为正数")
        self._fetch_page = fetch_page
        self._global_limit = asyncio.Semaphore(global_limit)
        self._domain_locks: dict[str, asyncio.Lock] = {}
        self._max_attempts = max_attempts

    async def sample(self, requests: Sequence[SamplingRequest]) -> list[SamplingResult]:
        """执行 sample 的业务流程并返回该流程的结果。

Args:
    requests: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        return list(await asyncio.gather(*(self._sample_one(item) for item in requests)))

    async def _sample_one(self, item: SamplingRequest) -> SamplingResult:
        """执行内部步骤 _sample_one，供同一模块的公开流程复用。

Args:
    item: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
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
        """执行内部步骤 _fetch_with_backoff，供同一模块的公开流程复用。

Args:
    url: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        last_status: int | None = None
        for attempt in range(1, self._max_attempts + 1):
            async with self._global_limit:
                response = await self._fetch_page(url)
            if isinstance(response, FetchResponse) and not response.allowed:
                return SamplingResult(
                    url, False, response.status_code, attempt, response.message
                )
            retry_after: float | None = None
            if isinstance(response, FetchResponse):
                last_status = response.status_code
            elif isinstance(response, tuple):
                last_status, retry_after = response
            else:
                last_status = response
            if last_status not in {429, 503}:
                return SamplingResult(url, True, last_status, attempt, "请求完成")
            if attempt < self._max_attempts:
                await asyncio.sleep(max(0.0, min(retry_after or 0.0, 60.0)))
        return SamplingResult(url, False, last_status, self._max_attempts, "达到退避重试上限")


def _blocked_result(url: str, decision: SamplingPolicyDecision) -> SamplingResult:
    """执行内部步骤 _blocked_result，供同一模块的公开流程复用。

Args:
    url: 参数语义、输入边界和安全约束。
    decision: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return SamplingResult(url, False, None, 0, f"{decision.code}: {decision.message}")
