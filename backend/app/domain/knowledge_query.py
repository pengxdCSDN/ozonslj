"""可执行的知识问答编排：检索、证据门禁和引用输出必须在同一条链路完成。"""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.domain.knowledge_answer import (
    EvidenceDecision,
    IntentSegment,
    RewriteResult,
    classify_intents,
    gate_evidence,
    rewrite_query,
)
from backend.app.domain.knowledge_retrieval import (
    EmbeddingPort,
    KeywordSearchPort,
    RetrievalHit,
    VectorIndexPort,
    hybrid_retrieve,
)


@dataclass(frozen=True, slots=True)
class KnowledgeCitation:
    """回答引用的最小可审计信息，不返回原始敏感文档。"""

    chunk_id: str
    source_locator: str
    title_path: tuple[str, ...]
    score: float
    excerpt: str


@dataclass(frozen=True, slots=True)
class KnowledgeSegmentAnswer:
    text: str
    intent: str
    status: str
    answer: str
    reason: str | None
    citations: tuple[KnowledgeCitation, ...]
    rewrite: RewriteResult


class KnowledgeQueryEngine:
    """知识型混合 RAG 引擎。

    该引擎采用抽取式回答作为基础闭环，后续可把 answer 端口替换为
    LangChain Runnable；证据门禁仍在模型调用之前执行，避免无证据幻觉。
    """

    def __init__(
        self,
        *,
        embedding: EmbeddingPort,
        keyword_index: KeywordSearchPort,
        vector_index: VectorIndexPort,
    ) -> None:
        self._embedding = embedding
        self._keyword_index = keyword_index
        self._vector_index = vector_index

    async def answer(self, question: str, *, limit: int = 5) -> tuple[KnowledgeSegmentAnswer, ...]:
        results: list[KnowledgeSegmentAnswer] = []
        for segment in classify_intents(question):
            rewritten = rewrite_query(segment)
            hits = (
                await hybrid_retrieve(
                    rewritten.normalized,
                    embedding=self._embedding,
                    keyword_index=self._keyword_index,
                    vector_index=self._vector_index,
                    limit=limit,
                )
                if not rewritten.degraded
                else []
            )
            decision = gate_evidence(segment, hits)
            results.append(_to_answer(segment, rewritten, decision))
        return tuple(results)


def _to_answer(
    segment: IntentSegment,
    rewritten: RewriteResult,
    decision: EvidenceDecision,
) -> KnowledgeSegmentAnswer:
    citations = tuple(_citation(hit) for hit in decision.supported_hits)
    if decision.status == "answered" and citations:
        answer = citations[0].excerpt
    elif decision.status == "refused":
        answer = "该请求涉及受控写入或外部操作，知识问答不会代替人工审批执行。"
    elif decision.status == "degraded":
        answer = "这是实时业务问题，当前知识库不能提供可靠结论，请改用实时业务查询。"
    elif decision.status == "needs_clarification":
        answer = "我无法确定你的具体意图，请补充业务对象、时间范围或期望动作。"
    else:
        answer = "当前知识库没有足够证据回答这个问题，我不知道。"
    return KnowledgeSegmentAnswer(
        text=segment.text,
        intent=segment.intent,
        status=decision.status,
        answer=answer,
        reason=decision.reason,
        citations=citations,
        rewrite=rewritten,
    )


def _citation(hit: RetrievalHit) -> KnowledgeCitation:
    return KnowledgeCitation(
        chunk_id=hit.chunk.chunk_id,
        source_locator=hit.chunk.metadata.source_locator,
        title_path=hit.chunk.metadata.title_path,
        score=round(hit.score, 6),
        excerpt=hit.chunk.content[:500],
    )
