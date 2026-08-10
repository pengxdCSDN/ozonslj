import pytest

from backend.app.domain.listing_fabe import FabePoint, generate_fabe_draft


def test_fabe_filters_incomplete_four_part_points() -> None:
    result = generate_fabe_draft(
        [FabePoint("容量", "便携", "通勤使用", "规格", "容量 500 ml")],
        product_name="Термос",
    )
    assert len(result.bullets) == 1


def test_fabe_rejects_empty_product_name() -> None:
    with pytest.raises(ValueError):
        generate_fabe_draft([], product_name=" ")
