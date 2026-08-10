from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SearchAttributeSuggestion:
    name: str
    suggested_value: str | None
    covered: bool
    source_term: str | None


@dataclass(frozen=True, slots=True)
class SearchAttributesReport:
    suggestions: tuple[SearchAttributeSuggestion, ...]
    coverage_percent: float
    missing_required: tuple[str, ...]
    editable: bool = True


class SearchAttributesGateway(Protocol):
    async def save_report(
        self, *, workspace_id: str, product_scope: str, report: SearchAttributesReport
    ) -> SearchAttributesReport: ...

    async def list_reports(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[SearchAttributesReport]: ...


def build_search_attributes(
    required: dict[str, str],
    current: dict[str, str],
    keyword_terms: dict[str, str] | None = None,
) -> SearchAttributesReport:
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
