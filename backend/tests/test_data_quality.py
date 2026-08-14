from datetime import UTC, datetime, timedelta

from backend.app.domain.data_quality import (
    check_amount_and_inventory,
    check_cross_source_consistency,
    check_relationship_and_time,
    check_required_and_enum,
)


def test_quality_check_reports_missing_required_field_without_exposing_value() -> None:
    findings = check_required_and_enum(
        {"status": "active"},
        required_fields=("offer_id",),
        enum_fields={"status": frozenset({"active", "disabled"})},
    )

    assert findings[0].rule_code == "DQ-003-MISSING"
    assert findings[0].field_name == "offer_id"
    assert "value" not in findings[0].message


def test_quality_check_reports_unknown_enum() -> None:
    findings = check_required_and_enum(
        {"offer_id": "SKU-1", "status": "broken"},
        required_fields=("offer_id",),
        enum_fields={"status": frozenset({"active", "disabled"})},
    )

    assert [(item.rule_code, item.field_name) for item in findings] == [("DQ-003-ENUM", "status")]


def test_relationship_and_time_check_reports_orphan_and_time_regression() -> None:
    now = datetime.now(UTC)
    findings = check_relationship_and_time(
        {
            "workspace_id": "store-1",
            "offer_id": None,
            "started_at": now,
            "completed_at": now - timedelta(seconds=1),
        },
        required_relationships=(("workspace_id", "offer_id"),),
        time_order=("started_at", "completed_at"),
    )

    assert {item.rule_code for item in findings} == {"DQ-004-ORPHAN", "DQ-004-TIME"}


def test_amount_and_inventory_check_reports_invalid_values() -> None:
    findings = check_amount_and_inventory({"available_stock": -1, "price": "bad"})

    assert {item.rule_code for item in findings} == {"DQ-005-STOCK", "DQ-005-AMOUNT"}


def test_cross_source_check_reports_conflict_without_overwriting_official_value() -> None:
    findings = check_cross_source_consistency(
        {"official_price": "100", "imported_price": "90"},
        source_pairs=(("official_price", "imported_price"),),
    )

    assert findings[0].rule_code == "DQ-006-CONFLICT"
    assert findings[0].severity == "warning"
