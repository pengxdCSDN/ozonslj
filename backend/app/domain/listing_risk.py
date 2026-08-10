from dataclasses import dataclass
from typing import Literal, Protocol

RiskType = Literal["absolute", "medical", "brand", "certification"]


@dataclass(frozen=True, slots=True)
class ListingRiskFinding:
    risk_type: RiskType
    matched_text: str
    severity: Literal["warning", "error"]
    message: str
    suggestion: str


@dataclass(frozen=True, slots=True)
class ListingRiskReport:
    findings: tuple[ListingRiskFinding, ...]
    original_text: str
    safe_to_review: bool


class ListingRiskGateway(Protocol):
    async def save_report(
        self, *, workspace_id: str, product_scope: str, report: ListingRiskReport
    ) -> ListingRiskReport: ...

    async def list_reports(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[ListingRiskReport]: ...


def detect_listing_risks(
    text: str,
    *,
    authorized_brands: set[str] | None = None,
    verified_certifications: set[str] | None = None,
) -> ListingRiskReport:
    authorized_brands = {value.casefold() for value in (authorized_brands or set())}
    verified_certifications = {value.casefold() for value in (verified_certifications or set())}
    findings: list[ListingRiskFinding] = []
    _find_phrase(
        findings, text, ("лучший", "самый", "100%", "гарантированно"),
        "absolute", "绝对化表达需要人工确认", "改为可验证的客观描述",
    )
    _find_phrase(
        findings, text, ("лечит", "исцеляет", "лечебный", "без побочных эффектов"),
        "medical", "疑似疗效或医疗承诺", "删除疗效承诺并补充合规依据",
    )
    for brand in _tokens(text):
        if (
            brand.casefold() not in authorized_brands
            and brand.casefold() in {"apple", "nike", "adidas", "samsung"}
        ):
            findings.append(
                ListingRiskFinding(
                    "brand", brand, "error", "疑似未授权品牌词", "确认授权或移除品牌词"
                )
            )
    for certification in ("EAC", "GOST-R"):
        if (
            certification.casefold() in text.casefold()
            and certification.casefold() not in verified_certifications
        ):
            findings.append(
                ListingRiskFinding(
                    "certification", certification, "error",
                    "认证声明缺少验证记录", "补充证书依据后再使用",
                )
            )
    return ListingRiskReport(tuple(findings), text, True)


def _find_phrase(
    findings: list[ListingRiskFinding], text: str, phrases: tuple[str, ...],
    risk_type: RiskType, message: str, suggestion: str,
) -> None:
    folded = text.casefold()
    for phrase in phrases:
        if phrase.casefold() in folded:
            findings.append(
                ListingRiskFinding(
                    risk_type, phrase,
                    "error" if risk_type == "medical" else "warning",
                    message, suggestion,
                )
            )


def _tokens(text: str) -> list[str]:
    return [token.strip(".,;:!?()[]") for token in text.split() if token.strip()]
