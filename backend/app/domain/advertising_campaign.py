from dataclasses import dataclass
from typing import Literal, Protocol, cast

CampaignStatus = Literal["active", "paused", "archived"]


@dataclass(frozen=True, slots=True)
class AdvertisingKeyword:
    keyword: str
    bid_minor: int | None
    negative: bool


@dataclass(frozen=True, slots=True)
class AdvertisingCampaign:
    campaign_id: str
    name: str
    campaign_type: str
    status: CampaignStatus
    keywords: tuple[AdvertisingKeyword, ...]
    source: str = "performance_api"


class AdvertisingCampaignGateway(Protocol):
    async def save_campaigns(
        self, *, workspace_id: str, campaigns: list[AdvertisingCampaign]
    ) -> list[AdvertisingCampaign]: ...

    async def list_campaigns(
        self, *, workspace_id: str, limit: int
    ) -> list[AdvertisingCampaign]: ...


def map_performance_campaign(raw: dict[str, object]) -> AdvertisingCampaign:
    """把 Performance API 模型映射为内部只读模型，未知活动状态不静默转换。"""
    status = str(raw.get("status", "paused"))
    if status not in {"active", "paused", "archived"}:
        status = "paused"
    keywords: list[AdvertisingKeyword] = []
    raw_keywords = raw.get("keywords", [])
    for item in raw_keywords if isinstance(raw_keywords, list) else []:
        if isinstance(item, dict) and str(item.get("keyword", "")).strip():
            bid = item.get("bid_minor")
            if bid is not None and (not isinstance(bid, int) or isinstance(bid, bool) or bid < 0):
                raise ValueError("广告关键词出价必须是非负整数")
            keywords.append(
                AdvertisingKeyword(
                    str(item["keyword"]).strip(),
                    int(bid) if bid is not None else None,
                    bool(item.get("negative", False)),
                )
            )
    return AdvertisingCampaign(
        campaign_id=str(raw.get("campaign_id", "")),
        name=str(raw.get("name", "")),
        campaign_type=str(raw.get("campaign_type", "unknown")),
        status=cast(CampaignStatus, status), keywords=tuple(_dedupe_keywords(keywords)),
    )


def _dedupe_keywords(items: list[AdvertisingKeyword]) -> list[AdvertisingKeyword]:
    seen: set[tuple[str, bool]] = set()
    result: list[AdvertisingKeyword] = []
    for item in items:
        key = (item.keyword.casefold(), item.negative)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result
