"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Literal, Protocol

SmartSearchSeverity = Literal["warning", "error"]


@dataclass(frozen=True, slots=True)
class SmartSearchFinding:
    """说明 SmartSearchFinding 的职责、状态边界和对外协作关系。"""
    code: str
    severity: SmartSearchSeverity
    message: str
    suggestion: str


@dataclass(frozen=True, slots=True)
class SmartSearchReport:
    """说明 SmartSearchReport 的职责、状态边界和对外协作关系。"""
    findings: tuple[SmartSearchFinding, ...]
    covered_terms: tuple[str, ...]
    missing_terms: tuple[str, ...]
    valid: bool
    original_text_preserved: bool = True


class SmartSearchGateway(Protocol):
    """说明 SmartSearchGateway 的职责、状态边界和对外协作关系。"""
    async def save_report(
        self, *, workspace_id: str, product_scope: str, source_text: str,
        report: SmartSearchReport
    ) -> SmartSearchReport:
        """执行 save_report 的业务流程并返回该流程的结果。"""

    async def list_reports(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[SmartSearchReport]:
        """执行 list_reports 的业务流程并返回该流程的结果。"""


def check_smart_search(
    text: str,
    *,
    required_terms: list[str],
    category: str,
    category_terms: list[str] | None = None,
) -> SmartSearchReport:
    """执行 check_smart_search 的业务流程并返回该流程的结果。"""
    if not text.strip():
        return SmartSearchReport(
            (
                SmartSearchFinding(
                    "LST-EMPTY", "error", "Listing 文本不能为空", "补充原始 Listing 文本"
                ),
            ),
            (),
            tuple(_unique(required_terms)),
            False,
        )
    folded = text.casefold()
    terms = _unique(required_terms)
    covered = tuple(term for term in terms if term.casefold() in folded)
    missing = tuple(term for term in terms if term not in covered)
    findings: list[SmartSearchFinding] = []
    if missing:
        findings.append(
            SmartSearchFinding(
                "LST-COVERAGE", "warning", "存在未覆盖关键词", f"补充：{'、'.join(missing)}"
            )
        )
    repeated = [term for term in terms if folded.count(term.casefold()) > 2]
    if repeated:
        findings.append(
            SmartSearchFinding(
                "LST-REPEAT", "warning", "关键词重复次数较高", f"减少重复：{'、'.join(repeated)}"
            )
        )
    token_count = len(text.split())
    if token_count and len(set(text.casefold().split())) / token_count < 0.45:
        findings.append(
            SmartSearchFinding(
                "LST-STUFFING", "error", "文本疑似关键词堆砌", "改用自然俄语句子表达"
            )
        )
    if category_terms and category and not any(
        term.casefold() in folded for term in category_terms
    ):
        findings.append(
            SmartSearchFinding(
                "LST-CATEGORY", "warning", "标题与类目关键词一致性不足", f"确认类目：{category}"
            )
        )
    return SmartSearchReport(
        tuple(findings), covered, missing,
        not any(item.severity == "error" for item in findings),
    )


def _unique(values: list[str]) -> list[str]:
    """执行内部步骤 _unique，供同一模块的公开流程复用。"""
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = " ".join(value.split()).strip()
        if normalized and normalized.casefold() not in seen:
            seen.add(normalized.casefold())
            result.append(normalized)
    return result
