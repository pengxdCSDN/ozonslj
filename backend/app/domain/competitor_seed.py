"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class CompetitorSeed:
    """说明 CompetitorSeed 的职责、状态边界和对外协作关系。"""
    id: str
    workspace_id: str
    url: str
    title: str | None
    status: str


class CompetitorSeedGateway(Protocol):
    """说明 CompetitorSeedGateway 的职责、状态边界和对外协作关系。"""
    async def create_seed(self, *, workspace_id: str, url: str) -> CompetitorSeed:
        """执行 create_seed 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    url: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def list_seeds(self, *, workspace_id: str) -> list[CompetitorSeed]:
        """执行 list_seeds 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def update_status(self, *, seed_id: str, status: str) -> CompetitorSeed | None:
        """执行 update_status 的业务流程并返回该流程的结果。

Args:
    seed_id: 参数语义、输入边界和安全约束。
    status: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


class CompetitorSeedError(ValueError):
    """竞品种子不符合受控公开采样边界。"""


def validate_competitor_seed_url(url: str) -> str:
    """只接受公开 HTTPS 页面，拒绝凭据、查询注入和非网页协议。

Args:
    url: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    CompetitorSeedError: 业务约束或外部依赖失败时抛出。
"""

    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or not parsed.hostname:
        raise CompetitorSeedError("竞品种子必须是公开 HTTPS URL")
    if parsed.username or parsed.password:
        raise CompetitorSeedError("竞品 URL 不得包含登录凭据")
    if parsed.fragment:
        raise CompetitorSeedError("竞品 URL 不得包含 fragment")
    return parsed._replace(query="", fragment="").geturl()
