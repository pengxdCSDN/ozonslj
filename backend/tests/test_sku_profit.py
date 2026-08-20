import pytest

from backend.app.domain.sku_profit import (
    CommissionRule,
    FbsLogisticsTemplate,
    LogisticsBand,
    ProductProfitInput,
    ProfitCalculationError,
    RateTrace,
    SkuProfitInput,
    calculate_sku_profits,
)


def _trace(version: str) -> RateTrace:
    return RateTrace(version=version, source="manual", effective_at="2026-08-20")


def _sku(sku_id: str, weight_g: int, dimensions_mm: tuple[int, int, int]) -> SkuProfitInput:
    return SkuProfitInput(
        sku_id=sku_id,
        selling_price_minor=100_000,
        discount_minor=0,
        landed_cost_minor=30_000,
        weight_g=weight_g,
        length_mm=dimensions_mm[0],
        width_mm=dimensions_mm[1],
        height_mm=dimensions_mm[2],
        logistics_template_id="fbs-default",
        packaging_minor=1_000,
        payment_rate_bps=100,
        ad_rate_bps=500,
        return_loss_rate_bps=200,
    )


def test_calculates_each_sku_with_commission_and_weight_band() -> None:
    product = ProductProfitInput(
        product_name="测试商品",
        category_id="category-1",
        skus=(
            _sku("small", 400, (100, 100, 100)),
            _sku("medium", 1_500, (200, 200, 200)),
            _sku("volume-heavy", 500, (300, 300, 300)),
        ),
    )
    commission = (CommissionRule("category-1", 1_500, _trace("commission-v1")),)
    template = (
        FbsLogisticsTemplate(
            "fbs-default",
            5_000,
            (
                LogisticsBand(1_000, 5_000),
                LogisticsBand(2_000, 8_000),
                LogisticsBand(6_000, 12_000),
            ),
            _trace("logistics-v3"),
        ),
    )

    results = calculate_sku_profits(product, commission, template)

    assert [result.logistics_minor for result in results] == [5_000, 8_000, 12_000]
    assert results[2].volumetric_weight_g == 5_400
    assert results[2].chargeable_weight_g == 5_400
    assert results[0].commission_minor == 15_000
    assert results[0].contribution_profit_minor == 41_000
    assert results[0].break_even_price_minor == 46_754
    assert results[0].commission_trace.version == "commission-v1"
    assert results[0].logistics_trace.version == "logistics-v3"


def test_rejects_missing_commission_rule() -> None:
    product = ProductProfitInput("测试商品", "missing", (_sku("sku-1", 400, (100, 100, 100)),))

    with pytest.raises(ProfitCalculationError, match="缺少有效佣金规则"):
        calculate_sku_profits(product, (), ())


def test_rejects_weight_outside_logistics_template() -> None:
    product = ProductProfitInput(
        "测试商品", "category-1", (_sku("oversize", 2_000, (100, 100, 100)),)
    )
    commission = (CommissionRule("category-1", 1_500, _trace("commission-v1")),)
    templates = (
        FbsLogisticsTemplate(
            "fbs-default", 5_000, (LogisticsBand(1_000, 5_000),), _trace("logistics-v1")
        ),
    )

    with pytest.raises(ProfitCalculationError, match="超出模板"):
        calculate_sku_profits(product, commission, templates)
