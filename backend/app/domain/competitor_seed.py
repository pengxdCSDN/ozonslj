from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class CompetitorSeed:
    id: str
    workspace_id: str
    url: str
    title: str | None
    status: str


class CompetitorSeedGateway(Protocol):
    async def create_seed(self, *, workspace_id: str, url: str) -> CompetitorSeed: ...

    async def list_seeds(self, *, workspace_id: str) -> list[CompetitorSeed]: ...

    async def update_status(self, *, seed_id: str, status: str) -> CompetitorSeed | None: ...


class CompetitorSeedError(ValueError):
    """竞品种子不符合受控公开采样边界。"""


def validate_competitor_seed_url(url: str) -> str:
    """只接受公开 HTTPS 页面，拒绝凭据、查询注入和非网页协议。"""

    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or not parsed.hostname:
        raise CompetitorSeedError("竞品种子必须是公开 HTTPS URL")
    if parsed.username or parsed.password:
        raise CompetitorSeedError("竞品 URL 不得包含登录凭据")
    if parsed.fragment:
        raise CompetitorSeedError("竞品 URL 不得包含 fragment")
    return parsed._replace(query="", fragment="").geturl()
