import pytest

from backend.app.domain.knowledge_chunking import ChunkMetadata, KnowledgeChunk
from backend.app.domain.knowledge_runtime import KnowledgeRuntimeIndex
from backend.app.domain.rag_evaluation_corpus import fixed_evaluation_corpus
from backend.app.domain.rag_quality_runner import classify_evaluation_error, run_fixed_quality_suite
from backend.app.infrastructure.cloud_models import (
    CloudModelNotFoundError,
    CloudModelQuotaError,
    CloudModelTimeoutError,
)


def _chunk(case_id: str, question: str) -> KnowledgeChunk:
    suffix = case_id.removeprefix("fixed-rag-v2-")
    return KnowledgeChunk(
        chunk_id=f"gold-{suffix}",
        content=question + " 这是经过人工确认的评测证据。",
        content_hash=case_id.ljust(64, "0")[:64],
        ordinal=0,
        metadata=ChunkMetadata(
            document_id="quality-fixture",
            document_version_id="quality-fixture-v1",
            business_domain="general",
            source_type="markdown",
            source_level="a",
            language="zh-CN",
            title_path=("固定评测语料",),
            source_locator="quality-fixture.md",
            chunk_strategy="fixture",
            chunk_strategy_version="1",
            status="draft",
        ),
    )


async def _engine_with_fixed_evidence() -> KnowledgeRuntimeIndex:
    runtime = KnowledgeRuntimeIndex()
    cases = fixed_evaluation_corpus()
    chunks = []
    for case in cases:
        chunks.extend(
            _chunk(chunk_id.replace("gold-", "fixed-rag-v2-"), case.question)
            for chunk_id in case.expected_chunk_ids
        )
    runtime.stage("quality-fixture-v1", tuple(chunks))
    # 评测夹具只用于验证执行器串联，不代表生产知识库内容。
    await runtime.publish("quality-fixture-v1")
    return runtime


@pytest.mark.asyncio
@pytest.mark.parametrize(("suite", "target"), [("quick", 30), ("standard", 120), ("full", 240)])
async def test_fixed_quality_runner_executes_all_fixed_cases(suite: str, target: int) -> None:
    runtime = await _engine_with_fixed_evidence()
    report = await run_fixed_quality_suite(runtime.engine(), suite)  # type: ignore[arg-type]

    assert report.target_count == target
    assert report.executed_count == target
    assert report.error_count == 0
    assert report.status == "completed"
    assert report.metrics.average_latency_ms >= 0


@pytest.mark.asyncio
async def test_fixed_quality_runner_rejects_large_batches() -> None:
    runtime = await _engine_with_fixed_evidence()
    with pytest.raises(ValueError, match="1 到 10"):
        await run_fixed_quality_suite(runtime.engine(), "quick", batch_size=11)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_fixed_quality_fixture_retrieves_expected_chunks() -> None:
    runtime = await _engine_with_fixed_evidence()
    case = fixed_evaluation_corpus()[160]
    answers = await runtime.engine().answer(case.question, limit=10)
    citations = tuple(citation.chunk_id for answer in answers for citation in answer.citations)
    assert case.expected_chunk_ids, case.case_id
    assert set(case.expected_chunk_ids) & set(citations), (case.case_id, case.question, citations)


@pytest.mark.asyncio
async def test_fixed_quality_fixture_expected_rank_is_top() -> None:
    runtime = await _engine_with_fixed_evidence()
    for case in fixed_evaluation_corpus()[160:190]:
        if not case.expected_chunk_ids or case.expected_status != "answered":
            continue
        answers = await runtime.engine().answer(case.question, limit=10)
        citations = tuple(citation.chunk_id for answer in answers for citation in answer.citations)
        assert citations[: len(case.expected_chunk_ids)] == case.expected_chunk_ids, (
            case.case_id, case.expected_chunk_ids, citations
        )


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (CloudModelQuotaError("额度或限流"), "quota_exceeded"),
        (CloudModelTimeoutError("请求超时"), "timeout"),
        (CloudModelNotFoundError("模型或接口不存在", status_code=404), "model_not_found"),
        (RuntimeError("Embedding 向量维度不一致"), "embedding_dimension_mismatch"),
        (RuntimeError("Chroma 检索不可用"), "chroma_unavailable"),
    ],
)
def test_classify_evaluation_error_without_leaking_provider_text(
    error: BaseException, expected: str
) -> None:
    assert classify_evaluation_error(error) == expected


@pytest.mark.asyncio
async def test_fixed_quality_runner_reports_error_breakdown() -> None:
    class FailingEngine:
        async def answer(self, question: str, *, limit: int = 5) -> tuple[object, ...]:
            raise CloudModelQuotaError("供应商额度或限流已触发", status_code=429)

    report = await run_fixed_quality_suite(FailingEngine(), "quick")  # type: ignore[arg-type]

    assert report.status == "error"
    assert report.executed_count == 0
    assert report.error_count == 30
    assert report.primary_error_code == "quota_exceeded"
    assert report.error_breakdown == {"quota_exceeded": 30}
