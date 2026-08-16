"""知识问答目标 API 的安全最小实现；真实检索适配器接入前只返回路由计划。"""

from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.domain.knowledge_answer import classify_intents, rewrite_query
from backend.app.domain.knowledge_chunking import ChunkMetadata, KnowledgeChunk
from backend.app.domain.knowledge_query import KnowledgeQueryEngine
from backend.app.domain.knowledge_retrieval import (
    DeterministicEmbedding,
    InMemoryKeywordIndex,
    InMemoryVectorIndex,
)
from backend.app.domain.knowledge_runtime import (
    get_knowledge_runtime,
    resolve_knowledge_engine,
)

router = APIRouter(prefix="/v1/knowledge-answers", tags=["knowledge-rag"])


class KnowledgeQuestionPayload(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class KnowledgeTranslationPayload(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=50)


class KnowledgeTranslationResponse(BaseModel):
    texts: list[str]


class KnowledgeIntentResponse(BaseModel):
    text: str
    intent: str
    confidence: float
    risk: str
    needs_clarification: bool
    normalized_query: str
    degraded: bool


class KnowledgeQuestionResponse(BaseModel):
    answer_id: str | None = None
    trace_id: str | None = None
    status: str
    segments: list[KnowledgeIntentResponse]
    message: str


class KnowledgeCitationResponse(BaseModel):
    chunk_id: str
    source_locator: str
    title_path: list[str]
    score: float
    excerpt: str


class KnowledgeAnswerSegmentResponse(BaseModel):
    text: str
    intent: str
    status: str
    answer: str
    reason: str | None
    citations: list[KnowledgeCitationResponse]
    normalized_query: str


class KnowledgeAnswerResponse(BaseModel):
    answer_id: str
    trace_id: str
    status: str
    segments: list[KnowledgeAnswerSegmentResponse]
    message: str


class KnowledgeTraceResponse(BaseModel):
    trace_id: str
    answer_id: str
    question_hash: str
    status: str
    segment_count: int
    citation_count: int


_traces: dict[str, KnowledgeTraceResponse] = {}


class KnowledgeFeedbackPayload(BaseModel):
    reason: str = Field(
        pattern="^(helpful|incorrect|outdated_source|missing_answer|citation_mismatch)$"
    )
    note: str | None = Field(default=None, max_length=1000)


class KnowledgeFeedbackResponse(BaseModel):
    feedback_id: str
    answer_id: str
    reason: str
    status: str
    created_at: str


_feedback: dict[str, KnowledgeFeedbackResponse] = {}
_answers: set[str] = set()


async def _demo_engine() -> KnowledgeQueryEngine:
    """提供无外部凭据的演示索引；生产环境由 Chroma/PostgreSQL 适配器替换。"""

    embedding = DeterministicEmbedding()
    vector = InMemoryVectorIndex(dimension=embedding.dimension)
    keyword = InMemoryKeywordIndex()
    metadata = ChunkMetadata(
        document_id="demo-rag-document",
        document_version_id="demo-rag-version-1",
        business_domain="general",
        source_type="markdown",
        source_level="a",
        language="zh-CN",
        title_path=("RAG 使用说明",),
        source_locator="docs/rag/demo.md",
        chunk_strategy="markdown_section",
        chunk_strategy_version="1.0",
        status="published",
    )
    chunks = [KnowledgeChunk(
        chunk_id="demo-rag-chunk-001",
        content="知识型 RAG 只引用已发布知识片段；没有足够证据时必须明确回答不知道。",
        content_hash="demo-rag-hash-001",
        ordinal=0,
        metadata=metadata,
    )]
    await keyword.replace(chunks)
    await vector.upsert(chunks, await embedding.embed([chunk.content for chunk in chunks]))
    return KnowledgeQueryEngine(embedding=embedding, keyword_index=keyword, vector_index=vector)


@router.post("/plan", response_model=KnowledgeQuestionResponse)
async def build_knowledge_query_plan(
    payload: KnowledgeQuestionPayload,
) -> KnowledgeQuestionResponse:
    """生成受控意图/重写计划；未接入索引前不会伪造回答或引用。"""

    segments = classify_intents(payload.question)
    plans = [
        KnowledgeIntentResponse(
            text=segment.text,
            intent=segment.intent,
            confidence=segment.confidence,
            risk=segment.risk,
            needs_clarification=segment.needs_clarification,
            normalized_query=rewrite_query(segment).normalized,
            degraded=rewrite_query(segment).degraded,
        )
        for segment in segments
    ]
    status = "needs_clarification" if any(item.needs_clarification for item in plans) else "planned"
    return KnowledgeQuestionResponse(
        status=status,
        segments=plans,
        message="当前仅生成安全查询计划；知识索引和回答链路尚未接入。",
    )


@router.post("/query", response_model=KnowledgeAnswerResponse)
async def answer_knowledge_question(payload: KnowledgeQuestionPayload) -> KnowledgeAnswerResponse:
    """执行可审计的混合检索；无证据时返回不知道，不调用生成模型兜底编造。"""

    runtime = get_knowledge_runtime()
    # 本地测试保留演示知识，生产环境绝不使用演示内容作为回答兜底。
    engine = (
        await _demo_engine()
        if not runtime.persistent and not await runtime.has_published()
        else await resolve_knowledge_engine(runtime)
    )
    results = await engine.answer(payload.question)
    response_segments = [
        KnowledgeAnswerSegmentResponse(
            text=result.text,
            intent=result.intent,
            status=result.status,
            answer=result.answer,
            reason=result.reason,
            citations=[
                KnowledgeCitationResponse(
                    chunk_id=citation.chunk_id,
                    source_locator=citation.source_locator,
                    title_path=list(citation.title_path),
                    score=citation.score,
                    excerpt=citation.excerpt,
                )
                for citation in result.citations
            ],
            normalized_query=result.rewrite.normalized,
        )
        for result in results
    ]
    statuses = {segment.status for segment in response_segments}
    status = "answered" if statuses == {"answered"} else "partially_answered"
    if "needs_clarification" in statuses or "unsupported" in statuses:
        status = "needs_clarification" if "needs_clarification" in statuses else "unsupported"
    answer_id = str(uuid4())
    trace_id = str(uuid4())
    _answers.add(answer_id)
    _traces[trace_id] = KnowledgeTraceResponse(
        trace_id=trace_id, answer_id=answer_id,
        question_hash=sha256(payload.question.encode("utf-8")).hexdigest(),
        status=status, segment_count=len(response_segments),
        citation_count=sum(len(segment.citations) for segment in response_segments),
    )
    return KnowledgeAnswerResponse(
        answer_id=answer_id,
        trace_id=trace_id,
        status=status,
        segments=response_segments,
        message="回答仅基于已发布知识片段，并附带引用；实时数据和写操作不会由知识 RAG 代替。",
    )


@router.post("/translate", response_model=KnowledgeTranslationResponse)
async def translate_knowledge_text(
    payload: KnowledgeTranslationPayload,
) -> KnowledgeTranslationResponse:
    """调用 translation 用途绑定；生产环境失败时拒绝伪造译文。"""
    if any(not text.strip() for text in payload.texts):
        raise HTTPException(status_code=422, detail="翻译输入不能包含空文本")
    runtime = get_knowledge_runtime()
    try:
        translated = await runtime.translate(payload.texts)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return KnowledgeTranslationResponse(texts=translated)


@router.get("/{answer_id}/trace", response_model=KnowledgeTraceResponse)
async def get_knowledge_answer_trace(answer_id: str) -> KnowledgeTraceResponse:
    for trace in _traces.values():
        if trace.answer_id == answer_id:
            return trace
    raise HTTPException(status_code=404, detail="回答追踪不存在或已过期")


@router.get("/history", response_model=list[KnowledgeTraceResponse])
async def list_knowledge_answer_history() -> list[KnowledgeTraceResponse]:
    return list(_traces.values())


@router.post("/{answer_id}/feedback", response_model=KnowledgeFeedbackResponse, status_code=201)
async def create_knowledge_feedback(
    answer_id: str, payload: KnowledgeFeedbackPayload
) -> KnowledgeFeedbackResponse:
    if answer_id not in _answers:
        raise HTTPException(status_code=404, detail="回答不存在或已过期")
    feedback = KnowledgeFeedbackResponse(
        feedback_id=str(uuid4()), answer_id=answer_id, reason=payload.reason,
        status="open", created_at=datetime.now(UTC).isoformat(),
    )
    _feedback[feedback.feedback_id] = feedback
    return feedback


@router.get("/feedback", response_model=list[KnowledgeFeedbackResponse])
async def list_knowledge_feedback() -> list[KnowledgeFeedbackResponse]:
    return list(_feedback.values())
