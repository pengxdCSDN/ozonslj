import pytest

from backend.app.domain.selection_decision_book import validate_confirmation_status


def test_confirmation_rejects_pending_status() -> None:
    with pytest.raises(ValueError):
        validate_confirmation_status("pending")
