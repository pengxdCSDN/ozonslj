import { useEffect, useState } from "react";
import { checkAndSaveListingRisks, listListingRiskHistory, type ListingRiskReport } from "./api";

export function ListingRiskView({ workspaceId }: { workspaceId: string }) {
  const [reports, setReports] = useState<ListingRiskReport[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("风险检测只提供建议，原文始终保留");
  const load = async () => { try { setReports(await listListingRiskHistory(workspaceId)); setMessage("已加载风险报告历史"); } catch (error) { setMessage(error instanceof Error ? error.message : "风险历史加载失败"); } };
  useEffect(() => { void load(); }, [workspaceId]);
  const run = async () => { setBusy(true); try { await checkAndSaveListingRisks(workspaceId, { text: "Термос лечит всё, Apple EAC", authorized_brands: [], verified_certifications: [] }); setMessage("风险报告已保存，原文保持不变"); await load(); } catch (error) { setMessage(error instanceof Error ? error.message : "风险报告保存失败"); } finally { setBusy(false); } };
  return <div className="view-content"><section className="page-heading compact"><div><p className="eyebrow">Listing Skill / LST-007</p><h1>内容风险检测</h1><p>标记绝对化、疗效、品牌和认证风险，只给出修改建议，不自动删除原文。</p></div></section><section className="panel import-panel"><button className="secondary-button" disabled={busy} onClick={() => void run()}>{busy ? "检测并保存中…" : "检测并保存报告"}</button><p className="form-message">{message}</p></section><section className="panel"><div className="panel-heading"><h2>最近检测</h2><button className="secondary-button" disabled={busy} onClick={() => void load()}>刷新</button></div>{reports.length ? reports.map((report, index) => <article className="history-item" key={`${report.original_text}-${index}`}><strong>{report.findings.length ? `发现 ${report.findings.length} 个风险` : "未发现风险"} · 原文已保留</strong><span>{report.original_text}</span><small>{report.findings.map((item) => `${item.risk_type}/${item.severity}：${item.matched_text} → ${item.suggestion}`).join("；") || "暂无修改建议"}</small></article>) : <div className="empty-search"><strong>暂无风险报告</strong><span>检测结果会保留原文，并记录人工修改建议。</span></div>}</section></div>;
}
