from backend.app.domain.listing_fabe import FabePoint, generate_fabe_draft


def test_fabe_generates_bullets_description_images_and_evidence_warning() -> None:
    result = generate_fabe_draft(
        [
            FabePoint(
                "нержавеющая сталь", "прочный корпус", "долгий срок службы",
                "паспорт материала", "Корпус из нержавеющей стали для ежедневного использования.",
            ),
            FabePoint(
                "500 мл", "удобный объём", "подходит для поездок", None,
                "Объём 500 мл для дороги и офиса.",
            ),
        ],
        product_name="Термос",
    )
    assert len(result.bullets) == 2
    assert "Термос" in result.long_description
    assert result.missing_evidence == ("500 мл",)
    assert len(result.image_copy_suggestions) == 2
