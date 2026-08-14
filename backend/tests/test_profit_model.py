from backend.app.domain.profit_model import ProfitModelInput, calculate_profit_model


def test_profit_model_calculates_fbo_fbs_and_sensitivity() -> None:
    fbo, fbs = calculate_profit_model(
        ProfitModelInput(10000, 3000, 700, 1000, 1000, 500, 200, 30000)
    )
    assert fbo.fulfillment_type == "FBO"
    assert fbo.contribution_profit_minor == 4600
    assert fbs.contribution_profit_minor == 4300
    assert fbo.ad_cost_plus_20_profit_minor < fbo.contribution_profit_minor
    assert fbo.break_even_units == 7
