"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class FabePoint:
    """说明 FabePoint 的职责、状态边界和对外协作关系。"""
    feature: str
    advantage: str
    benefit: str
    evidence: str | None
    copy: str


@dataclass(frozen=True, slots=True)
class ListingFabeDraft:
    """说明 ListingFabeDraft 的职责、状态边界和对外协作关系。"""
    bullets: tuple[FabePoint, ...]
    long_description: str
    image_copy_suggestions: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    editable: bool = True


class ListingFabeGateway(Protocol):
    """说明 ListingFabeGateway 的职责、状态边界和对外协作关系。"""
    async def save_draft(
        self, *, workspace_id: str, product_scope: str, draft: ListingFabeDraft
    ) -> ListingFabeDraft:
        """执行 save_draft 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    product_scope: 参数语义、输入边界和安全约束。
    draft: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def list_drafts(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[ListingFabeDraft]:
        """执行 list_drafts 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


def generate_fabe_draft(points: list[FabePoint], *, product_name: str) -> ListingFabeDraft:
    """执行 generate_fabe_draft 的业务流程并返回该流程的结果。

Args:
    points: 参数语义、输入边界和安全约束。
    product_name: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    if not product_name.strip():
        raise ValueError("FABE 草稿必须包含商品名称")
    normalized = tuple(
        FabePoint(
            point.feature.strip(),
            point.advantage.strip(),
            point.benefit.strip(),
            point.evidence,
            point.copy.strip(),
        )
        for point in points
        if point.feature.strip() and point.advantage.strip() and point.benefit.strip()
    )
    bullets = tuple(point for point in normalized if point.copy)
    paragraphs = [product_name.strip(), *[point.copy for point in bullets]]
    long_description = "\n\n".join(paragraphs)
    if len(long_description) > 5000:
        raise ValueError("FABE 长描述不得超过 5000 个字符")
    missing = tuple(point.feature for point in normalized if not point.evidence)
    images = tuple(f"展示 {point.feature}：{point.benefit}" for point in normalized[:5])
    return ListingFabeDraft(bullets, long_description, images, missing)
