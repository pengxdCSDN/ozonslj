"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SearchAttributeSuggestion:
    """说明 SearchAttributeSuggestion 的职责、状态边界和对外协作关系。"""
    name: str
    suggested_value: str | None
    covered: bool
    source_term: str | None


@dataclass(frozen=True, slots=True)
class SearchAttributesReport:
    """说明 SearchAttributesReport 的职责、状态边界和对外协作关系。"""
    suggestions: tuple[SearchAttributeSuggestion, ...]
    coverage_percent: float
    missing_required: tuple[str, ...]
    editable: bool = True


class SearchAttributesGateway(Protocol):
    """说明 SearchAttributesGateway 的职责、状态边界和对外协作关系。"""
    async def save_report(
        self, *, workspace_id: str, product_scope: str, report: SearchAttributesReport
    ) -> SearchAttributesReport:
        """执行 save_report 的业务流程并返回该流程的结果。"""

    async def list_reports(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[SearchAttributesReport]:
        """执行 list_reports 的业务流程并返回该流程的结果。"""


def build_search_attributes(
    required: dict[str, str],
    current: dict[str, str],
    keyword_terms: dict[str, str] | None = None,
) -> SearchAttributesReport:
    """执行 build_search_attributes 的业务流程并返回该流程的结果。"""
    if any(not name.strip() for name in required):
        raise ValueError("Search Attributes 必填属性名不能为空")
    keyword_terms = keyword_terms or {}
    suggestions: list[SearchAttributeSuggestion] = []
    for name, _expected in required.items():
        value = (current.get(name) or keyword_terms.get(name) or "").strip() or None
        suggestions.append(
            SearchAttributeSuggestion(
                name, value, bool(value), name if name in keyword_terms else None
            )
        )
    covered = sum(item.covered for item in suggestions)
    return SearchAttributesReport(
        tuple(suggestions),
        round(covered / len(suggestions) * 100, 2) if suggestions else 100.0,
        tuple(item.name for item in suggestions if not item.covered),
    )
