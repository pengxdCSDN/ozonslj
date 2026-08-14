from backend.app.domain.selection_validate import ValidateInput, validate_product


def test_validate_returns_fbo_fbs_profit_and_risks() -> None:
    result = validate_product(
        ValidateInput(
            "SKU-1", 10000, 3000, 1000, 1000, 500, 200, 30000, 25, 100, 20, True
        )
    )
    assert result.fbo.contribution_profit_minor == 4300
    assert result.fbo.break_even_units == 7
    assert "竞品数量较高" in result.risks
    assert "需要人工确认认证要求" in result.risks
