"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Literal, Protocol

KeywordLayer = Literal["core", "attribute", "scene", "long_tail"]


@dataclass(frozen=True, slots=True)
class LayeredKeyword:
    """说明 LayeredKeyword 的职责、状态边界和对外协作关系。"""
    keyword: str
    layer: KeywordLayer
    reason: str
    manually_confirmed: bool


class ListingLayerGateway(Protocol):
    """说明 ListingLayerGateway 的职责、状态边界和对外协作关系。"""
    async def save_layers(
        self, *, workspace_id: str, layers: list[LayeredKeyword]
    ) -> list[LayeredKeyword]:
        """执行 save_layers 的业务流程并返回该流程的结果。"""

    async def list_layers(self, *, workspace_id: str, limit: int = 50) -> list[LayeredKeyword]:
        """执行 list_layers 的业务流程并返回该流程的结果。"""


def classify_listing_keywords(
    keywords: list[str],
    *,
    core_terms: set[str] | None = None,
    attribute_terms: set[str] | None = None,
    scene_terms: set[str] | None = None,
) -> list[LayeredKeyword]:
    """按人工词表优先、词形特征其次分层；结果始终可人工复核。"""
    core_terms = {term.casefold() for term in (core_terms or set())}
    attribute_terms = {term.casefold() for term in (attribute_terms or set())}
    scene_terms = {term.casefold() for term in (scene_terms or set())}
    result: list[LayeredKeyword] = []
    for keyword in _unique(keywords):
        folded = keyword.casefold()
        if folded in core_terms:
            layer: KeywordLayer = "core"
            reason, confirmed = "人工核心词表", True
        elif folded in attribute_terms:
            layer = "attribute"
            reason, confirmed = "人工属性词表", True
        elif folded in scene_terms:
            layer = "scene"
            reason, confirmed = "人工场景词表", True
        elif len(keyword.split()) >= 4:
            layer = "long_tail"
            reason, confirmed = "词组长度达到长尾规则", False
        else:
            layer = "core"
            reason, confirmed = "默认作为核心词候选", False
        result.append(LayeredKeyword(keyword, layer, reason, confirmed))
    return result


def _unique(values: list[str]) -> list[str]:
    """执行内部步骤 _unique，供同一模块的公开流程复用。"""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = " ".join(value.split()).strip()
        if normalized and normalized.casefold() not in seen:
            seen.add(normalized.casefold())
            result.append(normalized)
    return result
