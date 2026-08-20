"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ExpandInput:
    """说明 ExpandInput 的职责、状态边界和对外协作关系。"""
    seed_product: str
    core_keywords: tuple[str, ...]
    related_keywords: tuple[str, ...]
    attributes: tuple[str, ...]
    scenes: tuple[str, ...]
    variants: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExpandResult:
    """说明 ExpandResult 的职责、状态边界和对外协作关系。"""
    seed_product: str
    core_terms: tuple[str, ...]
    attribute_terms: tuple[str, ...]
    scene_terms: tuple[str, ...]
    variant_candidates: tuple[str, ...]
    estimated: bool
    missing_inputs: tuple[str, ...]


class ExpandResultGateway(Protocol):
    """说明 ExpandResultGateway 的职责、状态边界和对外协作关系。"""
    async def save_expansion(self, *, workspace_id: str, result: ExpandResult) -> ExpandResult:
        """执行 save_expansion 的业务流程并返回该流程的结果。"""

    async def list_expansions(
        self, *, workspace_id: str, limit: int
    ) -> list[ExpandResult]:
        """执行 list_expansions 的业务流程并返回该流程的结果。"""


def expand_product(item: ExpandInput) -> ExpandResult:
    """对输入词去重并分层，结果仅作为进入 Validate 的候选，不自动上架。"""
    if not item.seed_product.strip():
        raise ValueError("扩展必须包含种子商品")
    core = _unique(item.core_keywords + item.related_keywords)
    variants = _unique(
        item.variants
        or tuple(f"{item.seed_product} {attribute}" for attribute in item.attributes)
    )
    missing = tuple(
        field
        for field, values in (
            ("core_keywords", core),
            ("attributes", item.attributes),
            ("scenes", item.scenes),
        )
        if not values
    )
    return ExpandResult(
        seed_product=item.seed_product,
        core_terms=core,
        attribute_terms=_unique(item.attributes),
        scene_terms=_unique(item.scenes),
        variant_candidates=variants,
        estimated=True,
        missing_inputs=missing,
    )


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    """执行内部步骤 _unique，供同一模块的公开流程复用。"""
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        normalized = " ".join(value.split()).strip()
        key = normalized.casefold()
        if normalized and key not in seen:
            seen.add(key)
            output.append(normalized)
    return tuple(output)
