"""运行 RAG 固定评测执行器的离线契约验收。

该脚本使用脱敏固定语料和确定性内存索引验证 30/120/240 三档执行边界，
不代表真实供应商或生产知识库质量；真实验收必须由生产运行时注入已发布知识版本后执行。
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict

from backend.app.domain.knowledge_chunking import ChunkMetadata, KnowledgeChunk
from backend.app.domain.knowledge_runtime import KnowledgeRuntimeIndex
from backend.app.domain.rag_evaluation_corpus import fixed_evaluation_corpus
from backend.app.domain.rag_metrics import quality_gate_passed
from backend.app.domain.rag_quality_runner import run_fixed_quality_suite


def _chunk(case_id: str, question: str) -> KnowledgeChunk:
    suffix = case_id.removeprefix("fixed-rag-v2-")
    return KnowledgeChunk(
        chunk_id=f"gold-{suffix}",
        content=question + " 这是经过人工确认的脱敏评测证据。",
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


async def main() -> None:
    runtime = KnowledgeRuntimeIndex()
    cases = fixed_evaluation_corpus()
    chunks = []
    for case in cases:
        chunks.extend(
            _chunk(chunk_id.replace("gold-", "fixed-rag-v2-"), case.question)
            for chunk_id in case.expected_chunk_ids
        )
    runtime.stage("quality-fixture-v1", tuple(chunks))
    await runtime.publish("quality-fixture-v1")
    results = []
    for suite in ("quick", "standard", "full"):
        report = await run_fixed_quality_suite(runtime.engine(), suite)  # type: ignore[arg-type]
        results.append({
            "suite": report.suite,
            **asdict(report),
            "metrics": asdict(report.metrics),
            "gate_status": "passed" if quality_gate_passed(report.metrics) else "blocked",
        })
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if any(item["gate_status"] != "passed" for item in results):
        raise SystemExit("RAG 质量门禁未通过；请查看上方分组指标")


if __name__ == "__main__":
    asyncio.run(main())
