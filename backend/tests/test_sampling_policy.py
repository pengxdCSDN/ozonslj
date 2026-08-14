from backend.app.domain.sampling_policy import check_sampling_policy


def test_sampling_policy_normalizes_allowed_public_url() -> None:
    decision = check_sampling_policy(
        "https://example.com/item/1?utm_source=test#details",
        robots_allowed=True,
    )
    assert decision.allowed is True
    assert decision.normalized_url == "https://example.com/item/1"


def test_sampling_policy_blocks_robots_and_stop_conditions() -> None:
    blocked = check_sampling_policy("https://example.com/item/1", robots_allowed=False)
    stopped = check_sampling_policy(
        "https://example.com/item/1",
        robots_allowed=True,
        stop_requested=True,
    )
    assert (blocked.allowed, blocked.code) == (False, "robots_forbidden")
    assert (stopped.allowed, stopped.code) == (False, "sampling_stopped")
