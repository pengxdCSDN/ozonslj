"""受控自动化编排的防循环、幂等和有限重试回归测试。"""

import pytest

from backend.app.domain.automation_orchestration import (
    AutomationRun,
    RetryPolicy,
    build_idempotency_key,
    ensure_trigger_allowed,
)


def make_run(*, depth: int = 0) -> AutomationRun:
    return AutomationRun(
        run_id="run-1",
        workspace_id="workspace-1",
        automation_type="seller_sync",
        data_version="version-1",
        depth=depth,
    )


def test_display_refresh_cannot_trigger_business_sync() -> None:
    with pytest.raises(ValueError, match="不允许触发"):
        ensure_trigger_allowed(
            event_type="display_refreshed",
            target="seller_sync",
            run=make_run(),
        )


def test_recommendation_can_only_enter_human_review() -> None:
    with pytest.raises(ValueError, match="不允许触发"):
        ensure_trigger_allowed(
            event_type="recommendation_created",
            target="controlled_publish",
            run=make_run(),
        )
    ensure_trigger_allowed(
        event_type="recommendation_created",
        target="human_review",
        run=make_run(),
    )


def test_trigger_chain_is_fused_after_max_depth() -> None:
    with pytest.raises(ValueError, match="超过最大深度"):
        ensure_trigger_allowed(
            event_type="external_fact_changed",
            target="data_quality",
            run=make_run(depth=6),
        )


def test_child_run_keeps_root_and_parent_for_traceability() -> None:
    child = make_run().child(
        run_id="run-2", automation_type="data_quality", data_version="version-1"
    )
    assert child.root_run_id == "run-1"
    assert child.parent_run_id == "run-1"
    assert child.depth == 1
    assert build_idempotency_key(child) == "workspace-1:run-1:data_quality:version-1"


def test_retry_policy_has_bounded_exponential_backoff() -> None:
    policy = RetryPolicy(max_attempts=3, base_delay_seconds=10, max_delay_seconds=15)
    assert policy.delay_seconds(attempt=1, retryable=True) == 10
    assert policy.delay_seconds(attempt=2, retryable=True) == 15
    assert policy.delay_seconds(attempt=3, retryable=True) is None
    assert policy.delay_seconds(attempt=1, retryable=False) is None
