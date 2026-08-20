"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ListingTitleDraft:
    """说明 ListingTitleDraft 的职责、状态边界和对外协作关系。"""
    title: str
    category: str
    covered_terms: tuple[str, ...]
    missing_terms: tuple[str, ...]
    character_count: int
    risks: tuple[str, ...]
    editable: bool = True


class ListingTitleDraftGateway(Protocol):
    """说明 ListingTitleDraftGateway 的职责、状态边界和对外协作关系。"""
    async def save_draft(
        self, *, workspace_id: str, product_scope: str, draft: ListingTitleDraft
    ) -> ListingTitleDraft:
        """执行 save_draft 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    product_scope: 参数语义、输入边界和安全约束。
    draft: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def list_drafts(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[ListingTitleDraft]:
        """执行 list_drafts 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


def generate_russian_title(
    *,
    category: str,
    core_terms: list[str],
    attribute_terms: list[str],
    scene_terms: list[str],
    max_characters: int = 120,
) -> ListingTitleDraft:
    """执行 generate_russian_title 的业务流程并返回该流程的结果。

Args:
    category: 参数语义、输入边界和安全约束。
    core_terms: 参数语义、输入边界和安全约束。
    attribute_terms: 参数语义、输入边界和安全约束。
    scene_terms: 参数语义、输入边界和安全约束。
    max_characters: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    if max_characters < 1:
        raise ValueError("标题最大长度必须为正数")
    terms = _unique(core_terms + attribute_terms + scene_terms)
    raw_title = " ".join(terms).strip()
    title = raw_title[:max_characters].strip()
    covered = tuple(term for term in terms if term.casefold() in title.casefold())
    missing = tuple(term for term in terms if term not in covered)
    risks: list[str] = []
    if len(raw_title) > max_characters:
        risks.append("标题超过长度限制")
    if not core_terms:
        risks.append("缺少核心词")
    if category.strip() == "":
        risks.append("缺少类目")
    return ListingTitleDraft(title, category, covered, missing, len(title), tuple(risks))


def _unique(values: list[str]) -> list[str]:
    """执行内部步骤 _unique，供同一模块的公开流程复用。

Args:
    values: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = " ".join(value.split()).strip()
        if normalized and normalized.casefold() not in seen:
            seen.add(normalized.casefold())
            result.append(normalized)
    return result
