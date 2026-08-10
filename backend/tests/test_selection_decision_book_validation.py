import pytest

from backend.app.domain.selection_decision_book import SelectionDecisionBook, validate_decision_book


def test_decision_book_requires_sources_and_keywords() -> None:
    book = SelectionDecisionBook(
        "机会", "场景", "样本", (), "利润", (), "价格", "备货", (), (), "不确定", "pending"
    )
    with pytest.raises(ValueError):
        validate_decision_book(book)
