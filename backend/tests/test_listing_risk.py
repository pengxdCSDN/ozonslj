from backend.app.domain.listing_risk import detect_listing_risks


def test_listing_risk_detects_medical_brand_and_certification_claims() -> None:
    result = detect_listing_risks("Лучший товар лечит всё Apple EAC")
    risk_types = {item.risk_type for item in result.findings}
    assert {"absolute", "medical", "brand", "certification"} <= risk_types
    assert result.original_text == "Лучший товар лечит всё Apple EAC"
    assert result.safe_to_review is True
