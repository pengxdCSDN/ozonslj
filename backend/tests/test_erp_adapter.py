import pytest

from backend.app.domain.erp_adapter import normalize_erp_supply_record, parse_erp_csv


def test_erp_port_normalizes_supplementary_supply_record() -> None:
    result = normalize_erp_supply_record({
        "external_id": "PO-1", "offer_id": "SKU-1", "record_type": "inbound",
        "quantity": 10, "amount_minor": 1000, "currency": "rub",
        "expected_date": "2026-08-20",
    })
    assert result.currency == "RUB"
    assert result.source == "erp_import"


def test_erp_port_rejects_unknown_type_and_invalid_quantity() -> None:
    with pytest.raises(ValueError):
        normalize_erp_supply_record({
            "external_id": "1", "offer_id": "SKU", "record_type": "stock",
        })
    with pytest.raises(ValueError):
        normalize_erp_supply_record({
            "external_id": "1", "offer_id": "SKU", "record_type": "cost", "quantity": -1,
        })


def test_erp_csv_parser_deduplicates_external_facts() -> None:
    content = (
        "external_id,offer_id,record_type,quantity,amount_minor,currency,expected_date\n"
        "PO-1,SKU-1,purchase,2,1000,RUB,2026-08-20\n"
    )
    result = parse_erp_csv(content)
    assert len(result) == 1
    assert result[0].record_type == "purchase"
    with pytest.raises(ValueError):
        parse_erp_csv(content + "PO-1,SKU-1,purchase,2,1000,RUB,2026-08-20\n")


def test_erp_record_rejects_amount_without_currency() -> None:
    with pytest.raises(ValueError, match="金额存在时必须同时提供币种"):
        normalize_erp_supply_record({
            "external_id": "PO-1", "offer_id": "SKU-1", "record_type": "cost",
            "quantity": 1, "amount_minor": 1000,
        })
