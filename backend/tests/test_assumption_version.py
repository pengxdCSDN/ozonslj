from backend.app.domain.assumption_version import assumption_version


def test_assumption_version_is_stable_and_changes_with_input() -> None:
    assert assumption_version({"price": 1, "cost": 2}) == assumption_version(
        {"cost": 2, "price": 1}
    )
    assert assumption_version({"price": 1}) != assumption_version({"price": 2})
