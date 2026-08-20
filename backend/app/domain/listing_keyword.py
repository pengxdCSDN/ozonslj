"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

KeywordLayer = Literal["core", "attribute", "scene", "long_tail"]


@dataclass(frozen=True, slots=True)
class ListingKeyword:
    """说明 ListingKeyword 的职责、状态边界和对外协作关系。"""
    keyword: str
    source: str
    observed_at: datetime
    language: str
    layer: KeywordLayer
    product_scope: str


class ListingKeywordGateway(Protocol):
    """说明 ListingKeywordGateway 的职责、状态边界和对外协作关系。"""
    async def save_keyword(
        self, *, workspace_id: str, keyword: ListingKeyword
    ) -> ListingKeyword:
        """执行 save_keyword 的业务流程并返回该流程的结果。"""

    async def list_keywords(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[ListingKeyword]:
        """执行 list_keywords 的业务流程并返回该流程的结果。"""


class ListingKeywordError(ValueError):
    """Listing 关键词不符合来源和分层约束。"""


def normalize_listing_keyword(item: ListingKeyword) -> ListingKeyword:
    """执行 normalize_listing_keyword 的业务流程并返回该流程的结果。"""
    keyword = " ".join(item.keyword.split()).strip()
    if not keyword:
        raise ListingKeywordError("关键词不能为空")
    if not item.language or not item.product_scope or not item.source:
        raise ListingKeywordError("关键词必须包含来源、语言和适用商品范围")
    return ListingKeyword(
        keyword,
        item.source,
        item.observed_at,
        item.language.lower(),
        item.layer,
        item.product_scope,
    )
