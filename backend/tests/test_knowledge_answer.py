from backend.app.domain.knowledge_answer import classify_intents, gate_evidence, rewrite_query
from backend.app.domain.knowledge_chunking import ChunkMetadata, KnowledgeChunk
from backend.app.domain.knowledge_retrieval import RetrievalHit


def _hit(status: str = "published") -> RetrievalHit:
    metadata = ChunkMetadata(
        document_id="d", document_version_id="v", business_domain="requirements",
        source_type="markdown", source_level="b", language="zh-CN", title_path=("RAG",),
        source_locator="docs/rag.md",
        chunk_strategy="markdown_sections",
        chunk_strategy_version="1",
        status=status,  # type: ignore[arg-type]
    )
    chunk = KnowledgeChunk("c", "已发布证据", "h", 0, metadata)
    return RetrievalHit(chunk, 1.0, "keyword")


def test_multiple_intents_are_segmented_and_unsafe_ones_refused() -> None:
    segments = classify_intents("什么是切片？如何发布？")
    assert len(segments) == 2
    assert segments[0].intent == "data_definition"
    assert segments[1].intent == "restricted_action"
    assert rewrite_query(segments[0]).degraded is False
    unsafe = classify_intents("删除这个版本")[0]
    assert gate_evidence(unsafe, [_hit()]).status == "refused"


def test_unknown_and_realtime_are_not_guessed() -> None:
    unknown = classify_intents("帮我看看这个")[0]
    assert gate_evidence(unknown, [_hit()]).status == "needs_clarification"
    realtime = classify_intents("当前库存是多少")[0]
    assert gate_evidence(realtime, [_hit()]).status == "degraded"


def test_evidence_gate_rejects_unpublished_and_accepts_published() -> None:
    segment = classify_intents("字段是什么意思")[0]
    assert gate_evidence(segment, [_hit("draft")]).status == "unsupported"
    decision = gate_evidence(segment, [_hit()])
    assert decision.status == "answered"
    assert len(decision.supported_hits) == 1
