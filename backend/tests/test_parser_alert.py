from backend.app.domain.parser_alert import detect_parser_changes


def test_parser_change_detects_changed_and_missing_fields() -> None:
    changes = detect_parser_changes(
        {"title": "旧标题", "rating": "4.5", "price": "100"},
        {"title": "新标题", "price": "100"},
    )
    assert [(item.field_name, item.severity) for item in changes] == [
        ("rating", "error"),
        ("title", "warning"),
    ]
