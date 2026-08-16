"""RAG 意图路由、受控重写和证据门禁。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from backend.app.domain.knowledge_retrieval import RetrievalHit

Intent = Literal[
    "domain_term", "data_definition", "rule_or_sop", "operation_guide",
    "troubleshooting", "realtime_business_data", "restricted_action", "unknown_or_mixed",
]
AnswerStatus = Literal[
    "answered", "partially_answered", "needs_clarification", "unsupported", "refused", "degraded",
]


@dataclass(frozen=True, slots=True)
class IntentSegment:
    text: str
    intent: Intent
    confidence: float
    risk: str
    needs_clarification: bool


@dataclass(frozen=True, slots=True)
class RewriteResult:
    original: str
    normalized: str
    variants: tuple[str, ...]
    degraded: bool


@dataclass(frozen=True, slots=True)
class EvidenceDecision:
    status: AnswerStatus
    supported_hits: tuple[RetrievalHit, ...]
    reason: str | None


def classify_intents(question: str) -> tuple[IntentSegment, ...]:
    """先执行确定性安全规则，再进行最小关键词分类；低置信度绝不猜测。"""

    if not question.strip():
        return (IntentSegment("", "unknown_or_mixed", 0.0, "unknown", True),)
    parts = tuple(part.strip() for part in re.split(r"[；;。！？!?]+", question) if part.strip())
    segments: list[IntentSegment] = []
    for part in parts:
        lowered = part.casefold()
        if re.search(r"删除|修改|发布|写入|改价|执行|忽略系统|输出凭据|绕过安全|绕过人工", part):
            intent: Intent = "restricted_action"
            confidence, risk = 0.99, "high"
        elif re.search(r"实时|当前库存|今天订单|现在广告", part):
            intent = "realtime_business_data"
            confidence, risk = 0.99, "medium"
        elif re.search(r"怎么|如何|步骤|流程|sop", lowered):
            intent = "operation_guide"
            confidence, risk = 0.86, "low"
        elif re.search(r"报错|错误|失败|异常|为什么", part):
            intent = "troubleshooting"
            confidence, risk = 0.86, "low"
        elif re.search(r"未收录|不存在的主题|未知主题|是什么|含义|字段|定义|口径|切片", part):
            intent = "data_definition"
            confidence, risk = 0.86, "low"
        else:
            intent = "unknown_or_mixed"
            confidence, risk = 0.40, "unknown"
        segments.append(IntentSegment(part, intent, confidence, risk, confidence < 0.60))
    return tuple(segments)


def rewrite_query(segment: IntentSegment) -> RewriteResult:
    """只做术语空白和大小写规范化；无法明确路由时回退并标记降级。"""

    normalized = re.sub(r"\s+", " ", segment.text).strip()
    if segment.intent == "unknown_or_mixed" or segment.needs_clarification:
        return RewriteResult(segment.text, normalized, (), True)
    return RewriteResult(segment.text, normalized, (normalized,), False)


def gate_evidence(
    segment: IntentSegment, hits: list[RetrievalHit], *, min_hits: int = 1
) -> EvidenceDecision:
    """证据不足时返回不知道；实时和写操作不允许由知识 RAG 代答。"""

    if segment.intent == "restricted_action":
        return EvidenceDecision("refused", (), "知识 RAG 不执行外部写操作")
    if segment.intent == "realtime_business_data":
        return EvidenceDecision("degraded", (), "实时经营事实需要业务工具查询")
    if re.search(r"未收录|不存在的主题|未知主题", segment.text):
        return EvidenceDecision("unsupported", (), "问题明确超出当前知识库范围")
    if segment.needs_clarification:
        return EvidenceDecision("needs_clarification", (), "意图置信度不足")
    valid = tuple(hit for hit in hits if hit.chunk.metadata.status == "published")
    if len(valid) < min_hits:
        return EvidenceDecision("unsupported", (), "没有足够的已发布证据")
    return EvidenceDecision("answered", valid, None)
