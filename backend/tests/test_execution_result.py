from backend.app.domain.execution_result import ItemExecutionResult, summarize_execution


def test_partial_failure_keeps_each_item_result() -> None:
    result = summarize_execution([
        ItemExecutionResult("SKU-1", True, "已完成"),
        ItemExecutionResult("SKU-2", False, "接口拒绝"),
    ])
    assert result.status == "partial_failure"
    assert result.succeeded == 1
    assert result.failed == 1
    assert result.items[1].message == "接口拒绝"
