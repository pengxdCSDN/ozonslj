"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_profit_model_gateway, get_store_workspace_gateway
from backend.app.domain.assumption_version import assumption_version
from backend.app.domain.logistics_template_import import (
    LogisticsTemplateImportError,
    preview_logistics_template_csv,
)
from backend.app.domain.profit_model import (
    ProfitModelGateway,
    ProfitModelInput,
    ProfitScenario,
    calculate_profit_model,
)
from backend.app.domain.profit_reconciliation import (
    ProfitReconciliationError,
    preview_profit_reconciliation_csv,
)
from backend.app.domain.sku_profit import (
    CommissionRule,
    FbsLogisticsTemplate,
    LogisticsBand,
    ProductProfitInput,
    ProfitCalculationError,
    RateTrace,
    SkuProfitInput,
    SkuProfitResult,
    calculate_sku_profits,
)
from backend.app.domain.store_workspace import StoreWorkspaceGateway

router = APIRouter(prefix="/v1/selection/profit-model", tags=["selection"])


class ProfitModelPayload(BaseModel):
    """说明 ProfitModelPayload 的职责、状态边界和对外协作关系。"""
    selling_price_minor: int = Field(ge=0)
    purchase_cost_minor: int = Field(ge=0)
    fbo_logistics_minor: int = Field(ge=0)
    fbs_logistics_minor: int = Field(ge=0)
    commission_minor: int = Field(ge=0)
    ad_cost_minor: int = Field(ge=0)
    return_loss_minor: int = Field(ge=0)
    fixed_cost_minor: int = Field(default=0, ge=0)


class RateTracePayload(BaseModel):
    """描述费率版本的来源和生效时间，供利润结果审计与重放。"""

    version: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=50)
    effective_at: str = Field(min_length=1, max_length=50)


class CommissionRulePayload(BaseModel):
    """接收一个类目佣金规则版本，费率以基点表示。"""

    category_id: str = Field(min_length=1, max_length=200)
    rate_bps: int = Field(ge=0, le=10_000)
    trace: RateTracePayload


class LogisticsBandPayload(BaseModel):
    """接收 FBS 模板中的一个计费重量上限及对应费用。"""

    max_chargeable_weight_g: int = Field(gt=0)
    fee_minor: int = Field(ge=0)


class FbsLogisticsTemplatePayload(BaseModel):
    """接收可追溯的 FBS 体积重系数和物流费用分档。"""

    template_id: str = Field(min_length=1, max_length=200)
    volumetric_divisor_cm3_per_kg: int = Field(gt=0)
    bands: list[LogisticsBandPayload] = Field(min_length=1)
    trace: RateTracePayload


class SkuProfitPayload(BaseModel):
    """接收单个 SKU 的价格、成本、规格和费用率假设。"""

    sku_id: str = Field(min_length=1, max_length=200)
    selling_price_minor: int = Field(gt=0)
    discount_minor: int = Field(default=0, ge=0)
    landed_cost_minor: int = Field(ge=0)
    weight_g: int = Field(gt=0)
    length_mm: int = Field(gt=0)
    width_mm: int = Field(gt=0)
    height_mm: int = Field(gt=0)
    logistics_template_id: str = Field(min_length=1, max_length=200)
    packaging_minor: int = Field(default=0, ge=0)
    payment_rate_bps: int = Field(default=0, ge=0, le=10_000)
    ad_rate_bps: int = Field(default=0, ge=0, le=10_000)
    return_loss_rate_bps: int = Field(default=0, ge=0, le=10_000)
    other_variable_cost_minor: int = Field(default=0, ge=0)


class ProductSkuProfitPayload(BaseModel):
    """接收商品、SKU 和版本化规则目录，驱动一次自动利润测算。"""

    product_name: str = Field(min_length=1, max_length=300)
    category_id: str = Field(min_length=1, max_length=200)
    skus: list[SkuProfitPayload] = Field(min_length=1, max_length=500)
    commission_rules: list[CommissionRulePayload] = Field(min_length=1, max_length=500)
    logistics_templates: list[FbsLogisticsTemplatePayload] = Field(min_length=1, max_length=100)


class LogisticsTemplateCsvPayload(BaseModel):
    """接收物流模板 CSV 文本，仅用于预览和校验，不直接写入配置。"""

    content: str = Field(min_length=1, max_length=2_000_000)


class ProfitReconciliationCsvPayload(BaseModel):
    """接收订单实际费用 CSV，仅用于预览和差异计算。"""

    content: str = Field(min_length=1, max_length=2_000_000)


@router.post("/reconciliation/preview")
async def preview_profit_reconciliation(
    payload: ProfitReconciliationCsvPayload,
) -> dict[str, object]:
    """预览实际费用 CSV 并返回预计/实际利润差异。

    Args:
        payload: 包含订单、SKU、预计费用和实际费用的 UTF-8 CSV 文本。

    Returns:
        行数、错误摘要和标准化差异明细；该接口不会写入业务事实。

    Raises:
        HTTPException: CSV 表头缺失或内容不可解析时返回 422。
    """
    try:
        preview = preview_profit_reconciliation_csv(payload.content)
    except ProfitReconciliationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "profit_reconciliation_csv_invalid", "message": str(exc)},
        ) from exc
    return {
        "row_count": preview.row_count,
        "errors": list(preview.errors),
        "rows": [asdict(row) for row in preview.rows],
    }


@router.post("/logistics-templates/preview")
async def preview_logistics_templates(
    payload: LogisticsTemplateCsvPayload,
) -> dict[str, object]:
    """校验物流模板 CSV 并返回标准化预览结果。

    Args:
        payload: UTF-8 CSV 文本，包含模板上下文和重量分档。

    Returns:
        行数、错误摘要和可保存的标准化模板预览。

    Raises:
        HTTPException: CSV 缺少表头或无法解析时返回 422。
    """
    try:
        preview = preview_logistics_template_csv(payload.content)
    except LogisticsTemplateImportError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "logistics_template_csv_invalid", "message": str(exc)},
        ) from exc
    return {
        "row_count": preview.row_count,
        "errors": list(preview.errors),
        "templates": [
            {
                "template_id": template.template_id,
                "fulfillment_type": template.fulfillment_type,
                "warehouse_id": template.warehouse_id,
                "route_id": template.route_id,
                "region_id": template.region_id,
                "version": template.trace.version,
                "effective_at": template.trace.effective_at,
                "bands": [asdict(band) for band in template.bands],
            }
            for template in preview.templates
        ],
    }


@router.post("/calculate-skus", response_model=list[SkuProfitResult])
async def calculate_product_skus(payload: ProductSkuProfitPayload) -> list[SkuProfitResult]:
    """按类目和 SKU 规格自动匹配费率并返回分 SKU 贡献利润。

    Args:
        payload: 商品、SKU 及本次可用的版本化佣金和 FBS 物流规则。

    Returns:
        与请求 SKU 顺序一致、包含费用瀑布和费率追溯信息的结果。

    Raises:
        HTTPException: 业务输入无法匹配唯一规则或违反计算边界时返回 422。
    """
    try:
        product = ProductProfitInput(
            product_name=payload.product_name,
            category_id=payload.category_id,
            skus=tuple(SkuProfitInput(**item.model_dump()) for item in payload.skus),
        )
        commission_rules = tuple(
            CommissionRule(
                category_id=item.category_id,
                rate_bps=item.rate_bps,
                trace=RateTrace(**item.trace.model_dump()),
            )
            for item in payload.commission_rules
        )
        templates = tuple(
            FbsLogisticsTemplate(
                template_id=item.template_id,
                volumetric_divisor_cm3_per_kg=item.volumetric_divisor_cm3_per_kg,
                bands=tuple(LogisticsBand(**band.model_dump()) for band in item.bands),
                trace=RateTrace(**item.trace.model_dump()),
            )
            for item in payload.logistics_templates
        )
        return list(calculate_sku_profits(product, commission_rules, templates))
    except ProfitCalculationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "profit_calculation_invalid", "message": str(exc)},
        ) from exc


@router.post("/calculate", response_model=list[ProfitScenario])
async def calculate_profit(payload: ProfitModelPayload) -> list[ProfitScenario]:
    """执行 calculate_profit 的业务流程并返回该流程的结果。

Args:
    payload: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    return list(calculate_profit_model(ProfitModelInput(**payload.model_dump())))


@router.post(
    "/store-workspaces/{workspace_id}/calculate-and-save",
    response_model=list[ProfitScenario],
)
async def calculate_and_save_profit(
    workspace_id: str,
    payload: ProfitModelPayload,
    gateway: Annotated[ProfitModelGateway, Depends(get_profit_model_gateway)],
    workspace_gateway: Annotated[StoreWorkspaceGateway, Depends(get_store_workspace_gateway)],
) -> list[ProfitScenario]:
    """执行 calculate_and_save_profit 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    payload: 参数语义、输入边界和安全约束。
    gateway: 参数语义、输入边界和安全约束。
    workspace_gateway: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    HTTPException: 业务约束或外部依赖失败时抛出。
"""
    if await workspace_gateway.get_workspace(workspace_id) is None:
        raise HTTPException(status_code=404, detail={"code": "workspace_not_found"})
    assumptions = payload.model_dump()
    assumptions["assumption_version"] = assumption_version(assumptions)
    scenarios = calculate_profit_model(ProfitModelInput(**assumptions))
    saved = await gateway.save_model(
        workspace_id=workspace_id, assumptions=assumptions, scenarios=scenarios
    )
    return list(saved)
