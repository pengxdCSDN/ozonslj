from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class FabePoint:
    feature: str
    advantage: str
    benefit: str
    evidence: str | None
    copy: str


@dataclass(frozen=True, slots=True)
class ListingFabeDraft:
    bullets: tuple[FabePoint, ...]
    long_description: str
    image_copy_suggestions: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    editable: bool = True


class ListingFabeGateway(Protocol):
    async def save_draft(
        self, *, workspace_id: str, product_scope: str, draft: ListingFabeDraft
    ) -> ListingFabeDraft: ...

    async def list_drafts(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[ListingFabeDraft]: ...


def generate_fabe_draft(points: list[FabePoint], *, product_name: str) -> ListingFabeDraft:
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
