import math

import pytest

from backend.app.domain.summary_report import build_summary_report


def test_summary_report_rejects_boolean_count_and_non_finite_change() -> None:
    with pytest.raises(ValueError):
        build_summary_report(
            report_type="daily", period="2026-08-09", sales_change_percent=0,
            stockout_risk_count=True, advertising_anomaly_count=0, opportunity_count=0,
        )
    with pytest.raises(ValueError):
        build_summary_report(
            report_type="daily", period="2026-08-09", sales_change_percent=math.inf,
            stockout_risk_count=0, advertising_anomaly_count=0, opportunity_count=0,
        )
