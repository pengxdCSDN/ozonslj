from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ListingTitleDraft:
    title: str
    category: str
    covered_terms: tuple[str, ...]
    missing_terms: tuple[str, ...]
    character_count: int
    risks: tuple[str, ...]
    editable: bool = True


class ListingTitleDraftGateway(Protocol):
    async def save_draft(
        self, *, workspace_id: str, product_scope: str, draft: ListingTitleDraft
    ) -> ListingTitleDraft: ...

    async def list_drafts(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[ListingTitleDraft]: ...


def generate_russian_title(
    *,
    category: str,
    core_terms: list[str],
    attribute_terms: list[str],
    scene_terms: list[str],
    max_characters: int = 120,
) -> ListingTitleDraft:
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
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = " ".join(value.split()).strip()
        if normalized and normalized.casefold() not in seen:
            seen.add(normalized.casefold())
            result.append(normalized)
    return result
