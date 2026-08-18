from backend.app.domain.rag_evaluation_corpus import (
    fixed_evaluation_chunks,
    fixed_evaluation_corpus,
    fixed_suite_case_ids,
)


def test_fixed_corpus_has_calibration_and_frozen_suites() -> None:
    cases = fixed_evaluation_corpus()
    assert len(cases) == 400
    assert sum(item.split == "calibration" for item in cases) == 160
    assert sum(item.split == "frozen" for item in cases) == 240
    assert len({item.case_id for item in cases}) == 400
    assert len(fixed_suite_case_ids("quick")) == 30
    assert len(fixed_suite_case_ids("standard")) == 120
    assert len(fixed_suite_case_ids("full")) == 240


def test_fixed_corpus_contains_security_and_multi_intent_cases() -> None:
    tags = {tag for item in fixed_evaluation_corpus() for tag in item.safety_tags}
    assert {"prompt_injection", "permission_boundary", "multi_intent", "unsupported"} <= tags


def test_fixed_evaluation_chunks_match_gold_ids_and_exclude_refusals() -> None:
    cases = fixed_evaluation_corpus()
    chunks = fixed_evaluation_chunks()
    expected = {chunk_id for case in cases for chunk_id in case.expected_chunk_ids}
    assert {chunk.chunk_id for chunk in chunks} == expected
    assert len(chunks) == len(expected)
    assert all(chunk.metadata.extra[-1] == ("evaluation_only", "true") for chunk in chunks)
    assert all(chunk.metadata.status == "published" for chunk in chunks)


def test_fixed_evaluation_chunks_can_be_loaded_by_suite() -> None:
    quick_case_ids = set(fixed_suite_case_ids("quick"))
    chunks = fixed_evaluation_chunks(suite="quick")
    expected = {
        chunk_id
        for case in fixed_evaluation_corpus()
        if case.case_id in quick_case_ids
        for chunk_id in case.expected_chunk_ids
    }
    assert {chunk.chunk_id for chunk in chunks} == expected
