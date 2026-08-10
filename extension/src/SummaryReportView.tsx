import { useState } from "react";
import { buildAndSaveSummaryReport, listSummaryReports, type SummaryReport } from "./api";

export function SummaryReportView({ workspaceId }: { workspaceId: string }) {
  const [reports, setReports] = useState<SummaryReport[]>([]);
  const [message, setMessage] = useState("报告只提供建议，不自动执行写操作");
  const [busy, setBusy] = useState(false);
  const build = async () => { setBusy(true); try { const report = await buildAndSaveSummaryReport(workspaceId, { report_type: "weekly", period: "2026-W32", sales_change_percent: -25, stockout_risk_count: 2, advertising_anomaly_count: 1, opportunity_count: 3 }); setReports((current) => [report, ...current]); setMessage("运营汇总报告已保存"); } catch (error) { setMessage(error instanceof Error ? error.message : "报告生成失败"); } finally { setBusy(false); } };
  const load = async () => { setBusy(true); try { setReports(await listSummaryReports(workspaceId)); setMessage("已加载报告历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "报告历史加载失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">报告与智能助手 / AI-007</p><h1>运营汇总报告</h1><p>统一生成日报、周报、月报和站内待办，报告只提供建议。</p></div></section><section className="panel"><div className="section-heading"><div><p className="eyebrow">只读报告</p><h2>运营摘要</h2></div><div className="button-row"><button className="secondary-button" disabled={busy} onClick={() => void build()}>生成并保存周报</button><button className="secondary-button" disabled={busy} onClick={() => void load()}>加载历史</button></div></div><p className="form-message">{message}</p>{reports.length ? reports.map((result, index) => <div className="quality-result" key={`${result.report_type}-${result.period}-${index}`}><strong>{result.headline} · {result.report_type}</strong>{result.metric_lines.map((item) => <span key={item}>{item}</span>)}<small>异常：{result.anomalies.join("；")}</small><small>待办：{result.todos.join("；") || "无"}</small><em>{result.read_only ? "只读报告" : "需复核"}</em></div>) : <div className="empty-search"><strong>尚未生成运营报告</strong><span>报告和待办只提供建议，不自动执行写操作。</span></div>}</section></div>;
}
