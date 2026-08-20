"""说明本模块的职责、边界和主要协作对象。"""

import math
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SummaryReport:
    """说明 SummaryReport 的职责、状态边界和对外协作关系。"""
    report_type: str
    period: str
    headline: str
    metric_lines: list[str]
    anomalies: list[str]
    todos: list[str]
    read_only: bool


class SummaryReportGateway(Protocol):
    """说明 SummaryReportGateway 的职责、状态边界和对外协作关系。"""
    async def save_report(
        self, *, workspace_id: str, report: SummaryReport
    ) -> SummaryReport:
        """执行 save_report 的业务流程并返回该流程的结果。"""

    async def list_reports(
        self, *, workspace_id: str, limit: int
    ) -> list[SummaryReport]:
        """执行 list_reports 的业务流程并返回该流程的结果。"""


def build_summary_report(
    *, report_type: str, period: str, sales_change_percent: float | None,
    stockout_risk_count: int, advertising_anomaly_count: int,
    opportunity_count: int,
) -> SummaryReport:
    """执行 build_summary_report 的业务流程并返回该流程的结果。"""
    normalized = report_type.strip().lower()
    if normalized not in {"daily", "weekly", "monthly"} or not period.strip():
        raise ValueError("报告类型必须是 daily、weekly 或 monthly，且周期不能为空")
    counts = (stockout_risk_count, advertising_anomaly_count, opportunity_count)
    if (
        any(isinstance(value, bool) or not isinstance(value, int) for value in counts)
        or min(counts) < 0
    ):
        raise ValueError("报告统计数量不能为负数")
    if sales_change_percent is not None and (
        isinstance(sales_change_percent, bool)
        or not isinstance(sales_change_percent, (int, float))
        or not math.isfinite(sales_change_percent)
    ):
        raise ValueError("销售变化必须是有限数值")
    anomalies: list[str] = []
    todos: list[str] = []
    if sales_change_percent is not None and sales_change_percent <= -20:
        anomalies.append("销售额较上一窗口下降 20% 以上")
        todos.append("复核销售下降商品、库存和广告承接")
    if stockout_risk_count:
        anomalies.append(f"{stockout_risk_count} 个商品存在缺货风险")
        todos.append("处理缺货风险商品并核对在途计划")
    if advertising_anomaly_count:
        anomalies.append(f"广告分析发现 {advertising_anomaly_count} 项异常")
        todos.append("复核高费无转化关键词和 ACOS 告警")
    if opportunity_count:
        todos.append(f"查看 {opportunity_count} 个选品机会")
    if not anomalies:
        anomalies.append("本周期未触发已配置异常规则")
    return SummaryReport(
        normalized, period, f"{period} 运营摘要", [
            (
                f"销售变化：{sales_change_percent:.2f}%"
                if sales_change_percent is not None else "销售变化：数据不足"
            ),
            f"缺货风险：{stockout_risk_count} 个",
            f"广告异常：{advertising_anomaly_count} 项",
            f"选品机会：{opportunity_count} 个",
        ], anomalies, todos, True,
    )
