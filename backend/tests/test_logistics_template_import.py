import pytest

from backend.app.domain.logistics_template_import import (
    LogisticsTemplateImportError,
    preview_logistics_template_csv,
)

CSV_CONTENT = (
    "template_id,fulfillment_type,warehouse_id,route_id,region_id,version,effective_from,"
    "effective_to,volumetric_divisor_cm3_per_kg,max_weight_g,base_fee_minor,"
    "additional_fee_minor,additional_step_g,fee_rate_bps,currency,source\n"
    "fbs-main,FBS,warehouse-1,route-main,all,v1,2026-08-20,,5000,1000,5000,0,0,0,RUB,manual\n"
    "fbs-main,FBS,warehouse-1,route-main,all,v1,2026-08-20,,5000,3000,8000,0,0,0,RUB,manual\n"
)


def test_preview_groups_template_bands_and_preserves_context() -> None:
    preview = preview_logistics_template_csv(CSV_CONTENT)

    assert preview.row_count == 2
    assert not preview.errors
    assert len(preview.templates) == 1
    template = preview.templates[0]
    assert template.warehouse_id == "warehouse-1"
    assert [band.max_chargeable_weight_g for band in template.bands] == [1000, 3000]


def test_preview_rejects_missing_required_column() -> None:
    with pytest.raises(LogisticsTemplateImportError, match="缺少必需列"):
        preview_logistics_template_csv("template_id,max_weight_g\na,1000\n")


def test_preview_reports_row_error_without_creating_template() -> None:
    invalid_csv = CSV_CONTENT.replace(",1000,5000,0,0,0,RUB", ",-1,5000,0,0,0,RUB")
    preview = preview_logistics_template_csv(invalid_csv)

    assert preview.errors
    assert not preview.templates
