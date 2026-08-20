"""可执行的知识问答编排：检索、证据门禁和引用输出必须在同一条链路完成。"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

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
    """说明 KnowledgeSegmentAnswer 的职责、状态边界和对外协作关系。"""
    text: str
    intent: str
    status: str
    answer: str
    reason: str | None
    citations: tuple[KnowledgeCitation, ...]
    rewrite: RewriteResult


class RerankerPort(Protocol):
    """说明 RerankerPort 的职责、状态边界和对外协作关系。"""
    async def rerank(self, query: str, hits: list[RetrievalHit]) -> list[RetrievalHit]:
        """执行 rerank 的业务流程并返回该流程的结果。

Args:
    query: 参数语义、输入边界和安全约束。
    hits: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


class AnswerGeneratorPort(Protocol):
    """说明 AnswerGeneratorPort 的职责、状态边界和对外协作关系。"""
    async def generate(
        self, question: str, evidence: tuple[KnowledgeCitation, ...]
    ) -> str | None:
        """执行 generate 的业务流程并返回该流程的结果。

Args:
    question: 参数语义、输入边界和安全约束。
    evidence: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


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
        reranker: RerankerPort | None = None,
        answer_generator: AnswerGeneratorPort | None = None,
    ) -> None:
        """初始化对象依赖和运行时状态。

Args:
    embedding: 参数语义、输入边界和安全约束。
    keyword_index: 参数语义、输入边界和安全约束。
    vector_index: 参数语义、输入边界和安全约束。
    reranker: 参数语义、输入边界和安全约束。
    answer_generator: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._embedding = embedding
        self._keyword_index = keyword_index
        self._vector_index = vector_index
        self._reranker = reranker
        self._answer_generator = answer_generator

    async def answer(self, question: str, *, limit: int = 5) -> tuple[KnowledgeSegmentAnswer, ...]:
        """执行 answer 的业务流程并返回该流程的结果。

Args:
    question: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        results: list[KnowledgeSegmentAnswer] = []
        for segment in classify_intents(question):
            rewritten = rewrite_query(segment)
            chain_error: str | None = None
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
            if self._reranker is not None and hits:
                try:
                    hits = await self._reranker.rerank(rewritten.normalized, hits)
                    decision = gate_evidence(segment, hits)
                except (RuntimeError, TimeoutError, ValueError):
                    # 重排只改善排序，失败时保留混合召回结果，不能让问答整体中断。
                    chain_error = "reranker_unavailable"
            result = _to_answer(segment, rewritten, decision)
            if self._answer_generator is not None and result.status == "answered":
                try:
                    generated = await self._answer_generator.generate(
                        segment.text, result.citations
                    )
                except (RuntimeError, TimeoutError, ValueError):
                    generated = None
                    chain_error = "text_model_unavailable"
                if generated:
                    result = KnowledgeSegmentAnswer(
                        text=result.text, intent=result.intent, status=result.status,
                        answer=generated, reason=result.reason, citations=result.citations,
                        rewrite=result.rewrite,
                    )
            if chain_error is not None and result.status == "answered":
                # 普通问答保留证据摘录作为安全降级，但将链路故障编码到 reason，
                # 供正式质量评测拒绝把降级答案当作模型调用成功。
                result = replace(result, reason=chain_error)
            results.append(result)
        return tuple(results)


def _to_answer(
    segment: IntentSegment,
    rewritten: RewriteResult,
    decision: EvidenceDecision,
) -> KnowledgeSegmentAnswer:
    """执行内部步骤 _to_answer，供同一模块的公开流程复用。

Args:
    segment: 参数语义、输入边界和安全约束。
    rewritten: 参数语义、输入边界和安全约束。
    decision: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
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
    """执行内部步骤 _citation，供同一模块的公开流程复用。

Args:
    hit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return KnowledgeCitation(
        chunk_id=hit.chunk.chunk_id,
        source_locator=hit.chunk.metadata.source_locator,
        title_path=hit.chunk.metadata.title_path,
        score=round(hit.score, 6),
        excerpt=hit.chunk.content[:500],
    )
