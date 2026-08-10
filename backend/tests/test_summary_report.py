from backend.app.domain.summary_report import build_summary_report


def test_summary_report_builds_anomalies_and_todos() -> None:
    result = build_summary_report(
        report_type="weekly", period="2026-W32", sales_change_percent=-25,
        stockout_risk_count=2, advertising_anomaly_count=1, opportunity_count=3,
    )
    assert result.report_type == "weekly"
    assert len(result.anomalies) == 3
    assert len(result.todos) == 4
    assert result.read_only is True
