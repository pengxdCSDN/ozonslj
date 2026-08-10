from backend.app.domain.advertising_readonly import check_advertising_action


def test_advertising_writes_are_denied_and_analysis_is_allowed() -> None:
    assert check_advertising_action("diagnose").allowed is True
    denied = check_advertising_action("change_budget")
    assert denied.allowed is False
    assert denied.audit_required is True


def test_unknown_advertising_action_is_denied_by_default() -> None:
    assert check_advertising_action("future_write").allowed is False
